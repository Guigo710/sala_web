from typing import Literal

from fastapi import APIRouter, Query, status
from sqlalchemy import SmallInteger, any_, cast, exists, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, nao_encontrado
from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.models import HorarioAula, Reserva
from app.schemas.comum import HorarioAula as HorarioSaida
from app.schemas.horarios import HorarioEntrada
from app.services.aulas import ordem_turno_sql

router = APIRouter(prefix="/horarios", tags=["horários"])


def _obter(db: Db, horario_id: int) -> HorarioAula:
    h = db.get(HorarioAula, horario_id)
    if h is None:
        raise nao_encontrado("Aula não encontrada.")
    return h


def _erro_ordem() -> ErroApi:
    return ErroApi(409, "ORDEM_DUPLICADA", "Já existe uma aula com esta ordem neste turno.")


def _checar(db: Db, entrada: HorarioEntrada, ignorar_id: int | None = None) -> None:
    stmt = select(HorarioAula.id).where(HorarioAula.turno == entrada.turno, HorarioAula.ordem == entrada.ordem)
    if ignorar_id is not None:
        stmt = stmt.where(HorarioAula.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise _erro_ordem()
    if not entrada.ativo:
        return
    stmt = select(HorarioAula).where(
        HorarioAula.ativo.is_(True),
        HorarioAula.dias_semana.overlap(cast(entrada.dias_semana, ARRAY(SmallInteger))),
        HorarioAula.inicio < entrada.fim,
        HorarioAula.fim > entrada.inicio,
    )
    if ignorar_id is not None:
        stmt = stmt.where(HorarioAula.id != ignorar_id)
    outra = db.scalars(stmt).first()
    if outra is not None:
        raise ErroApi(
            409,
            "HORARIO_SOBREPOSTO",
            f"Este horário se sobrepõe à {outra.ordem}ª aula do turno {outra.turno} "
            f"({outra.inicio:%H:%M}–{outra.fim:%H:%M}) em um dia em comum.",
        )


def _salvar(db: Db, h: HorarioAula) -> HorarioAula:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _erro_ordem() from None
    db.refresh(h)
    return h


@router.get("", response_model=list[HorarioSaida])
def listar(
    db: Db,
    usuario: UsuarioOpcional,
    dia_semana: int | None = Query(None, ge=1, le=7),
    turno: Literal["manha", "tarde", "noite"] | None = None,
    incluir_inativos: bool = False,
) -> list[HorarioAula]:
    stmt = select(HorarioAula)
    if not (incluir_inativos and usuario is not None and usuario.eh_admin):
        stmt = stmt.where(HorarioAula.ativo.is_(True))
    if dia_semana is not None:
        stmt = stmt.where(literal(dia_semana, SmallInteger) == any_(HorarioAula.dias_semana))
    if turno is not None:
        stmt = stmt.where(HorarioAula.turno == turno)
    return list(db.scalars(stmt.order_by(ordem_turno_sql, HorarioAula.ordem)))


@router.get("/{horario_id}", response_model=HorarioSaida)
def obter(horario_id: int, db: Db) -> HorarioAula:
    return _obter(db, horario_id)


@router.post("", response_model=HorarioSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: HorarioEntrada, db: Db, _: Admin) -> HorarioAula:
    _checar(db, entrada)
    h = HorarioAula(**entrada.model_dump())
    db.add(h)
    return _salvar(db, h)


@router.put("/{horario_id}", response_model=HorarioSaida)
def atualizar(horario_id: int, entrada: HorarioEntrada, db: Db, _: Admin) -> HorarioAula:
    h = _obter(db, horario_id)
    _checar(db, entrada, ignorar_id=h.id)
    for campo, valor in entrada.model_dump().items():
        setattr(h, campo, valor)
    return _salvar(db, h)


@router.delete("/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(horario_id: int, db: Db, _: Admin) -> None:
    h = _obter(db, horario_id)
    em_uso = ErroApi(409, "HORARIO_EM_USO", "Esta aula já foi usada em reservas. Desative-a (ativo = false).")
    if db.scalar(
        select(exists().where(or_(Reserva.horario_inicio_id == h.id, Reserva.horario_fim_id == h.id)))
    ):
        raise em_uso
    db.delete(h)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise em_uso from None
