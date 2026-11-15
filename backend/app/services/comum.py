"""Apoio comum aos services: busca por id, commit com tradução de constraint e escape de LIKE."""

from collections.abc import Mapping
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import ErroApi, nao_encontrado, nome_constraint

T = TypeVar("T")


def obter_ou_404(db: Session, modelo: type[T], id_: int, mensagem: str) -> T:
    """Linha por chave primária ou `404 NAO_ENCONTRADO` com a mensagem dada."""
    obj = db.get(modelo, id_)
    if obj is None:
        raise nao_encontrado(mensagem)
    return obj


def commit_traduzindo(db: Session, erros: Mapping[str, ErroApi] | None = None) -> None:
    """`db.commit()`; se o banco recusar, faz rollback e devolve o `ErroApi` da constraint violada.

    As pré-checagens dos services dão as mensagens amigáveis; a constraint do banco é a garantia final
    (corridas entre duas requisições). Constraint fora de `erros` (FK, CHECK inesperados) é relançada e vira
    `500 ERRO_INTERNO` com log, em vez de um 409 com mensagem errada.
    """
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        erro = (erros or {}).get(nome_constraint(e) or "")
        if erro is None:
            raise
        raise erro from None


def escapar_like(texto: str) -> str:
    """Escapa `\\`, `%` e `_` para uso literal em LIKE/ILIKE com `escape="\\\\"`."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
