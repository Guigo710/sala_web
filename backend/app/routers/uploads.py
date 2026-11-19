"""Entrega das fotos guardadas no banco (ADR-0010, contrato §1.9 e §4.1).

Substitui o `StaticFiles` sobre `UPLOAD_DIR`: a URL continua `/uploads/salas/{sala_id}/{uuid}.jpg`, mas os bytes
vêm de `fotos_sala.conteudo`. O nome tem um UUID e o conteúdo de um nome nunca muda, então a resposta pode ficar
em cache por um ano (`immutable`) e o `ETag` é o próprio UUID.
"""

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.erros import nao_encontrado
from app.core.middlewares import CACHE_UPLOADS
from app.models import FotoSala
from app.services import fotos as servico

router = APIRouter(tags=["fotos"])


def _etag(arquivo: str) -> str:
    """ETag forte com o UUID do nome (`salas/3/<uuid>.jpg` → `"<uuid>"`)."""
    nome = arquivo.rsplit("/", 1)[-1]
    return '"' + nome.rsplit(".", 1)[0] + '"'


def _bate_com(if_none_match: str | None, etag: str) -> bool:
    """`If-None-Match` com o mesmo ETag (aceita lista, `W/` e `*`)."""
    if not if_none_match:
        return False
    for item in if_none_match.split(","):
        item = item.strip()
        if item == "*" or item.removeprefix("W/") == etag:
            return True
    return False


@router.get(
    "/uploads/{arquivo:path}",
    summary="Foto de um ambiente (bytes lidos do banco)",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "A foto"}, 304: {"description": "Não mudou"}},
)
def foto(arquivo: str, request: Request) -> Response:
    etag = _etag(arquivo)
    cabecalhos = {"ETag": etag, "Cache-Control": CACHE_UPLOADS}
    # Sessão curta, sem usuário e sem carregar a sala.
    with SessionLocal() as db:
        if _bate_com(request.headers.get("if-none-match"), etag):
            existe = db.scalar(
                select(FotoSala.id).where(FotoSala.arquivo == arquivo, FotoSala.conteudo.is_not(None))
            )
            if existe is not None:
                return Response(status_code=304, headers=cabecalhos)
            raise nao_encontrado("Foto não encontrada.")
        achado = servico.obter_conteudo(db, arquivo)
    if achado is None:
        raise nao_encontrado("Foto não encontrada.")
    conteudo, tipo = achado
    return Response(content=conteudo, media_type=tipo, headers=cabecalhos)
