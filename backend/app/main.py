"""Aplicação FastAPI do sala_web."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import obter_config
from app.core.db import SessionLocal
from app.core.erros import registrar_handlers
from app.core.middlewares import CabecalhosSeguranca, ErroInterno, LimiteCorpo
from app.routers import (
    auth,
    equipamentos,
    fotos,
    horarios,
    professores,
    reservas,
    salas,
    semestres,
    softwares,
    uploads,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

# Corpo máximo das rotas que não são upload de foto (ticket 40). O maior corpo legítimo da API
# (recorrência com ~20 datas, listas de ids) tem poucos KB.
LIMITE_CORPO_PADRAO = 1024 * 1024


def criar_app() -> FastAPI:
    config = obter_config()
    log = logging.getLogger("sala_web")
    if config.banco_com_senha_de_exemplo:
        log.warning(
            "A senha do banco ainda é a de exemplo do .env.example (POSTGRES_PASSWORD). Troque-a "
            "(ALTER USER ... PASSWORD no Postgres e no .env). A porta do banco só é publicada em 127.0.0.1."
        )
    app = FastAPI(
        title="sala_web",
        description="API de reserva de salas e laboratórios (contrato em docs/api-contrato.md).",
        version="1.0.0",
        # Rotas não têm barra final (contrato §1.1). Sem isto, `/salas/` viraria `307` para `http://...`:
        # atrás do proxy do Render o esquema visto é http. Com isto, `/salas/` responde 404 (ticket 62).
        redirect_slashes=False,
    )

    registrar_handlers(app)

    # Middlewares, adicionados de dentro para fora (o último adicionado fica por fora; ver
    # app/core/middlewares.py). O CORS é o mais externo dos nossos: 413 antecipado e 500 também levam
    # os cabeçalhos CORS (contrato §1.5, ticket 30).
    # Upload: UPLOAD_MAX_MB + folga do multipart; o limite exato do arquivo é conferido no service (ADR-0005).
    folga_multipart = 512 * 1024
    app.add_middleware(
        LimiteCorpo,
        limite_upload=config.upload_max_bytes + folga_multipart,
        mensagem_upload=f"A foto passa do limite de {config.UPLOAD_MAX_MB} MB.",
        limite_padrao=LIMITE_CORPO_PADRAO,
    )
    app.add_middleware(ErroInterno)
    app.add_middleware(CabecalhosSeguranca)
    # Origens já normalizadas e validadas em Config (sem barra final, nunca "*"; ADR-0009, ticket 62).
    log.info("CORS liberado para: %s", ", ".join(config.cors_origens) or "(nenhuma origem)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/saude", tags=["saúde"], summary="Saúde da API e do banco")
    def saude() -> JSONResponse:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception as erro:  # noqa: BLE001
            # Sem a URL nem o traceback (a mensagem do driver pode trazer a string de conexão): só host e tipo.
            log.error("Banco indisponível em %s (%s)", config.host_banco, type(erro).__name__)
            return JSONResponse(status_code=503, content={"status": "erro"})
        return JSONResponse(content={"status": "ok"})

    # /uploads/{arquivo}: fotos lidas do banco (ADR-0010), no lugar do antigo StaticFiles sobre UPLOAD_DIR.
    for modulo in (auth, salas, fotos, uploads, equipamentos, softwares, professores, horarios, semestres, reservas):
        app.include_router(modulo.router)
    return app


app = criar_app()
