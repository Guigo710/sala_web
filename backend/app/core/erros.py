"""Envelope de erro da API (contrato §1.4) e handlers globais."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("sala_web")


class ErroApi(Exception):
    """Erro de negócio: vira `{"detail", "codigo", **extras}` com o status indicado."""

    def __init__(self, status: int, codigo: str, detail: str, **extras: Any) -> None:
        super().__init__(detail)
        self.status = status
        self.codigo = codigo
        self.detail = detail
        self.extras = extras


# Atalhos usados pelos services/rotas
def nao_encontrado(detail: str = "Recurso não encontrado.") -> ErroApi:
    return ErroApi(404, "NAO_ENCONTRADO", detail)


def sem_permissao(detail: str = "Você não tem permissão para esta operação.") -> ErroApi:
    return ErroApi(403, "SEM_PERMISSAO", detail)


def erro_validacao(campo: str, mensagem: str, detail: str | None = None) -> ErroApi:
    return ErroApi(
        422,
        "VALIDACAO",
        detail or f"Dados inválidos: {mensagem}.",
        erros=[{"campo": campo, "mensagem": mensagem}],
    )


def nome_constraint(erro: IntegrityError) -> str | None:
    diag = getattr(erro.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def sqlstate(erro: IntegrityError) -> str | None:
    return getattr(erro.orig, "sqlstate", None)


# ---------------------------------------------------------------- validação
def _mensagem_pt(e: dict[str, Any]) -> str:
    tipo = e.get("type", "")
    ctx = e.get("ctx") or {}
    msg = e.get("msg", "")
    traducoes = {
        "missing": "campo obrigatório",
        "json_invalid": "JSON inválido",
        "int_parsing": "deve ser um número inteiro",
        "int_type": "deve ser um número inteiro",
        "int_from_float": "deve ser um número inteiro",
        "bool_parsing": "deve ser verdadeiro ou falso",
        "bool_type": "deve ser verdadeiro ou falso",
        "string_type": "deve ser um texto",
        "list_type": "deve ser uma lista",
        "dict_type": "deve ser um objeto",
        "model_attributes_type": "deve ser um objeto",
        "model_type": "deve ser um objeto",
        "date_parsing": "data inválida (use AAAA-MM-DD)",
        "date_from_datetime_parsing": "data inválida (use AAAA-MM-DD)",
        "date_from_datetime_inexact": "data inválida (use AAAA-MM-DD)",
        "date_type": "data inválida (use AAAA-MM-DD)",
        "time_parsing": "hora inválida (use HH:MM)",
        "time_type": "hora inválida (use HH:MM)",
        "string_pattern_mismatch": "formato inválido",
        "extra_forbidden": "campo não permitido",
        "enum": "valor inválido",
        "uuid_parsing": "identificador inválido",
    }
    if tipo in traducoes:
        return traducoes[tipo]
    if tipo == "string_too_short":
        n = ctx.get("min_length", 1)
        return "não pode ficar vazio" if n == 1 else f"deve ter pelo menos {n} caracteres"
    if tipo == "string_too_long":
        return f"deve ter no máximo {ctx.get('max_length')} caracteres"
    if tipo == "too_short":
        return f"deve ter pelo menos {ctx.get('min_length')} item(ns)"
    if tipo == "too_long":
        return f"deve ter no máximo {ctx.get('max_length')} item(ns)"
    if tipo == "greater_than":
        return f"deve ser maior que {ctx.get('gt')}"
    if tipo == "greater_than_equal":
        return f"deve ser maior ou igual a {ctx.get('ge')}"
    if tipo == "less_than":
        return f"deve ser menor que {ctx.get('lt')}"
    if tipo == "less_than_equal":
        return f"deve ser menor ou igual a {ctx.get('le')}"
    if tipo == "literal_error":
        return f"valor inválido; use um de: {str(ctx.get('expected')).replace(' or ', ' ou ')}"
    if tipo in ("value_error", "assertion_error"):
        texto = str(ctx.get("error") or msg)
        if "email" in texto.lower():
            return "e-mail inválido"
        for prefixo in ("Value error, ", "Assertion failed, "):
            texto = texto.removeprefix(prefixo)
        return texto
    return msg


def _campo(loc: tuple[Any, ...] | list[Any]) -> str:
    return ".".join(str(p) for p in loc)


def formatar_erros_validacao(erros: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"campo": _campo(e.get("loc", ())), "mensagem": _mensagem_pt(e)} for e in erros]


# ---------------------------------------------------------------- handlers
_CODIGOS_HTTP = {
    400: "REQUISICAO_INVALIDA",
    401: "NAO_AUTENTICADO",
    403: "SEM_PERMISSAO",
    404: "NAO_ENCONTRADO",
    405: "METODO_NAO_PERMITIDO",
    413: "ARQUIVO_GRANDE",
    415: "TIPO_ARQUIVO_INVALIDO",
}
_MENSAGENS_HTTP = {
    401: "Faça login para continuar.",
    403: "Você não tem permissão para esta operação.",
    404: "Recurso não encontrado.",
    405: "Método não permitido nesta rota.",
}


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroApi)
    async def _erro_api(_: Request, exc: ErroApi) -> JSONResponse:
        corpo = {"detail": exc.detail, "codigo": exc.codigo, **exc.extras}
        return JSONResponse(status_code=exc.status, content=corpo)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
        erros = formatar_erros_validacao(list(exc.errors()))
        detail = "Dados inválidos."
        if erros:
            detail = f"Dados inválidos: {erros[0]['campo']} {erros[0]['mensagem']}."
        return JSONResponse(
            status_code=422, content={"detail": detail, "codigo": "VALIDACAO", "erros": erros}
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigo = _CODIGOS_HTTP.get(exc.status_code, "ERRO_HTTP")
        detail = _MENSAGENS_HTTP.get(exc.status_code)
        if detail is None:
            detail = exc.detail if isinstance(exc.detail, str) else "Erro na requisição."
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "codigo": codigo},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Erro inesperado", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno no servidor. Tente novamente.", "codigo": "ERRO_INTERNO"},
        )
