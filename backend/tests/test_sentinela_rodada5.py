"""Sentinela, ticket 68 (rodada 5): segurança do que mudou com as fotos no banco e a publicação no Render.

- `/uploads/...`: tentativas de caminho, NUL, nomes enormes e `If-None-Match: *` em nome inexistente → 404 com
  envelope, sem os cabeçalhos de foto;
- upload: formatos que não são JPEG/PNG/WebP (SVG, GIF, TIFF, HTML com assinatura de JPEG) → 415; dimensões
  anunciadas no cabeçalho acima de 40 MP → 413 sem decodificar; poliglota PNG+ZIP é recodificado (o ZIP some);
- valores que o Postgres recusa (id além do `integer`, texto com NUL) → 422 VALIDACAO, não 500;
- logs: erro do banco sem os valores da consulta; configuração recusada sem o valor (ex.: JWT_SECRET curto).
"""

import io
import logging
import struct
import zlib

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.config import Config
from app.core.db import engine
from tests.apoio_imagens import jpeg, png


def enviar(client, headers, sala_id, conteudo, nome="foto.jpg", tipo="image/jpeg"):
    return client.post(f"/salas/{sala_id}/fotos", headers=headers, files={"arquivo": (nome, conteudo, tipo)})


def _png_cabecalho(largura: int, altura: int) -> bytes:
    """PNG cujo IHDR anuncia largura × altura, com um IDAT minúsculo: tem de ser recusado antes de decodificar."""

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", ihdr) + bloco(b"IDAT", zlib.compress(b"\x00" * 64)) + bloco(b"IEND", b"")


def _jpeg_com_sof(largura: int, altura: int) -> bytes:
    """JPEG válido com as dimensões do SOF trocadas (anuncia uma imagem gigante)."""
    dados = bytearray(jpeg(64, 48))
    i = next(i for i in range(2, len(dados) - 1) if dados[i] == 0xFF and dados[i + 1] in (0xC0, 0xC2))
    dados[i + 5 : i + 9] = struct.pack(">HH", altura, largura)
    return bytes(dados)


# ---------------------------------------------------------------- /uploads
@pytest.mark.parametrize(
    "caminho",
    [
        "/uploads/../app/main.py",
        "/uploads/%2e%2e/%2e%2e/etc/passwd",
        "/uploads/..%2f..%2fapp%2fmain.py",
        "/uploads/salas/1/../../../app/main.py",
        "/uploads/salas/1/%00.jpg",
        "/uploads/salas/1/foto.jpg%00.png",
        "/uploads/salas/abc/xyz.jpg",
        "/uploads/salas/1/" + "a" * 4000 + ".jpg",
        "/uploads/",
        "/uploads/%0d%0aSet-Cookie:%20x=1",
    ],
)
def test_uploads_caminhos_estranhos_dao_404_com_envelope(client, caminho):
    r = client.get(caminho)
    assert r.status_code == 404, r.text
    assert r.json()["codigo"] == "NAO_ENCONTRADO"
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["x-content-type-options"] == "nosniff"
    for cabecalho in ("content-disposition", "etag", "set-cookie"):
        assert cabecalho not in r.headers
    assert "immutable" not in r.headers.get("cache-control", "")


def test_uploads_if_none_match_curinga_so_vale_para_foto_que_existe(client, admin, sala_id):
    url = enviar(client, admin, sala_id, jpeg()).json()["url"]
    r = client.get(url, headers={"If-None-Match": "*"})
    assert r.status_code == 304 and r.content == b""
    r = client.get(f"/uploads/salas/{sala_id}/00000000-0000-4000-8000-000000000000.jpg", headers={"If-None-Match": "*"})
    assert (r.status_code, r.json()["codigo"]) == (404, "NAO_ENCONTRADO")
    assert client.post(url).status_code == 405
    assert client.delete(url).status_code == 405


