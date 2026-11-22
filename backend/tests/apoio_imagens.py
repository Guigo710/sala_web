"""Imagens de verdade para os testes de upload (ADR-0010: o servidor decodifica e reduz cada foto).

Os testes antigos mandavam só a assinatura seguida de zeros; desde a rodada 5 isso é `415` (não pode ser lida
como imagem). Estas funções geram arquivos pequenos e válidos na hora, sem versionar binários.
"""

import io
import struct

from PIL import Image


def _salvar(img: Image.Image, formato: str, **opcoes) -> bytes:
    saida = io.BytesIO()
    img.save(saida, format=formato, **opcoes)
    return saida.getvalue()


def jpeg(largura: int = 32, altura: int = 24, cor=(200, 40, 40), **opcoes) -> bytes:
    return _salvar(Image.new("RGB", (largura, altura), cor), "JPEG", quality=90, **opcoes)


def png(largura: int = 32, altura: int = 24, cor=(40, 160, 40), modo: str = "RGB") -> bytes:
    return _salvar(Image.new(modo, (largura, altura), cor), "PNG")


def webp(largura: int = 32, altura: int = 24, cor=(40, 40, 200)) -> bytes:
    return _salvar(Image.new("RGB", (largura, altura), cor), "WEBP", quality=90)


def jpeg_com_tamanho(total: int) -> bytes:
    """JPEG válido com exatamente `total` bytes: um JPEG pequeno + segmentos de comentário (COM) de enchimento,
    inseridos logo depois do SOI. Continua decodificável (o conteúdo de COM é ignorado)."""
    base = jpeg()
    soi, resto = base[:2], base[2:]
    falta = total - len(base)
    assert falta >= 0, "total menor que o JPEG base"
    segmentos: list[bytes] = []
    while falta > 0:
        if falta > 65537:
            segmentos.append(_com(65533))
            falta -= 65537
        elif falta >= 4:
            segmentos.append(_com(falta - 4))
            falta = 0
        else:  # sobram 1 a 3 bytes: o último COM vira dois, que somados cobrem o que falta
            assert segmentos, "total muito próximo do JPEG base"
            bloco = len(segmentos.pop()) + falta
            metade = bloco // 2
            segmentos += [_com(metade - 4), _com(bloco - metade - 4)]
            falta = 0
    return soi + b"".join(segmentos) + resto


def _com(n: int) -> bytes:
    return b"\xff\xfe" + struct.pack(">H", n + 2) + b"x" * n


def eh_jpeg(dados: bytes) -> bool:
    return dados.startswith(b"\xff\xd8\xff")


def marcadores_jpeg(dados: bytes) -> list[int]:
    """Marcadores dos segmentos antes do início da imagem (SOS): APP1 = EXIF/XMP, COM = comentário, ..."""
    assert dados[:2] == b"\xff\xd8"
    i, achados = 2, []
    while i < len(dados) - 4:
        assert dados[i] == 0xFF, f"esperava marcador em {i}"
        marcador = dados[i + 1]
        achados.append(marcador)
        if marcador == 0xDA:  # SOS: daqui em diante é a imagem
            break
        (tamanho,) = struct.unpack(">H", dados[i + 2 : i + 4])
        i += 2 + tamanho
    return achados
