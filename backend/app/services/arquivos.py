"""Fotos em disco (ADR-0005): validação por assinatura, gravação e remoção."""

import logging
import shutil
import uuid
from pathlib import Path

from app.core.config import obter_config
from app.core.erros import ErroApi

log = logging.getLogger("sala_web")

_TAMANHO_BLOCO = 64 * 1024


def tipo_por_assinatura(cabecalho: bytes) -> str | None:
    """Extensão pelo conteúdo (magic bytes): jpg, png, webp ou None."""
    if cabecalho.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if cabecalho.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(cabecalho) >= 12 and cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP":
        return "webp"
    return None


def ler_limitado(arquivo, limite: int) -> bytes:  # noqa: ANN001
    """Lê em blocos; passa do limite → 413 (nada é gravado em disco)."""
    partes: list[bytes] = []
    total = 0
    while True:
        bloco = arquivo.read(_TAMANHO_BLOCO)
        if not bloco:
            break
        total += len(bloco)
        if total > limite:
            raise ErroApi(
                413, "ARQUIVO_GRANDE", f"A foto passa do limite de {obter_config().UPLOAD_MAX_MB} MB."
            )
        partes.append(bloco)
    return b"".join(partes)


def caminho_absoluto(relativo: str) -> Path:
    base = obter_config().upload_dir
    caminho = (base / relativo).resolve()
    if base not in caminho.parents:
        raise ValueError("caminho fora de UPLOAD_DIR")
    return caminho


def gravar_foto(sala_id: int, conteudo: bytes) -> str:
    """Grava a foto e devolve o caminho relativo `salas/{id}/{uuid}.{ext}`."""
    ext = tipo_por_assinatura(conteudo[:16])
    if ext is None:
        raise ErroApi(415, "TIPO_ARQUIVO_INVALIDO", "Envie uma imagem JPEG, PNG ou WebP.")
    relativo = f"salas/{sala_id}/{uuid.uuid4()}.{ext}"
    destino = caminho_absoluto(relativo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(destino)
    return relativo


def apagar_arquivo(relativo: str) -> None:
    try:
        caminho_absoluto(relativo).unlink(missing_ok=True)
    except (OSError, ValueError):
        log.warning("Não foi possível apagar o arquivo %s", relativo, exc_info=True)


def apagar_pasta_sala(sala_id: int) -> None:
    try:
        pasta = caminho_absoluto(f"salas/{sala_id}")
        shutil.rmtree(pasta, ignore_errors=True)
    except ValueError:
        pass