def test_uploads_tem_cors_para_a_origem_do_site(client, admin, sala_id):
    url = enviar(client, admin, sala_id, jpeg()).json()["url"]
    r = client.get(url, headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "cross-origin-resource-policy" not in r.headers
    r = client.get(url, headers={"Origin": "https://outro.example"})
    assert "access-control-allow-origin" not in r.headers


# ---------------------------------------------------------------- upload: formatos e tamanhos
@pytest.mark.parametrize(
    ("conteudo", "tipo"),
    [
        (b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "image/svg+xml"),
        (b"<html><script>alert(1)</script></html>", "image/jpeg"),
        (b"\xff\xd8\xff\xe0<html><script>alert(1)</script></html>", "image/jpeg"),
        (b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", "image/gif"),
        (b"II*\x00" + b"\x00" * 64, "image/tiff"),
        (b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 20, "image/webp"),
        (b"BM" + b"\x00" * 64, "image/bmp"),
    ],
    ids=["svg", "html", "assinatura-jpeg-com-html", "gif", "tiff", "webp-falso", "bmp"],
)
def test_upload_de_formato_que_nao_e_foto_415(client, admin, sala_id, conteudo, tipo):
    r = enviar(client, admin, sala_id, conteudo, nome="x.jpg", tipo=tipo)
    assert (r.status_code, r.json()["codigo"]) == (415, "TIPO_ARQUIVO_INVALIDO"), r.text


@pytest.mark.parametrize(
    "conteudo",
    [_png_cabecalho(8000, 5200), _png_cabecalho(100_000, 100_000), _jpeg_com_sof(65000, 65000)],
    ids=["png-41mp", "png-10-gigapixels", "jpeg-sof-65000"],
)
def test_dimensoes_anunciadas_acima_de_40_mp_dao_413(client, admin, sala_id, conteudo):
    r = enviar(client, admin, sala_id, conteudo)
    assert (r.status_code, r.json()["codigo"]) == (413, "ARQUIVO_GRANDE"), r.text


def test_png_gigantesco_no_ihdr_nao_derruba_a_api(client, admin, sala_id):
    # 2^31-1 × 2^31-1: o Pillow recusa ao ler o cabeçalho; o importante é não virar 500.
    r = enviar(client, admin, sala_id, _png_cabecalho(2**31 - 1, 2**31 - 1))
    assert r.status_code in (413, 415), r.text


def test_poliglota_png_mais_zip_e_recodificado(client, admin, sala_id):
    r = enviar(client, admin, sala_id, png(40, 30) + b"PK\x03\x04" + b"\x00" * 200, nome="x.png", tipo="image/png")
    assert r.status_code == 201, r.text
    g = client.get(r.json()["url"])
    assert g.headers["content-type"] == "image/jpeg"
    assert g.content[:2] == b"\xff\xd8" and b"PK\x03\x04" not in g.content
    assert Image.open(io.BytesIO(g.content)).size == (40, 30)


# ---------------------------------------------------------------- valores que o banco recusa
@pytest.mark.parametrize(
    "caminho",
    ["/salas/99999999999", "/horarios/99999999999", "/salas?capacidade_min=99999999999", "/salas?busca=%00", "/softwares?busca=a%00b"],
)
def test_valor_recusado_pelo_banco_e_422_e_nao_500(client, caminho, caplog):
    with caplog.at_level(logging.WARNING, logger="sala_web"):
        r = client.get(caminho)
    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "VALIDACAO" and r.json()["erros"]
    assert "Erro inesperado" not in caplog.text


def test_login_com_nul_no_rm_e_422(client):
    r = client.post("/auth/login", json={"rm": "adm\u0000in", "senha": "qualquer123"})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO"), r.text


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [("get", "/reservas/99999999999"), ("post", "/reservas/99999999999/cancelar"), ("get", "/reservas/grupos/99999999999")],
)
def test_reserva_com_id_enorme_e_422(client, admin, metodo, caminho):
    r = client.request(metodo.upper(), caminho, headers=admin, json={} if metodo == "post" else None)
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO"), r.text


# ---------------------------------------------------------------- logs sem segredos
def test_erro_do_banco_no_log_nao_traz_os_valores_da_consulta():
    assert engine.hide_parameters is True


def test_configuracao_recusada_nao_mostra_o_valor(monkeypatch):
    segredo = "segredo-curto-que-vazaria"
    monkeypatch.setenv("JWT_SECRET", segredo)
    with pytest.raises(ValidationError) as erro:
        Config()  # type: ignore[call-arg]
    assert "JWT_SECRET" in str(erro.value)
    assert segredo not in str(erro.value)


# ---------------------------------------------------------------- DATABASE_URL copiada do Neon
@pytest.mark.parametrize(
    ("copiada", "esperada"),
    [
        (
            "postgresql://neondb_owner:Abc123@ep-x-1.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+psycopg://neondb_owner:Abc123@ep-x-1.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        ),
        ("postgres://u:p@h/d?sslmode=require", "postgresql+psycopg://u:p@h/d?sslmode=require"),
        (" postgresql+psycopg://u:p@h/d ", "postgresql+psycopg://u:p@h/d"),
    ],
)
def test_database_url_do_neon_funciona_sem_trocar_o_comeco(monkeypatch, copiada, esperada):
    from app.core.config import ConfigBanco

    monkeypatch.setenv("DATABASE_URL", copiada)
    assert ConfigBanco().DATABASE_URL == esperada  # type: ignore[call-arg]
