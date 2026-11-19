"""Redução das fotos antes de guardar no banco (ADR-0010, contrato §4.4).

`reduzir(conteudo)` é pura (bytes → bytes, sem banco nem disco): recebe uma imagem JPEG/PNG/WebP já conferida
pela assinatura e devolve um JPEG com lado maior ≤ 1600 px, em pé (orientação do EXIF aplicada), RGB sobre fundo
branco, sem metadados (fica só o perfil de cor ICC RGB, se houver).

Erros (ErroApi, mesmo envelope da rota):
- mais de 40 megapixels → `413 ARQUIVO_GRANDE`, conferido pelo cabeçalho, **antes** de decodificar;
- assinatura válida, mas o Pillow não consegue ler → `415 TIPO_ARQUIVO_INVALIDO`.
"""

import io
import struct
import warnings

from PIL import Image, ImageOps

from app.core.erros import ErroApi

LADO_MAXIMO = 1600
LIMITE_PIXELS = 40_000_000
QUALIDADE = 80
QUALIDADE_REDUZIDA = 70
TETO_BYTES = 600 * 1024
TIPO_MIME = "image/jpeg"
FORMATOS_ACEITOS = ("JPEG", "PNG", "WEBP")

# Proteção do próprio Pillow contra "bomba de descompressão", coerente com o nosso limite: acima de
# LIMITE_PIXELS ele avisa (DecompressionBombWarning, que aqui vira exceção) e acima do dobro recusa
# (DecompressionBombError). A conferência explícita em `_abrir` continua sendo a regra.
Image.MAX_IMAGE_PIXELS = LIMITE_PIXELS
warnings.filterwarnings("error", category=Image.DecompressionBombWarning)

# Falhas de decodificação do Pillow com arquivo corrompido ou truncado.
_ERROS_DECODIFICACAO = (OSError, SyntaxError, ValueError, EOFError, IndexError, struct.error)


def erro_megapixels() -> ErroApi:
    return ErroApi(413, "ARQUIVO_GRANDE", f"A foto passa do limite de {LIMITE_PIXELS // 1_000_000} megapixels.")


def erro_ilegivel() -> ErroApi:
    return ErroApi(415, "TIPO_ARQUIVO_INVALIDO", "Não foi possível ler a imagem. Envie uma foto JPEG, PNG ou WebP.")


def _abrir(conteudo: bytes) -> Image.Image:
    """Abre (só o cabeçalho), confere a resolução e então decodifica."""
    try:
        img = Image.open(io.BytesIO(conteudo), formats=FORMATOS_ACEITOS)
        largura, altura = img.size
        if largura <= 0 or altura <= 0:
            raise erro_ilegivel()
        if largura * altura > LIMITE_PIXELS:
            raise erro_megapixels()
        if img.format == "JPEG":
            # Decodifica já reduzido (1/2, 1/4, 1/8) quando possível: menos memória e CPU no Render.
            img.draft("RGB", _tamanho_final(largura, altura))
        img.load()
        return img
    except ErroApi:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise erro_megapixels() from None
    except _ERROS_DECODIFICACAO:
        raise erro_ilegivel() from None


def _tamanho_final(largura: int, altura: int) -> tuple[int, int]:
    maior = max(largura, altura)
    if maior <= LADO_MAXIMO:
        return largura, altura
    fator = LADO_MAXIMO / maior
    return max(1, round(largura * fator)), max(1, round(altura * fator))


def _perfil_rgb(img: Image.Image) -> bytes | None:
    """Perfil ICC só se for de RGB (um perfil CMYK ou cinza num JPEG RGB deixaria as cores erradas)."""
    perfil = img.info.get("icc_profile")
    if isinstance(perfil, bytes) and len(perfil) >= 20 and perfil[16:20] == b"RGB ":
        return perfil
    return None


def _para_rgb(img: Image.Image) -> Image.Image:
    tem_alfa = img.mode in ("RGBA", "LA", "PA", "RGBa", "La") or (
        img.mode in ("P", "L", "RGB") and "transparency" in img.info
    )
    if tem_alfa:
        rgba = img.convert("RGBA")
        fundo = Image.new("RGB", rgba.size, (255, 255, 255))
        fundo.paste(rgba, mask=rgba.getchannel("A"))
        return fundo
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _gravar(img: Image.Image, qualidade: int, perfil: bytes | None) -> bytes:
    saida = io.BytesIO()
    opcoes: dict = {"quality": qualidade, "progressive": True, "optimize": True, "exif": b""}
    if perfil:
        opcoes["icc_profile"] = perfil
    img.save(saida, format="JPEG", **opcoes)
    return saida.getvalue()


def reduzir(conteudo: bytes) -> bytes:
    """JPEG reduzido conforme o ADR-0010. Ver docstring do módulo."""
    img = _abrir(conteudo)
    try:
        perfil = _perfil_rgb(img)
        img = ImageOps.exif_transpose(img) or img
        img = _para_rgb(img)
        img.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)  # nunca amplia
        # Nada do original segue para o arquivo: EXIF (GPS), XMP, comentários etc.
        img.info = {}
        dados = _gravar(img, QUALIDADE, perfil)
        if len(dados) > TETO_BYTES:
            dados = _gravar(img, QUALIDADE_REDUZIDA, perfil)
        return dados
    except _ERROS_DECODIFICACAO:
        raise erro_ilegivel() from None
