"""Reservas: criação avulsa, conflitos (service + constraint), consultas e cancelamento (RN03–RN08)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, time

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.core.erros import ErroApi, nao_encontrado, nome_constraint, sem_permissao, sqlstate
from app.core.tempo import agora, agora_tz, momento
from app.models import GrupoRecorrencia, HorarioAula, Professor, Reserva, Sala
from app.services import apresentacao
from app.services.aulas import validar_bloco

CONSTRAINT_CONFLITO = "ex_reservas_sem_sobreposicao"


@dataclass
class Bloco:
    """Dados validados comuns à reserva avulsa e à recorrente."""

    sala: Sala
    aulas: list[HorarioAula]
    inicio: time
    fim: time
    dono: Professor


def preparar_bloco(
    db: Session,
    usuario: Professor,
    sala_id: int,
    data: date,
    horario_ids: Sequence[int],
    professor_id: int | None,
) -> Bloco:
    """Regras comuns de criação (contrato §4.10)."""
    if professor_id is not None and not usuario.eh_admin:
        raise sem_permissao("Só o administrador pode reservar em nome de outro professor.")

    sala = db.get(Sala, sala_id)
    if sala is None:
        raise nao_encontrado("Ambiente não encontrado.")
    if not sala.ativo:
        raise ErroApi(422, "SALA_INATIVA", "Este ambiente está desativado e não aceita reservas.")

    aulas, inicio, fim = validar_bloco(db, horario_ids, data)

    if momento(data, inicio) <= agora():
        raise ErroApi(422, "DATA_PASSADA", "Não é possível reservar um horário que já começou ou passou.")

    dono = usuario
    if professor_id is not None:
        encontrado = db.get(Professor, professor_id)
        if encontrado is None:
            raise nao_encontrado("Professor não encontrado.")
        if not encontrado.ativo:
            raise ErroApi(422, "PROFESSOR_INATIVO", "A conta deste professor está desativada.")
        dono = encontrado

    return Bloco(sala=sala, aulas=aulas, inicio=inicio, fim=fim, dono=dono)


def buscar_conflitos(db: Session, sala_id: int, datas: Sequence[date], inicio: time, fim: time) -> list[Reserva]:
    """Reservas ativas da sala que sobrepõem [inicio, fim) em alguma das datas (encostar não conflita)."""
    if not datas:
        return []
    stmt = (
        select(Reserva)
        .where(
            Reserva.sala_id == sala_id,
            Reserva.status == "ativa",
            Reserva.data.in_(list(datas)),
            Reserva.inicio < fim,
            Reserva.fim > inicio,
        )
        .order_by(Reserva.data, Reserva.inicio)
    )
    return list(db.scalars(stmt).unique())


def erro_conflito(conflitos: Sequence[Reserva]) -> ErroApi:
    return ErroApi(
        409,
        "CONFLITO_RESERVA",
        "Sala não disponível neste horário.",
        conflitos=[apresentacao.conflito(r).model_dump(mode="json") for r in conflitos],
    )


def eh_violacao_conflito(erro: IntegrityError) -> bool:
    return nome_constraint(erro) == CONSTRAINT_CONFLITO or sqlstate(erro) == "23P01"


def nova_reserva(bloco: Bloco, data: date, usuario: Professor, observacao: str | None) -> Reserva:
    return Reserva(
        sala_id=bloco.sala.id,
        professor_id=bloco.dono.id,
        data=data,
        inicio=bloco.inicio,
        fim=bloco.fim,
        horario_inicio_id=bloco.aulas[0].id,
        horario_fim_id=bloco.aulas[-1].id,
        quantidade_aulas=len(bloco.aulas),
        status="ativa",
        observacao=observacao,
        criado_por_id=usuario.id,
    )


def criar_avulsa(
    db: Session,
    usuario: Professor,
    sala_id: int,
    data: date,
    horario_ids: Sequence[int],
    observacao: str | None,
    professor_id: int | None,
) -> Reserva:
    bloco = preparar_bloco(db, usuario, sala_id, data, horario_ids, professor_id)

    conflitos = buscar_conflitos(db, bloco.sala.id, [data], bloco.inicio, bloco.fim)
    if conflitos:
        raise erro_conflito(conflitos)

    reserva = nova_reserva(bloco, data, usuario, observacao)
    db.add(reserva)
    try:
        db.commit()
    except IntegrityError as e:
        # Corrida: outra requisição gravou entre a checagem e o INSERT; o banco barrou (ADR-0003).
        db.rollback()
        if eh_violacao_conflito(e):
            raise erro_conflito(buscar_conflitos(db, sala_id, [data], bloco.inicio, bloco.fim)) from None
        raise
    db.refresh(reserva)
    return reserva


# ---------------------------------------------------------------- consultas
def _ordenado_por_sala(stmt):  # noqa: ANN001, ANN202
    return stmt.join(Reserva.sala).options(contains_eager(Reserva.sala))


def listar_agenda(
    db: Session,
    de: date,
    ate: date,
    sala_ids: Sequence[int] | None,
    professor_id: int | None,
    status: str,
) -> list[Reserva]:
    stmt = _ordenado_por_sala(select(Reserva)).where(Reserva.data >= de, Reserva.data <= ate)
    if sala_ids:
        stmt = stmt.where(Reserva.sala_id.in_(list(sala_ids)))
    if professor_id is not None:
        stmt = stmt.where(Reserva.professor_id == professor_id)
    if status != "todas":
        stmt = stmt.where(Reserva.status == status)
    stmt = stmt.order_by(Reserva.data, Reserva.inicio, Sala.nome, Reserva.id)
    return list(db.scalars(stmt).unique())


def listar_minhas(db: Session, usuario: Professor, periodo: str, status: str) -> list[Reserva]:
    ref = agora()
    hoje, hora = ref.date(), ref.time()
    nao_terminou = or_(Reserva.data > hoje, and_(Reserva.data == hoje, Reserva.fim > hora))

    stmt = select(Reserva).where(Reserva.professor_id == usuario.id)
    if status != "todas":
        stmt = stmt.where(Reserva.status == status)
    if periodo == "futuras":
        stmt = stmt.where(nao_terminou).order_by(Reserva.data, Reserva.inicio, Reserva.id)
    else:
        if periodo == "passadas":
            stmt = stmt.where(~nao_terminou)
        stmt = stmt.order_by(Reserva.data.desc(), Reserva.inicio.desc(), Reserva.id.desc())
    return list(db.scalars(stmt).unique())


def obter(db: Session, reserva_id: int) -> Reserva:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise nao_encontrado("Reserva não encontrada.")
    return reserva


def obter_grupo(db: Session, grupo_id: int, usuario: Professor) -> GrupoRecorrencia:
    grupo = db.get(GrupoRecorrencia, grupo_id)
    if grupo is None:
        raise nao_encontrado("Grupo de recorrência não encontrado.")
    if not usuario.eh_admin and grupo.professor_id != usuario.id:
        raise sem_permissao("Esta reserva recorrente é de outro professor.")
    return grupo


def reservas_do_grupo(db: Session, grupo_id: int, recarregar: bool = False) -> list[Reserva]:
    """Ocorrências do grupo por data, numa consulta só.

    `recarregar=True` sobrescreve os objetos já na sessão (ex.: logo após o commit da criação, quando
    `criado_em` e os relacionamentos ainda não foram carregados).
    """
    stmt = (
        select(Reserva)
        .where(Reserva.grupo_recorrencia_id == grupo_id)
        .order_by(Reserva.data, Reserva.inicio, Reserva.id)
    )
    if recarregar:
        stmt = stmt.execution_options(populate_existing=True)
    return list(db.scalars(stmt).unique())


# ---------------------------------------------------------------- cancelamento (RN07)
def _marcar_cancelada(r: Reserva, usuario: Professor, motivo: str | None) -> None:
    r.status = "cancelada"
    r.cancelada_em = agora_tz()
    r.cancelada_por_id = usuario.id
    r.motivo_cancelamento = motivo


def cancelar(db: Session, reserva_id: int, usuario: Professor, motivo: str | None) -> Reserva:
    reserva = db.scalars(
        select(Reserva).where(Reserva.id == reserva_id).with_for_update(of=Reserva)
    ).unique().first()
    if reserva is None:
        raise nao_encontrado("Reserva não encontrada.")
    if not usuario.eh_admin and reserva.professor_id != usuario.id:
        raise sem_permissao("Você só pode cancelar as suas reservas.")
    if reserva.status == "cancelada":
        raise ErroApi(409, "RESERVA_JA_CANCELADA", "Esta reserva já foi cancelada.")
    if not usuario.eh_admin and agora() >= momento(reserva.data, reserva.inicio):
        raise ErroApi(422, "RESERVA_JA_INICIADA", "A aula já começou; não é mais possível cancelar.")

    _marcar_cancelada(reserva, usuario, motivo)
    db.commit()
    db.refresh(reserva)
    return reserva


def cancelar_grupo(db: Session, grupo_id: int, usuario: Professor, motivo: str | None) -> list[int]:
    obter_grupo(db, grupo_id, usuario)
    ref = agora()
    candidatas = db.scalars(
        select(Reserva)
        .where(Reserva.grupo_recorrencia_id == grupo_id, Reserva.status == "ativa")
        .order_by(Reserva.data, Reserva.inicio)
        .with_for_update(of=Reserva)
    ).unique()
    ids: list[int] = []
    for r in candidatas:
        if momento(r.data, r.inicio) > ref:
            _marcar_cancelada(r, usuario, motivo)
            ids.append(r.id)
    db.commit()
    return ids
