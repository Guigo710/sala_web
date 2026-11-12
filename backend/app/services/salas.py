"""Ambientes: consulta com filtros, disponibilidade, exclusão (RN01)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import SmallInteger, any_, exists, func, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroApi, nao_encontrado
from app.core.tempo import agora, momento
from app.models import (
    FotoSala,
    GrupoRecorrencia,
    HorarioAula,
    Professor,
    Reserva,
    Sala,
    SalaEquipamento,
    sala_softwares,
)
from app.schemas import reservas as sr
from app.schemas.comum import HorarioAula as HorarioSaida
from app.services import apresentacao, arquivos
from app.services.aulas import ordem_turno_sql, validar_bloco

_CARREGAR = (selectinload(Sala.equipamentos), selectinload(Sala.fotos), selectinload(Sala.softwares))


def escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def obter_sala(db: Session, sala_id: int, usuario: Professor | None) -> Sala:
    """Sala por id; inativa só para admin (senão 404)."""
    sala = db.scalars(select(Sala).where(Sala.id == sala_id).options(*_CARREGAR)).first()
    if sala is None or (not sala.ativo and not (usuario and usuario.eh_admin)):
        raise nao_encontrado("Ambiente não encontrado.")
    return sala


def recarregar(db: Session, sala_id: int) -> Sala:
    db.expire_all()
    sala = db.scalars(select(Sala).where(Sala.id == sala_id).options(*_CARREGAR)).first()
    if sala is None:
        raise nao_encontrado("Ambiente não encontrado.")
    return sala


def listar(
    db: Session,
    usuario: Professor | None,
    tipos: Sequence[str] | None = None,
    capacidade_min: int | None = None,
    equipamento_ids: Sequence[int] | None = None,
    software_ids: Sequence[int] | None = None,
    busca: str | None = None,
    data: date | None = None,
    horario_ids: Sequence[int] | None = None,
    incluir_inativas: bool = False,
) -> list[Sala]:
    stmt = select(Sala).options(selectinload(Sala.equipamentos), selectinload(Sala.fotos))
    if not (incluir_inativas and usuario is not None and usuario.eh_admin):
        stmt = stmt.where(Sala.ativo.is_(True))
    if tipos:
        stmt = stmt.where(Sala.tipo.in_(list(tipos)))
    if capacidade_min is not None:
        stmt = stmt.where(Sala.capacidade >= capacidade_min)
    for eid in set(equipamento_ids or []):
        stmt = stmt.where(
            exists().where(SalaEquipamento.sala_id == Sala.id, SalaEquipamento.equipamento_id == eid)
        )
    for sid in set(software_ids or []):
        stmt = stmt.where(
            exists().where(sala_softwares.c.sala_id == Sala.id, sala_softwares.c.software_id == sid)
        )
    if busca and busca.strip():
        padrao = f"%{escapar_like(busca.strip())}%"
        stmt = stmt.where(
            or_(
                Sala.nome.ilike(padrao, escape="\\"),
                Sala.descricao.ilike(padrao, escape="\\"),
                Sala.localizacao.ilike(padrao, escape="\\"),
            )
        )
    if data is not None and horario_ids:
        _, inicio, fim = validar_bloco(db, horario_ids, data, campo="query.horario_ids")
        stmt = stmt.where(
            ~exists().where(
                Reserva.sala_id == Sala.id,
                Reserva.status == "ativa",
                Reserva.data == data,
                Reserva.inicio < fim,
                Reserva.fim > inicio,
            )
        )
    return list(db.scalars(stmt.order_by(Sala.nome)).unique())


def disponibilidade(db: Session, sala: Sala, data: date) -> sr.Disponibilidade:
    dia = data.isoweekday()
    aulas = db.scalars(
        select(HorarioAula)
        .where(HorarioAula.ativo.is_(True), literal(dia, SmallInteger) == any_(HorarioAula.dias_semana))
        .order_by(ordem_turno_sql, HorarioAula.ordem)
    ).all()
    reservas = db.scalars(
        select(Reserva)
        .where(Reserva.sala_id == sala.id, Reserva.data == data, Reserva.status == "ativa")
        .order_by(Reserva.inicio)
    ).unique().all()
    ref = agora()
    itens = []
    for aula in aulas:
        ocupante = next((r for r in reservas if r.inicio < aula.fim and r.fim > aula.inicio), None)
        itens.append(
            sr.AulaDisponibilidade(
                horario=HorarioSaida.model_validate(aula),
                livre=ocupante is None,
                passou=ref >= momento(data, aula.inicio),
                reserva=(
                    sr.ReservaNaAula(
                        id=ocupante.id,
                        professor=apresentacao.pessoa(ocupante.professor),
                        inicio=ocupante.inicio,
                        fim=ocupante.fim,
                    )
                    if ocupante
                    else None
                ),
            )
        )
    return sr.Disponibilidade(sala_id=sala.id, data=data, dia_semana=dia, aulas=itens)


def excluir(db: Session, sala: Sala) -> None:
    tem_reservas = db.scalar(
        select(
            exists().where(Reserva.sala_id == sala.id)
            | exists().where(GrupoRecorrencia.sala_id == sala.id)
        )
    )
    if tem_reservas:
        raise _erro_com_reservas()
    arquivos_fotos = list(db.scalars(select(FotoSala.arquivo).where(FotoSala.sala_id == sala.id)))
    sala_id = sala.id
    db.delete(sala)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _erro_com_reservas() from None
    for arquivo in arquivos_fotos:
        arquivos.apagar_arquivo(arquivo)
    arquivos.apagar_pasta_sala(sala_id)


def _erro_com_reservas() -> ErroApi:
    return ErroApi(
        409,
        "SALA_COM_RESERVAS",
        "Este ambiente tem reservas e não pode ser excluído. Desative-o (ativo = false).",
    )


def proxima_ordem_foto(db: Session, sala_id: int) -> int:
    return (db.scalar(select(func.max(FotoSala.ordem)).where(FotoSala.sala_id == sala_id)) or 0) + 1
