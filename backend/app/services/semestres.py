"""Semestres letivos (contrato §4.9)."""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi, nao_encontrado
from app.core.tempo import hoje
from app.models import GrupoRecorrencia, Semestre
from app.schemas.semestres import SemestreEntrada
from app.services.comum import commit_traduzindo, obter_ou_404


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", "Já existe um semestre com este nome.")


def _sobreposto() -> ErroApi:
    return ErroApi(409, "SEMESTRE_SOBREPOSTO", "As datas se sobrepõem a outro semestre cadastrado.")


def _em_uso() -> ErroApi:
    return ErroApi(409, "SEMESTRE_EM_USO", "Há reservas recorrentes neste semestre; ele não pode ser excluído.")


def _checar(db: Session, entrada: SemestreEntrada, ignorar_id: int | None = None) -> None:
    filtro_id = [Semestre.id != ignorar_id] if ignorar_id is not None else []
    if db.scalar(select(Semestre.id).where(Semestre.nome == entrada.nome, *filtro_id)) is not None:
        raise _duplicado()
    sobreposto = select(Semestre.id).where(
        Semestre.data_inicio <= entrada.data_fim, Semestre.data_fim >= entrada.data_inicio, *filtro_id
    )
    if db.scalar(sobreposto) is not None:
        raise _sobreposto()


def _salvar(db: Session, s: Semestre) -> Semestre:
    commit_traduzindo(db, {"semestres_nome_key": _duplicado(), "ex_semestres_sem_sobreposicao": _sobreposto()})
    db.refresh(s)
    return s


def listar(db: Session) -> list[Semestre]:
    return list(db.scalars(select(Semestre).order_by(Semestre.data_inicio.desc())))


def atual(db: Session) -> Semestre:
    """Semestre que contém hoje ou, se não houver, o próximo."""
    d = hoje()
    s = db.scalars(select(Semestre).where(Semestre.data_inicio <= d, Semestre.data_fim >= d)).first()
    if s is None:
        s = db.scalars(select(Semestre).where(Semestre.data_inicio > d).order_by(Semestre.data_inicio)).first()
    if s is None:
        raise nao_encontrado("Nenhum semestre atual ou futuro cadastrado.")
    return s


def obter(db: Session, semestre_id: int) -> Semestre:
    return obter_ou_404(db, Semestre, semestre_id, "Semestre não encontrado.")


def criar(db: Session, entrada: SemestreEntrada) -> Semestre:
    _checar(db, entrada)
    s = Semestre(**entrada.model_dump())
    db.add(s)
    return _salvar(db, s)


def atualizar(db: Session, semestre_id: int, entrada: SemestreEntrada) -> Semestre:
    s = obter(db, semestre_id)
    _checar(db, entrada, ignorar_id=s.id)
    s.nome, s.data_inicio, s.data_fim = entrada.nome, entrada.data_inicio, entrada.data_fim
    return _salvar(db, s)


def excluir(db: Session, semestre_id: int) -> None:
    s = obter(db, semestre_id)
    if db.scalar(select(exists().where(GrupoRecorrencia.semestre_id == s.id))):
        raise _em_uso()
    db.delete(s)
    commit_traduzindo(db, {"grupos_recorrencia_semestre_id_fkey": _em_uso()})
