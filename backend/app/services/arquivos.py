"""Leitura do arquivo enviado (ADR-0005/0010): assinatura, leitura com limite e caminho seguro em UPLOAD_DIR.

Nada é gravado nem apagado em disco (ADR-0010): as fotos ficam no banco. `caminho_absoluto` só é usado pela
importação das fotos antigas (`python -m app.importar_fotos`), que apenas **lê** o disco.
"""

from pathlib import Path

from app.core.config import obter_config
from app.core.erros import ErroApi

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
    """Lê em blocos; passa do limite → 413 sem ler o resto."""
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


def caminho_absoluto(relativo: str, base: Path | None = None) -> Path:
    """Caminho de `relativo` dentro de `base` (padrão: UPLOAD_DIR); fora dela (`../`, caminho absoluto, link para
    fora) → ValueError."""
    base = (base or obter_config().upload_dir).resolve()
    caminho = (base / relativo).resolve()
    if base not in caminho.parents:
        raise ValueError("caminho fora de UPLOAD_DIR")
    return caminho
