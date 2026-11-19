"""Entrega das fotos guardadas no banco (ADR-0010, contrato §1.9 e §4.1).

Substitui o `StaticFiles` sobre `UPLOAD_DIR`: a URL continua `/uploads/salas/{sala_id}/{uuid}.jpg`, mas os bytes
vêm de `fotos_sala.conteudo`. O nome tem um UUID e o conteúdo de um nome nunca muda, então a resposta fica em cache
por um ano (`immutable`) e o `ETag` é o próprio UUID. `CabecalhosSeguranca` acrescenta `Content-Disposition`, a CSP
`sandbox` e `nosniff`.
"""

from fastapi import APIRouter, Request, Response

from app.core.db import SessionLocal
from app.core.middlewares import CACHE_UPLOADS
from app.services import fotos as servico

router = APIRouter(tags=["fotos"])


@router.get(
    "/uploads/{arquivo:path}",
    summary="Foto de um ambiente (bytes lidos do banco)",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "A foto"}, 304: {"description": "Não mudou"}},
)
def foto(arquivo: str, request: Request) -> Response:
    # Sessão curta e própria: a rota não precisa de usuário, e a conexão volta ao pool antes de enviar os bytes.
    with SessionLocal() as db:
        entrega = servico.entregar(db, arquivo, request.headers.get("if-none-match"))
    cabecalhos = {"ETag": entrega.etag, "Cache-Control": CACHE_UPLOADS}
    if entrega.conteudo is None:
        return Response(status_code=304, headers=cabecalhos)
    return Response(content=entrega.conteudo, media_type=entrega.tipo_mime, headers=cabecalhos)
