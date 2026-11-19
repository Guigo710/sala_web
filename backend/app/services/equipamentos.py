"""Catálogo de equipamentos (contrato §4.5)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi
from app.models import Equipamento
from app.schemas.equipamentos import EquipamentoEntrada
from app.services.comum import commit_traduzindo, escapar_like, obter_ou_404


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", "Já existe um equipamento com este nome.")


def _checar_nome(db: Session, nome: str, ignorar_id: int | None = None) -> None:
    stmt = select(Equipamento.id).where(Equipamento.nome == nome)
    if ignorar_id is not None:
        stmt = stmt.where(Equipamento.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise _duplicado()


def _salvar(db: Session, eq: Equipamento) -> Equipamento:
    commit_traduzindo(db, {"equipamentos_nome_key": _duplicado()})
    db.refresh(eq)
    return eq


def listar(db: Session, busca: str | None = None) -> list[Equipamento]:
    stmt = select(Equipamento)
    if busca and busca.strip():
        stmt = stmt.where(Equipamento.nome.ilike(f"%{escapar_like(busca.strip())}%", escape="\\"))
    return list(db.scalars(stmt.order_by(func.lower(Equipamento.nome), Equipamento.id)))


def obter(db: Session, equipamento_id: int) -> Equipamento:
    return obter_ou_404(db, Equipamento, equipamento_id, "Equipamento não encontrado.")


def criar(db: Session, entrada: EquipamentoEntrada) -> Equipamento:
    _checar_nome(db, entrada.nome)
    eq = Equipamento(**entrada.model_dump())
    db.add(eq)
    return _salvar(db, eq)


def atualizar(db: Session, equipamento_id: int, entrada: EquipamentoEntrada) -> Equipamento:
    eq = obter(db, equipamento_id)
    _checar_nome(db, entrada.nome, ignorar_id=eq.id)
    eq.nome, eq.descricao = entrada.nome, entrada.descricao
    return _salvar(db, eq)


def excluir(db: Session, equipamento_id: int) -> None:
    db.delete(obter(db, equipamento_id))  # associações caem por ON DELETE CASCADE
    commit_traduzindo(db)
