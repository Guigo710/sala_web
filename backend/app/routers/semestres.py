from fastapi import APIRouter, status

from app.core.seguranca import Admin, Db
from app.schemas.comum import Semestre as SemestreSaida
from app.schemas.semestres import SemestreEntrada
from app.services import semestres as servico

router = APIRouter(prefix="/semestres", tags=["semestres"])


@router.get("", response_model=list[SemestreSaida])
def listar(db: Db) -> list[SemestreSaida]:
    return [SemestreSaida.model_validate(s) for s in servico.listar(db)]


@router.get("/atual", response_model=SemestreSaida, summary="Semestre que contém hoje (ou o próximo)")
def atual(db: Db) -> SemestreSaida:
    return SemestreSaida.model_validate(servico.atual(db))


@router.get("/{semestre_id}", response_model=SemestreSaida)
def obter(semestre_id: int, db: Db) -> SemestreSaida:
    return SemestreSaida.model_validate(servico.obter(db, semestre_id))


@router.post("", response_model=SemestreSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: SemestreEntrada, db: Db, _: Admin) -> SemestreSaida:
    return SemestreSaida.model_validate(servico.criar(db, entrada))


@router.put("/{semestre_id}", response_model=SemestreSaida)
def atualizar(semestre_id: int, entrada: SemestreEntrada, db: Db, _: Admin) -> SemestreSaida:
    return SemestreSaida.model_validate(servico.atualizar(db, semestre_id, entrada))


@router.delete("/{semestre_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(semestre_id: int, db: Db, _: Admin) -> None:
    servico.excluir(db, semestre_id)
