"""Ambientes: consulta com filtros, disponibilidade, cadastro, associações e exclusão (RN01)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import SmallInteger, any_, delete, exists, insert, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.erros import ErroApi, erro_validacao, nao_encontrado
from app.core.tempo import agora, momento
from app.models import (
    Equipamento,
    GrupoRecorrencia,
    HorarioAula,
    Professor,
    Reserva,
    Sala,
    SalaEquipamento,
    Software,
    sala_softwares,
)
from app.schemas import reservas as sr
from app.schemas import salas as ss
from app.schemas.comum import HorarioAula as HorarioSaida
from app.services import apresentacao
from app.services.aulas import ordem_turno_sql, validar_bloco
from app.services.comum import commit_traduzindo, escapar_like

_CARREGAR = (selectinload(Sala.equipamentos), selectinload(Sala.fotos), selectinload(Sala.softwares))


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
    if data is not None and not horario_ids:
        raise erro_validacao("query.horario_ids", "informe as aulas junto com a data")
    if horario_ids and data is None:
        raise erro_validacao("query.data", "informe a data junto com as aulas")
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


def disponibilidade(db: Session, sala_id: int, usuario: Professor | None, data: date) -> sr.Disponibilidade:
    """Aulas do dia (ativas, que valem no dia da semana) com ocupação e `passou` (contrato §4.3)."""
    sala = obter_sala(db, sala_id, usuario)
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


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", "Já existe um ambiente com este nome.")


def _erro_com_reservas() -> ErroApi:
    return ErroApi(
        409,
        "SALA_COM_RESERVAS",
        "Este ambiente tem reservas e não pode ser excluído. Desative-o (ativo = false).",
    )


def _checar_nome(db: Session, nome: str, ignorar_id: int | None = None) -> None:
    stmt = select(Sala.id).where(Sala.nome == nome)
    if ignorar_id is not None:
        stmt = stmt.where(Sala.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise _duplicado()


def _commit_nome(db: Session) -> None:
    commit_traduzindo(db, {"salas_nome_key": _duplicado()})


def criar(db: Session, entrada: ss.SalaEntrada) -> Sala:
    _checar_nome(db, entrada.nome)
    sala = Sala(**entrada.model_dump())
    db.add(sala)
    _commit_nome(db)
    return recarregar(db, sala.id)


def atualizar(db: Session, sala_id: int, entrada: ss.SalaAtualizar, admin: Professor) -> Sala:
    sala = obter_sala(db, sala_id, admin)
    _checar_nome(db, entrada.nome, ignorar_id=sala.id)
    for campo, valor in entrada.model_dump().items():
        setattr(sala, campo, valor)
    _commit_nome(db)
    return recarregar(db, sala.id)


def definir_equipamentos(
    db: Session, sala_id: int, itens: Sequence[ss.SalaEquipamentoEntrada], admin: Professor
) -> Sala:
    """Substitui a lista inteira de equipamentos da sala."""
    sala = obter_sala(db, sala_id, admin)
    ids = [i.equipamento_id for i in itens]
    if len(set(ids)) != len(ids):
        raise erro_validacao("body", "equipamento repetido na lista")
    existentes = set(db.scalars(select(Equipamento.id).where(Equipamento.id.in_(ids)))) if ids else set()
    if len(existentes) != len(set(ids)):
        raise nao_encontrado("Equipamento não encontrado.")
    db.execute(delete(SalaEquipamento).where(SalaEquipamento.sala_id == sala.id))
    for i in itens:
        db.add(
            SalaEquipamento(
                sala_id=sala.id,
                equipamento_id=i.equipamento_id,
                quantidade=i.quantidade,
                especificacao=i.especificacao,
            )
        )
    # Corrida: equipamento excluído entre a checagem e o commit.
    commit_traduzindo(db, {"sala_equipamentos_equipamento_id_fkey": nao_encontrado("Equipamento não encontrado.")})
    return recarregar(db, sala.id)


def definir_softwares(db: Session, sala_id: int, software_ids: Sequence[int], admin: Professor) -> Sala:
    """Substitui a lista inteira de softwares da sala (ids repetidos são ignorados)."""
    sala = obter_sala(db, sala_id, admin)
    ids = list(dict.fromkeys(software_ids))
    existentes = set(db.scalars(select(Software.id).where(Software.id.in_(ids)))) if ids else set()
    if len(existentes) != len(ids):
        raise nao_encontrado("Software não encontrado.")
    db.execute(delete(sala_softwares).where(sala_softwares.c.sala_id == sala.id))
    if ids:
        db.execute(insert(sala_softwares), [{"sala_id": sala.id, "software_id": i} for i in ids])
    commit_traduzindo(db, {"sala_softwares_software_id_fkey": nao_encontrado("Software não encontrado.")})
    return recarregar(db, sala.id)


def excluir(db: Session, sala_id: int, admin: Professor) -> None:
    """Só ambientes sem reservas nem grupos; as fotos (no banco) saem junto, em cascata (ADR-0010)."""
    sala = obter_sala(db, sala_id, admin)
    tem_reservas = db.scalar(
        select(
            exists().where(Reserva.sala_id == sala.id)
            | exists().where(GrupoRecorrencia.sala_id == sala.id)
        )
    )
    if tem_reservas:
        raise _erro_com_reservas()
    db.delete(sala)
    commit_traduzindo(
        db, {"reservas_sala_id_fkey": _erro_com_reservas(), "grupos_recorrencia_sala_id_fkey": _erro_com_reservas()}
    )
