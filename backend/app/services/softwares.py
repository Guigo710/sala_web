"""Catálogo de softwares (contrato §4.6)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi
from app.models import Software
from app.schemas.softwares import SoftwareEntrada
from app.services.comum import commit_traduzindo, escapar_like, obter_ou_404


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", "Já existe um software com este nome e versão.")


def _checar_duplicado(db: Session, entrada: SoftwareEntrada, ignorar_id: int | None = None) -> None:
    stmt = select(Software.id).where(
        Software.nome == entrada.nome, Software.versao.is_not_distinct_from(entrada.versao)
    )
    if ignorar_id is not None:
        stmt = stmt.where(Software.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise _duplicado()


def _salvar(db: Session, sw: Software) -> Software:
    commit_traduzindo(db, {"uq_softwares_nome_versao": _duplicado()})
    db.refresh(sw)
    return sw


def listar(db: Session, busca: str | None = None, categoria: str | None = None) -> list[Software]:
    stmt = select(Software)
    if busca and busca.strip():
        stmt = stmt.where(Software.nome.ilike(f"%{escapar_like(busca.strip())}%", escape="\\"))
    if categoria and categoria.strip():
        stmt = stmt.where(Software.categoria == categoria.strip())
    stmt = stmt.order_by(func.lower(Software.nome), Software.versao.nulls_first(), Software.id)
    return list(db.scalars(stmt))


def categorias(db: Session) -> list[str]:
    stmt = select(Software.categoria).where(Software.categoria.is_not(None)).distinct().order_by(Software.categoria)
    return list(db.scalars(stmt))


def obter(db: Session, software_id: int) -> Software:
    return obter_ou_404(db, Software, software_id, "Software não encontrado.")


def criar(db: Session, entrada: SoftwareEntrada) -> Software:
    _checar_duplicado(db, entrada)
    sw = Software(**entrada.model_dump())
    db.add(sw)
    return _salvar(db, sw)


def atualizar(db: Session, software_id: int, entrada: SoftwareEntrada) -> Software:
    sw = obter(db, software_id)
    _checar_duplicado(db, entrada, ignorar_id=sw.id)
    sw.nome, sw.versao, sw.categoria = entrada.nome, entrada.versao, entrada.categoria
    return _salvar(db, sw)


def excluir(db: Session, software_id: int) -> None:
    db.delete(obter(db, software_id))  # associações caem por ON DELETE CASCADE
    commit_traduzindo(db)
