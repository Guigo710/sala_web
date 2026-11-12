"""Middlewares ASGI puros (tickets 30, 40 e 44).

Ordem (de fora para dentro), montada em `app.main.criar_app`:

    ServerErrorMiddleware (Starlette, última rede de segurança)
    └── CORSMiddleware                 ← o mais externo dos nossos: toda resposta abaixo ganha CORS (§1.5)
        └── CabecalhosSeguranca        ← nosniff, X-Frame-Options, Referrer-Policy (ticket 44)
            └── ErroInterno            ← exceção inesperada → 500 ERRO_INTERNO, com log (ticket 30)
                └── LimiteCorpo        ← 413 pelo Content-Length ou contando os bytes (ticket 40)
                    └── ExceptionMiddleware → rotas

No Starlette, `add_middleware` coloca o middleware por fora dos já adicionados, por isso `criar_app`
os adiciona de dentro para fora.
"""

import json
import logging
import re

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger("sala_web")

MENSAGEM_ERRO_INTERNO = "Erro interno no servidor. Tente novamente."


async def _enviar_json(send: Send, status: int, corpo: dict) -> None:
    dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(dados)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": dados})


# ---------------------------------------------------------------- 500 por dentro do CORS (ticket 30)
class ErroInterno:
    """Exceção não tratada → `500 {"detail", "codigo": "ERRO_INTERNO"}` sem stack trace no corpo.

    Fica por dentro do CORS, então o navegador recebe o envelope. O handler de `Exception` em
    `core/erros.py` (executado pelo ServerErrorMiddleware) continua como última rede de segurança.
    Se a resposta já começou a ser enviada, não há como trocá-la: a exceção segue adiante.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        iniciada = False

        async def enviar(mensagem: Message) -> None:
            nonlocal iniciada
            if mensagem["type"] == "http.response.start":
                iniciada = True
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar)
        except Exception:
            if iniciada:
                raise
            log.exception("Erro inesperado em %s %s", scope.get("method"), scope.get("path"))
            await _enviar_json(send, 500, {"detail": MENSAGEM_ERRO_INTERNO, "codigo": "ERRO_INTERNO"})


# ---------------------------------------------------------------- limite de corpo (ticket 40)
class _CorpoExcedido(Exception):
    """Interrompe a leitura do corpo quando ele passa do limite."""


_ROTA_FOTOS = re.compile(r"^/salas/[^/]+/fotos$")


class LimiteCorpo:
    """Recusa com `413` corpos acima do limite, com ou sem `Content-Length`.

    - Upload de foto (`POST /salas/{id}/fotos`): `limite_upload` (UPLOAD_MAX_MB + folga do multipart),
      código `ARQUIVO_GRANDE`. O limite exato do arquivo continua conferido no service (ADR-0005).
    - Demais rotas: `limite_padrao` (1 MB), código `CORPO_GRANDE`.

    Com `Content-Length` acima do limite responde antes de ler qualquer byte. Sem ele (chunked), conta os
    bytes entregues por `receive` e para de ler assim que passa do limite; o que a aplicação tentar
    responder depois disso é trocado pelo `413`.
    """

    def __init__(
        self,
        app: ASGIApp,
        limite_upload: int,
        mensagem_upload: str,
        limite_padrao: int = 1024 * 1024,
    ) -> None:
        self.app = app
        self.limite_upload = limite_upload
        self.mensagem_upload = mensagem_upload
        self.limite_padrao = limite_padrao

    def _regra(self, scope: Scope) -> tuple[int, dict]:
        if scope.get("method") == "POST" and _ROTA_FOTOS.match(scope.get("path", "")):
            return self.limite_upload, {"detail": self.mensagem_upload, "codigo": "ARQUIVO_GRANDE"}
        kb = self.limite_padrao // 1024
        tamanho = f"{kb // 1024} MB" if kb >= 1024 and kb % 1024 == 0 else f"{kb} KB"
        return self.limite_padrao, {
            "detail": f"A requisição passa do tamanho máximo de {tamanho}.",
            "codigo": "CORPO_GRANDE",
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limite, corpo_413 = self._regra(scope)

        for nome, valor in scope.get("headers", []):
            if nome == b"content-length":
                texto = valor.decode("latin-1").strip()
                if texto.isdigit() and int(texto) > limite:
                    await _enviar_json(send, 413, corpo_413)
                    return
                break

        recebidos = 0
        excedeu = False
        iniciada = False

        async def receber() -> Message:
            nonlocal recebidos, excedeu
            if excedeu:
                raise _CorpoExcedido
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebidos += len(mensagem.get("body", b""))
                if recebidos > limite:
                    excedeu = True
                    raise _CorpoExcedido
            return mensagem

        async def enviar(mensagem: Message) -> None:
            nonlocal iniciada
            if excedeu:
                return  # a resposta da aplicação (400/422/...) é descartada; vale o 413 abaixo
            if mensagem["type"] == "http.response.start":
                iniciada = True
            await send(mensagem)

        try:
            await self.app(scope, receber, enviar)
        except _CorpoExcedido:
            pass
        except Exception:
            if not excedeu:
                raise
        if excedeu and not iniciada:
            await _enviar_json(send, 413, corpo_413)


# ---------------------------------------------------------------- cabeçalhos de segurança (ticket 44)
class CabecalhosSeguranca:
    """`nosniff` em tudo; `X-Frame-Options`/`Referrer-Policy` em todas as respostas; e, em `/uploads`,
    `Content-Disposition: inline`, `Cache-Control` e uma CSP que impede executar qualquer coisa servida ali.
    """

    def __init__(self, app: ASGIApp, prefixo_uploads: str = "/uploads/") -> None:
        self.app = app
        self.prefixo_uploads = prefixo_uploads

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        eh_upload = scope.get("path", "").startswith(self.prefixo_uploads)

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                cab = MutableHeaders(scope=mensagem)
                cab["X-Content-Type-Options"] = "nosniff"
                cab.setdefault("X-Frame-Options", "DENY")
                cab.setdefault("Referrer-Policy", "no-referrer")
                if eh_upload and mensagem["status"] < 400:
                    cab["Content-Disposition"] = "inline"
                    cab["Content-Security-Policy"] = "default-src 'none'; sandbox"
                    # Nomes são UUIDs: o conteúdo de uma URL nunca muda.
                    cab.setdefault("Cache-Control", "public, max-age=86400")
            await send(mensagem)

        await self.app(scope, receive, enviar)
