"""Grade de aulas (contrato §4.8, RN02)."""

from sqlalchemy import SmallInteger, any_, cast, exists, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from app.core.erros import ErroApi
from app.models import HorarioAula, Professor, Reserva
from app.schemas.horarios import HorarioAtualizar, HorarioEntrada
from app.services.aulas import ordem_turno_sql
from app.services.comum import commit_traduzindo, obter_ou_404


def _erro_ordem() -> ErroApi:
    return ErroApi(409, "ORDEM_DUPLICADA", "Já existe uma aula com esta ordem neste turno.")


def _erro_em_uso() -> ErroApi:
    return ErroApi(409, "HORARIO_EM_USO", "Esta aula já foi usada em reservas. Desative-a (ativo = false).")


def _checar(db: Session, entrada: HorarioEntrada, ignorar_id: int | None = None) -> None:
    """`ORDEM_DUPLICADA` e RN02 (`HORARIO_SOBREPOSTO` com outra aula ativa em dia comum)."""
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


def _salvar(db: Session, h: HorarioAula) -> HorarioAula:
    commit_traduzindo(db, {"uq_horarios_turno_ordem": _erro_ordem()})
    db.refresh(h)
    return h


def listar(
    db: Session,
    usuario: Professor | None,
    dia_semana: int | None = None,
    turno: str | None = None,
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


def obter(db: Session, horario_id: int) -> HorarioAula:
    return obter_ou_404(db, HorarioAula, horario_id, "Aula não encontrada.")


def criar(db: Session, entrada: HorarioEntrada) -> HorarioAula:
    _checar(db, entrada)
    h = HorarioAula(**entrada.model_dump())
    db.add(h)
    return _salvar(db, h)


def atualizar(db: Session, horario_id: int, entrada: HorarioAtualizar) -> HorarioAula:
    h = obter(db, horario_id)
    _checar(db, entrada, ignorar_id=h.id)
    for campo, valor in entrada.model_dump().items():
        setattr(h, campo, valor)
    return _salvar(db, h)


def excluir(db: Session, horario_id: int) -> None:
    """Só aulas que não são início/fim de nenhuma reserva (a do meio de um bloco pode sair, ADR-0002)."""
    h = obter(db, horario_id)
    if db.scalar(select(exists().where(or_(Reserva.horario_inicio_id == h.id, Reserva.horario_fim_id == h.id)))):
        raise _erro_em_uso()
    db.delete(h)
    commit_traduzindo(
        db, {"reservas_horario_inicio_id_fkey": _erro_em_uso(), "reservas_horario_fim_id_fkey": _erro_em_uso()}
    )
