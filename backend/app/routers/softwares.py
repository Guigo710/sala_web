from fastapi import APIRouter, status

from app.core.seguranca import Admin, Db
from app.schemas.softwares import Software as SoftwareSaida
from app.schemas.softwares import SoftwareEntrada
from app.services import softwares as servico

router = APIRouter(prefix="/softwares", tags=["softwares"])


@router.get("", response_model=list[SoftwareSaida])
def listar(db: Db, busca: str | None = None, categoria: str | None = None) -> list[SoftwareSaida]:
    return [SoftwareSaida.model_validate(s) for s in servico.listar(db, busca, categoria)]


@router.get("/categorias", response_model=list[str])
def categorias(db: Db) -> list[str]:
    return servico.categorias(db)


@router.get("/{software_id}", response_model=SoftwareSaida)
def obter(software_id: int, db: Db) -> SoftwareSaida:
    return SoftwareSaida.model_validate(servico.obter(db, software_id))


@router.post("", response_model=SoftwareSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: SoftwareEntrada, db: Db, _: Admin) -> SoftwareSaida:
    return SoftwareSaida.model_validate(servico.criar(db, entrada))


@router.put("/{software_id}", response_model=SoftwareSaida)
def atualizar(software_id: int, entrada: SoftwareEntrada, db: Db, _: Admin) -> SoftwareSaida:
    return SoftwareSaida.model_validate(servico.atualizar(db, software_id, entrada))


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(software_id: int, db: Db, _: Admin) -> None:
    servico.excluir(db, software_id)
