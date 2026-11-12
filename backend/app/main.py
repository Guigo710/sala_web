"""Aplicação FastAPI do sala_web."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import obter_config
from app.core.db import SessionLocal
from app.core.erros import registrar_handlers
from app.routers import auth, equipamentos, fotos, horarios, professores, reservas, salas, semestres, softwares

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def criar_app() -> FastAPI:
    config = obter_config()
    app = FastAPI(
        title="sala_web",
        description="API de reserva de salas e laboratórios (contrato em docs/api-contrato.md).",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    registrar_handlers(app)

    # Upload de foto: recusa cedo (pelo Content-Length) o que certamente passa do limite,
    # antes de o corpo inteiro ser recebido. O limite exato é conferido no service (ADR-0005).
    folga_multipart = 512 * 1024

    @app.middleware("http")
    async def limitar_upload(request: Request, call_next):  # noqa: ANN001, ANN202
        if request.method == "POST" and request.url.path.endswith("/fotos"):
            tamanho = request.headers.get("content-length", "")
            if tamanho.isdigit() and int(tamanho) > config.upload_max_bytes + folga_multipart:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"A foto passa do limite de {config.UPLOAD_MAX_MB} MB.",
                        "codigo": "ARQUIVO_GRANDE",
                    },
                )
        return await call_next(request)

    @app.get("/saude", tags=["saúde"], summary="Saúde da API e do banco")
    def saude() -> JSONResponse:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            logging.getLogger("sala_web").exception("Banco indisponível")
            return JSONResponse(status_code=503, content={"status": "erro"})
        return JSONResponse(content={"status": "ok"})

    for modulo in (auth, salas, fotos, equipamentos, softwares, professores, horarios, semestres, reservas):
        app.include_router(modulo.router)

    pasta_uploads = config.upload_dir
    pasta_uploads.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=pasta_uploads), name="uploads")
    return app


app = criar_app()
