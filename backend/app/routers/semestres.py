from fastapi import APIRouter, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, nao_encontrado, nome_constraint
from app.core.seguranca import Admin, Db
from app.core.tempo import hoje
from app.models import GrupoRecorrencia, Semestre
from app.schemas.comum import Semestre as SemestreSaida
from app.schemas.semestres import SemestreEntrada

router = APIRouter(prefix="/semestres", tags=["semestres"])


def _obter(db: Db, semestre_id: int) -> Semestre:
    s = db.get(Semestre, semestre_id)
    if s is None:
        raise nao_encontrado("Semestre não encontrado.")
    return s


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", "Já existe um semestre com este nome.")


def _sobreposto() -> ErroApi:
    return ErroApi(409, "SEMESTRE_SOBREPOSTO", "As datas se sobrepõem a outro semestre cadastrado.")


def _checar(db: Db, entrada: SemestreEntrada, ignorar_id: int | None = None) -> None:
    filtro_id = [Semestre.id != ignorar_id] if ignorar_id is not None else []
    if db.scalar(select(Semestre.id).where(Semestre.nome == entrada.nome, *filtro_id)) is not None:
        raise _duplicado()
    sobreposto = select(Semestre.id).where(
        Semestre.data_inicio <= entrada.data_fim, Semestre.data_fim >= entrada.data_inicio, *filtro_id
    )
    if db.scalar(sobreposto) is not None:
        raise _sobreposto()


def _salvar(db: Db, s: Semestre) -> Semestre:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if nome_constraint(e) == "ex_semestres_sem_sobreposicao":
            raise _sobreposto() from None
        raise _duplicado() from None
    db.refresh(s)
    return s


@router.get("", response_model=list[SemestreSaida])
def listar(db: Db) -> list[Semestre]:
    return list(db.scalars(select(Semestre).order_by(Semestre.data_inicio.desc())))


@router.get("/atual", response_model=SemestreSaida, summary="Semestre que contém hoje (ou o próximo)")
def atual(db: Db) -> Semestre:
    d = hoje()
    s = db.scalars(select(Semestre).where(Semestre.data_inicio <= d, Semestre.data_fim >= d)).first()
    if s is None:
        s = db.scalars(
            select(Semestre).where(Semestre.data_inicio > d).order_by(Semestre.data_inicio)
        ).first()
    if s is None:
        raise nao_encontrado("Nenhum semestre atual ou futuro cadastrado.")
    return s


@router.get("/{semestre_id}", response_model=SemestreSaida)
def obter(semestre_id: int, db: Db) -> Semestre:
    return _obter(db, semestre_id)


@router.post("", response_model=SemestreSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: SemestreEntrada, db: Db, _: Admin) -> Semestre:
    _checar(db, entrada)
    s = Semestre(**entrada.model_dump())
    db.add(s)
    return _salvar(db, s)


@router.put("/{semestre_id}", response_model=SemestreSaida)
def atualizar(semestre_id: int, entrada: SemestreEntrada, db: Db, _: Admin) -> Semestre:
    s = _obter(db, semestre_id)
    _checar(db, entrada, ignorar_id=s.id)
    s.nome, s.data_inicio, s.data_fim = entrada.nome, entrada.data_inicio, entrada.data_fim
    return _salvar(db, s)


@router.delete("/{semestre_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(semestre_id: int, db: Db, _: Admin) -> None:
    s = _obter(db, semestre_id)
    em_uso = ErroApi(409, "SEMESTRE_EM_USO", "Há reservas recorrentes neste semestre; ele não pode ser excluído.")
    if db.scalar(select(exists().where(GrupoRecorrencia.semestre_id == s.id))):
        raise em_uso
    db.delete(s)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise em_uso from None
