from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, nao_encontrado
from app.core.seguranca import Admin, Db
from app.models import Software
from app.schemas.softwares import Software as SoftwareSaida
from app.schemas.softwares import SoftwareEntrada
from app.services.salas import escapar_like

router = APIRouter(prefix="/softwares", tags=["softwares"])

_DUPLICADO = "Já existe um software com este nome e versão."


def _obter(db: Db, software_id: int) -> Software:
    sw = db.get(Software, software_id)
    if sw is None:
        raise nao_encontrado("Software não encontrado.")
    return sw


def _checar_duplicado(db: Db, entrada: SoftwareEntrada, ignorar_id: int | None = None) -> None:
    stmt = select(Software.id).where(
        Software.nome == entrada.nome, Software.versao.is_not_distinct_from(entrada.versao)
    )
    if ignorar_id is not None:
        stmt = stmt.where(Software.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise ErroApi(409, "NOME_DUPLICADO", _DUPLICADO)


def _salvar(db: Db, sw: Software) -> Software:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroApi(409, "NOME_DUPLICADO", _DUPLICADO) from None
    db.refresh(sw)
    return sw


@router.get("", response_model=list[SoftwareSaida])
def listar(db: Db, busca: str | None = None, categoria: str | None = None) -> list[Software]:
    stmt = select(Software)
    if busca and busca.strip():
        stmt = stmt.where(Software.nome.ilike(f"%{escapar_like(busca.strip())}%", escape="\\"))
    if categoria and categoria.strip():
        stmt = stmt.where(Software.categoria == categoria.strip())
    stmt = stmt.order_by(func.lower(Software.nome), Software.versao.nulls_first(), Software.id)
    return list(db.scalars(stmt))


@router.get("/categorias", response_model=list[str])
def categorias(db: Db) -> list[str]:
    stmt = select(Software.categoria).where(Software.categoria.is_not(None)).distinct().order_by(Software.categoria)
    return list(db.scalars(stmt))


@router.get("/{software_id}", response_model=SoftwareSaida)
def obter(software_id: int, db: Db) -> Software:
    return _obter(db, software_id)


@router.post("", response_model=SoftwareSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: SoftwareEntrada, db: Db, _: Admin) -> Software:
    _checar_duplicado(db, entrada)
    sw = Software(**entrada.model_dump())
    db.add(sw)
    return _salvar(db, sw)


@router.put("/{software_id}", response_model=SoftwareSaida)
def atualizar(software_id: int, entrada: SoftwareEntrada, db: Db, _: Admin) -> Software:
    sw = _obter(db, software_id)
    _checar_duplicado(db, entrada, ignorar_id=sw.id)
    sw.nome, sw.versao, sw.categoria = entrada.nome, entrada.versao, entrada.categoria
    return _salvar(db, sw)


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(software_id: int, db: Db, _: Admin) -> None:
    db.delete(_obter(db, software_id))  # associações caem por ON DELETE CASCADE
    db.commit()
