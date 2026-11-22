"""Tickets 60 e 61 (ADR-0010): fotos reduzidas no upload, guardadas no banco, entregues por /uploads e importação
das fotos antigas do disco."""

import io
import logging
import os
import re
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest
from alembic.config import Config as AlembicConfig
from PIL import Image, ImageCms
from sqlalchemy import event, inspect, select, text
from sqlalchemy.exc import InvalidRequestError

from alembic import command
from app.core.config import obter_config
from app.core.db import engine
from app.core.erros import ErroApi
from app.importar_fotos import importar
from app.models import FotoSala
from app.services import imagens
from tests.apoio_imagens import jpeg, marcadores_jpeg, png, webp
from tests.conftest import PASTA_BACKEND

UUID_JPG = re.compile(r"^salas/\d+/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.jpg$")
APP1, COM = 0xE1, 0xFE


def enviar(client, headers, sala_id, conteudo, nome="foto.jpg", tipo="image/jpeg"):
    return client.post(f"/salas/{sala_id}/fotos", headers=headers, files={"arquivo": (nome, conteudo, tipo)})


def abrir(dados: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(dados))
    img.load()
    return img


def jpeg_de_celular() -> bytes:
    """4000×3000 "deitada" (EXIF Orientation = 6: girar 90° para ficar em pé), com GPS, XMP e comentário."""
    img = Image.new("RGB", (4000, 3000), (30, 120, 200))
    # faixa vermelha no topo da imagem armazenada: depois de girar (6 = 90° horário) fica à direita
    img.paste((220, 20, 20), (0, 0, 4000, 300))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation
    exif[0x010F] = "Fabricante"
    exif[0x8825] = {1: "S", 2: (23.0, 33.0, 0.0), 3: "W", 4: (46.0, 38.0, 0.0)}  # GPS
    xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/">segredo-xmp</x:xmpmeta>'
    saida = io.BytesIO()
    img.save(saida, "JPEG", quality=90, exif=exif.tobytes(), xmp=xmp, comment=b"comentario-secreto")
    return saida.getvalue()


# ---------------------------------------------------------------- migration 0003
def _alembic() -> AlembicConfig:
    cfg = AlembicConfig(os.path.join(PASTA_BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(PASTA_BACKEND, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"].replace("%", "%%"))
    return cfg


def _colunas_fotos(conn) -> set[str]:
    return set(
        conn.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'fotos_sala'"))
    )


def test_migration_0003_sobe_e_desce_com_fotos_antigas(db, sala_id):
    cfg = _alembic()
    db.close()
    engine.dispose()
    try:
        command.downgrade(cfg, "0002")
        with engine.begin() as conn:
            assert not {"conteudo", "tipo_mime", "tamanho"} & _colunas_fotos(conn)
            conn.execute(
                text("INSERT INTO fotos_sala (sala_id, arquivo, ordem) VALUES (:s, :a, 1)"),
                {"s": sala_id, "a": f"salas/{sala_id}/antiga.png"},
            )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert {"conteudo", "tipo_mime", "tamanho"} <= _colunas_fotos(conn)
            linha = conn.execute(text("SELECT arquivo, conteudo, tipo_mime, tamanho FROM fotos_sala")).one()
            assert linha == (f"salas/{sala_id}/antiga.png", None, None, None)
            armazenamento = conn.scalar(
                text(
                    "SELECT attstorage FROM pg_attribute WHERE attrelid = 'fotos_sala'::regclass AND attname = 'conteudo'"
                )
            )
            assert armazenamento == "e"  # SET STORAGE EXTERNAL
        command.downgrade(cfg, "-1")
        with engine.connect() as conn:
            assert not {"conteudo", "tipo_mime", "tamanho"} & _colunas_fotos(conn)
            assert conn.scalar(text("SELECT count(*) FROM fotos_sala")) == 1  # linha preservada
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()


# ---------------------------------------------------------------- redução (critérios do ticket 60)
def test_upload_jpeg_de_celular_fica_em_pe_1600_sem_exif_nem_gps(client, admin, sala_id):
    original = jpeg_de_celular()
    assert len(original) < obter_config().upload_max_bytes
    r = enviar(client, admin, sala_id, original)
    assert r.status_code == 201, r.text
    servido = client.get(r.json()["url"])
    assert servido.status_code == 200
    img = abrir(servido.content)
    assert img.format == "JPEG" and img.mode == "RGB"
    assert img.size == (1200, 1600)  # 3000×4000 em pé → lado maior 1600
    # a faixa vermelha (topo da imagem armazenada) foi para a direita: a orientação foi aplicada
    vermelho = img.getpixel((1190, 800))
    assert vermelho[0] > 180 and vermelho[2] < 80, vermelho
    assert img.getpixel((10, 800))[2] > 150
    # nenhum metadado: sem EXIF (nem GPS), sem XMP, sem comentário
    assert dict(img.getexif()) == {}
    assert APP1 not in marcadores_jpeg(servido.content) and COM not in marcadores_jpeg(servido.content)
    for segredo in (b"GPS", b"Fabricante", b"segredo-xmp", b"comentario-secreto", b"Exif"):
        assert segredo not in servido.content
    assert img.info.get("progressive") or img.info.get("progression")


def test_png_com_transparencia_vira_jpeg_com_fundo_branco(client, admin, sala_id):
    img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))  # totalmente transparente
    img.paste((0, 0, 255, 255), (100, 0, 200, 100))  # metade direita azul opaca
    saida = io.BytesIO()
    img.save(saida, "PNG")
    r = enviar(client, admin, sala_id, saida.getvalue(), "t.png", "image/png")
    assert r.status_code == 201, r.text
    final = abrir(client.get(r.json()["url"]).content)
    assert final.format == "JPEG" and final.mode == "RGB" and final.size == (200, 100)
    assert all(c >= 245 for c in final.getpixel((20, 50)))  # fundo branco, não preto
    azul = final.getpixel((180, 50))
    assert azul[2] > 200 and azul[0] < 40


def test_paleta_com_transparencia_e_webp(client, admin, sala_id):
    p = Image.new("P", (40, 40), 0)
    p.putpalette([0, 0, 0, 255, 0, 0] + [0] * (256 * 3 - 6))
    p.paste(1, (20, 0, 40, 40))
    saida = io.BytesIO()
    p.save(saida, "PNG", transparency=0)
    final = abrir(client.get(enviar(client, admin, sala_id, saida.getvalue(), "p.png").json()["url"]).content)
    assert all(c >= 245 for c in final.getpixel((5, 20)))
    r = enviar(client, admin, sala_id, webp(64, 48))
    assert r.status_code == 201 and abrir(client.get(r.json()["url"]).content).size == (64, 48)


def test_imagem_menor_nao_e_ampliada(client, admin, sala_id):
    r = enviar(client, admin, sala_id, png(800, 600), "a.png", "image/png")
    assert r.status_code == 201, r.text
    assert abrir(client.get(r.json()["url"]).content).size == (800, 600)


def test_lado_maior_exatamente_1600_e_paisagem_grande():
    assert abrir(imagens.reduzir(jpeg(1600, 900))).size == (1600, 900)
    assert abrir(imagens.reduzir(png(3200, 1000))).size == (1600, 500)
    assert abrir(imagens.reduzir(jpeg(1000, 5000))).size == (320, 1600)


def test_41_megapixels_413_sem_decodificar(client, admin, sala_id, db):
    grande = png(8000, 5200, cor=(10, 10, 10))  # 41,6 MP de cor sólida: poucos KB
    assert len(grande) < 1024 * 1024
    r = enviar(client, admin, sala_id, grande, "g.png", "image/png")
    assert (r.status_code, r.json()["codigo"]) == (413, "ARQUIVO_GRANDE")
    assert r.json()["detail"] == "A foto passa do limite de 40 megapixels."
    db.rollback()
    assert db.scalar(select(FotoSala.id)) is None
    # sem estourar memória: decodificar 8000×5200 RGB pediria ~125 MB; o pico fica em poucos MB
    tracemalloc.start()
    try:
        with pytest.raises(ErroApi) as erro:
            imagens.reduzir(grande)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert erro.value.status == 413 and pico < 10 * 1024 * 1024, pico


def test_bomba_de_descompressao_acima_do_dobro_tambem_413():
    # 100 MP em 1 bit: o Pillow recusa no open (DecompressionBombError) e vira o mesmo 413
    with pytest.raises(ErroApi) as erro:
        imagens.reduzir(png(10000, 10000, cor=0, modo="1"))
    assert (erro.value.status, erro.value.codigo) == (413, "ARQUIVO_GRANDE")


def test_exatamente_40_megapixels_passa():
    assert abrir(imagens.reduzir(png(8000, 5000, cor=(1, 2, 3)))).size == (1600, 1000)


def test_assinatura_jpeg_com_resto_invalido_415(client, admin, sala_id):
    for conteudo in (b"\xff\xd8\xff\xe0" + os.urandom(2048), jpeg()[:200]):
        r = enviar(client, admin, sala_id, conteudo)
        assert (r.status_code, r.json()["codigo"]) == (415, "TIPO_ARQUIVO_INVALIDO"), r.text
    # acima de 5 MB continua 413 pelo tamanho (antes de decodificar)
    r = enviar(client, admin, sala_id, b"\xff\xd8\xff" + b"0" * (obter_config().upload_max_bytes + 1))
    assert (r.status_code, r.json()["codigo"]) == (413, "ARQUIVO_GRANDE")


def test_perfil_icc_rgb_mantido():
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    saida = io.BytesIO()
    Image.new("RGB", (50, 50), (100, 150, 200)).save(saida, "JPEG", icc_profile=srgb)
    assert abrir(imagens.reduzir(saida.getvalue())).info.get("icc_profile") == srgb
    # perfil que não é RGB (cinza) não vai para o JPEG RGB
    cinza = Image.new("L", (50, 50), 128)
    saida = io.BytesIO()
    cinza.save(saida, "PNG", icc_profile=b"\x00" * 16 + b"GRAY" + b"\x00" * 108)
    final = abrir(imagens.reduzir(saida.getvalue()))
    assert final.mode == "RGB" and "icc_profile" not in final.info


def test_acima_de_600kb_regrava_com_qualidade_70(monkeypatch):
    qualidades: list[int] = []
    original = imagens._gravar

    def espiao(img, qualidade, perfil):
        qualidades.append(qualidade)
        return original(img, qualidade, perfil)

    monkeypatch.setattr(imagens, "_gravar", espiao)
    ruido = Image.frombytes("RGB", (1600, 1200), os.urandom(1600 * 1200 * 3))
    saida = io.BytesIO()
    ruido.save(saida, "PNG")
    imagens.reduzir(saida.getvalue())
    assert qualidades == [80, 70]
    qualidades.clear()
    imagens.reduzir(jpeg(800, 600))
    assert qualidades == [80]


# ---------------------------------------------------------------- entrega: GET /uploads/{arquivo}
def test_get_uploads_cabecalhos_etag_e_304(client, admin, sala_id, db):
    foto = enviar(client, admin, sala_id, jpeg(300, 200)).json()
    url = foto["url"]
    arquivo = url.removeprefix("/uploads/")
    assert UUID_JPG.match(arquivo)
    uuid = arquivo.rsplit("/", 1)[1].removesuffix(".jpg")

    r = client.get(url, headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    h = r.headers
    assert h["content-type"] == "image/jpeg"
    assert int(h["content-length"]) == len(r.content)
    assert h["etag"] == f'"{uuid}"'
    assert h["cache-control"] == "public, max-age=31536000, immutable"
    assert h["content-security-policy"] == "default-src 'none'; sandbox"
    assert h["x-content-type-options"] == "nosniff"
    assert h["content-disposition"] == "inline"
    assert h["access-control-allow-origin"] == "http://localhost:5173"
    assert "cross-origin-resource-policy" not in h
    db.rollback()
    linha = db.execute(select(FotoSala.tamanho, FotoSala.tipo_mime).where(FotoSala.id == foto["id"])).one()
    assert linha == (len(r.content), "image/jpeg")

    for inm in (f'"{uuid}"', f'W/"{uuid}"', f'"outro", "{uuid}"', "*"):
        r304 = client.get(url, headers={"If-None-Match": inm})
        assert r304.status_code == 304, inm
        assert r304.content == b""
        assert r304.headers["etag"] == f'"{uuid}"'
        assert r304.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert r304.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in r304.headers["content-security-policy"]
    assert client.get(url, headers={"If-None-Match": '"outro"'}).status_code == 200


def test_get_uploads_404_com_envelope(client, admin, sala_id, db):
    for caminho in (
        "/uploads/salas/999/00000000-0000-4000-8000-000000000000.jpg",
        f"/uploads/salas/{sala_id}/nao-existe.jpg",
    ):
        r = client.get(caminho)
        assert (r.status_code, r.json()["codigo"]) == (404, "NAO_ENCONTRADO")
        assert r.headers["content-type"].startswith("application/json")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "content-disposition" not in r.headers and "immutable" not in r.headers.get("cache-control", "")
    # foto antiga sem conteúdo (arquivo perdido na importação): 404, inclusive com If-None-Match
    db.add(FotoSala(sala_id=sala_id, arquivo=f"salas/{sala_id}/perdida.png", ordem=1))
    db.commit()
    for headers in ({}, {"If-None-Match": '"perdida"'}):
        r = client.get(f"/uploads/salas/{sala_id}/perdida.png", headers=headers)
        assert (r.status_code, r.json()["codigo"]) == (404, "NAO_ENCONTRADO")
    # foto excluída: 404
    foto = enviar(client, admin, sala_id, jpeg()).json()
    assert client.delete(f"/salas/{sala_id}/fotos/{foto['id']}", headers=admin).status_code == 204
    assert client.get(foto["url"]).status_code == 404


def test_foto_de_sala_inativa_continua_servida(client, admin, sala_id):
    foto = enviar(client, admin, sala_id, jpeg()).json()
    sala = client.get(f"/salas/{sala_id}", headers=admin).json()
    corpo = {k: sala[k] for k in ("nome", "tipo", "capacidade", "localizacao", "descricao")} | {"ativo": False}
    assert client.put(f"/salas/{sala_id}", headers=admin, json=corpo).status_code == 200
    assert client.get(foto["url"]).status_code == 200


# ---------------------------------------------------------------- conteudo só sob demanda
class _CapturaSql:
    def __init__(self) -> None:
        self.comandos: list[str] = []

    def __call__(self, _conn, _cursor, comando, *_args) -> None:  # noqa: ANN001
        self.comandos.append(comando)

    def __enter__(self):
        event.listen(engine, "before_cursor_execute", self)
        return self

    def __exit__(self, *_exc) -> None:
        event.remove(engine, "before_cursor_execute", self)


def test_listas_e_detalhe_nao_leem_conteudo(client, admin, sala_id):
    for _ in range(2):
        enviar(client, admin, sala_id, jpeg())
    with _CapturaSql() as sql:
        assert client.get("/salas").status_code == 200
        assert client.get(f"/salas/{sala_id}").json()["fotos"]
        assert len(client.get(f"/salas/{sala_id}/fotos").json()) == 2
        assert client.get("/salas", headers=admin).status_code == 200
    fotos_sql = [c for c in sql.comandos if "fotos_sala" in c]
    assert fotos_sql, "esperava consultas a fotos_sala"
    assert not any("conteudo" in c for c in sql.comandos), fotos_sql
    # a entrega lê a coluna
    with _CapturaSql() as sql:
        url = client.get(f"/salas/{sala_id}/fotos").json()[0]["url"]
        assert client.get(url).status_code == 200
    assert any("fotos_sala.conteudo" in c for c in sql.comandos)


def test_atributo_conteudo_nao_e_carregado(client, admin, sala_id, db):
    enviar(client, admin, sala_id, jpeg())
    db.rollback()
    foto = db.scalars(select(FotoSala)).one()
    assert "conteudo" in inspect(foto).unloaded
    with pytest.raises(InvalidRequestError):
        foto.conteudo  # noqa: B018  (raiseload: nunca uma consulta escondida)
    assert foto.tamanho and foto.tipo_mime == "image/jpeg"


# ---------------------------------------------------------------- nada em disco
def test_upload_nao_grava_em_disco(client, admin, sala_id, monkeypatch, tmp_path):
    inexistente = tmp_path / "nao" / "existe"
    monkeypatch.setattr(obter_config(), "UPLOAD_DIR", str(inexistente))
    antes = {p for p in tmp_path.rglob("*")}
    r = enviar(client, admin, sala_id, png(120, 80), "a.png", "image/png")
    assert r.status_code == 201, r.text
    assert client.get(r.json()["url"]).status_code == 200
    assert client.delete(f"/salas/{sala_id}/fotos/{r.json()['id']}", headers=admin).status_code == 204
    assert not inexistente.exists()
    assert {p for p in tmp_path.rglob("*")} == antes


def test_upload_com_upload_dir_somente_leitura(client, admin, sala_id, monkeypatch, tmp_path):
    """Pasta só leitura (como o volume `:ro` do Compose): o upload não tenta gravar nada nela."""
    pasta = tmp_path / "ro"
    pasta.mkdir()
    monkeypatch.setattr(obter_config(), "UPLOAD_DIR", str(pasta))
    escritas: list[str] = []
    original = Path.open

    def vigia(self, mode="r", *args, **kwargs):  # noqa: ANN001
        if any(c in mode for c in "wax+"):
            escritas.append(str(self))
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", vigia)
    pasta.chmod(0o555)
    try:
        r = enviar(client, admin, sala_id, jpeg())
        assert r.status_code == 201, r.text
    finally:
        pasta.chmod(0o755)
    assert list(pasta.iterdir()) == [] and escritas == []


# ---------------------------------------------------------------- importação das fotos antigas (ticket 61)
def _foto_antiga(db, sala_id: int, arquivo: str, ordem: int = 1) -> int:
    foto = FotoSala(sala_id=sala_id, arquivo=arquivo, ordem=ordem)
    db.add(foto)
    db.commit()
    return foto.id


def _gravar(base: Path, relativo: str, dados: bytes) -> Path:
    caminho = base / relativo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(dados)
    return caminho


def test_importar_fotos_antigas(client, db, sala_id, tmp_path, caplog):
    pasta = tmp_path / "uploads"
    fora = _gravar(tmp_path, "fora.jpg", jpeg())  # existe, mas fora de UPLOAD_DIR
    arquivos_disco = [
        _gravar(pasta, f"salas/{sala_id}/a.png", png(2000, 1000)),
        _gravar(pasta, f"salas/{sala_id}/b.webp", webp(64, 48)),
        _gravar(pasta, f"salas/{sala_id}/ruim.jpg", b"\xff\xd8\xff\xe0lixo" * 10),
        fora,
    ]
    ids = {
        "png": _foto_antiga(db, sala_id, f"salas/{sala_id}/a.png", 1),
        "webp": _foto_antiga(db, sala_id, f"salas/{sala_id}/b.webp", 2),
        "ausente": _foto_antiga(db, sala_id, f"salas/{sala_id}/sumiu.jpg", 3),
        "ruim": _foto_antiga(db, sala_id, f"salas/{sala_id}/ruim.jpg", 4),
        "fora": _foto_antiga(db, sala_id, "../fora.jpg", 5),
        "absoluto": _foto_antiga(db, sala_id, str(fora), 6),
    }
    conteudos_antes = {p: p.read_bytes() for p in arquivos_disco}

    caplog.set_level(logging.INFO, logger="sala_web")
    resumo = importar(db, pasta=pasta)
    assert (resumo.importadas, resumo.nao_encontradas, resumo.com_erro) == (2, 1, 3)

    db.expire_all()
    fotos = {f.id: f for f in db.scalars(select(FotoSala))}
    assert len(fotos) == 6  # nenhuma linha apagada
    for chave in ("png", "webp"):
        f = fotos[ids[chave]]
        assert UUID_JPG.match(f.arquivo) and f.arquivo.startswith(f"salas/{sala_id}/")
        assert f.tipo_mime == "image/jpeg" and f.tamanho and f.tamanho > 0
        r = client.get(f.url)
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert len(r.content) == f.tamanho
    assert abrir(client.get(fotos[ids["png"]].url).content).size == (1600, 800)
    assert client.get(f"/uploads/salas/{sala_id}/a.png").status_code == 404  # nome antigo deixa de existir
    for chave in ("ausente", "ruim", "fora", "absoluto"):
        f = fotos[ids[chave]]
        assert f.tamanho is None and f.tipo_mime is None
        assert client.get(f.url).status_code == 404
    assert fotos[ids["fora"]].arquivo == "../fora.jpg"
    # nada apagado nem alterado no disco
    assert {p: p.read_bytes() for p in arquivos_disco} == conteudos_antes

    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    texto = "\n".join(r.getMessage() for r in avisos)
    for chave, nome in (("ausente", "sumiu.jpg"), ("ruim", "ruim.jpg"), ("fora", "../fora.jpg")):
        assert re.search(rf"Foto {ids[chave]} \(.*{re.escape(nome)}\)", texto), texto
    assert "2 importada(s), 1 não encontrada(s), 3 com erro" in caplog.text

    # segunda vez: nada é reimportado, mesmas URLs
    urls = {i: f.url for i, f in fotos.items()}
    caplog.clear()
    resumo = importar(db, pasta=pasta)
    assert resumo.importadas == 0 and (resumo.nao_encontradas, resumo.com_erro) == (1, 3)
    db.expire_all()
    assert {f.id: f.url for f in db.scalars(select(FotoSala))} == urls


def test_importar_sem_pendentes_ou_sem_pasta_e_silencioso(db, sala_id, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="sala_web")
    assert importar(db, pasta=tmp_path / "nao-existe").total == 0
    _foto_antiga(db, sala_id, f"salas/{sala_id}/x.jpg")
    assert importar(db, pasta=tmp_path / "nao-existe").importadas == 0
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert [r for r in caplog.records if r.levelno == logging.INFO]


def test_importar_main_sempre_termina_com_zero(monkeypatch, caplog):
    import app.importar_fotos as modulo

    def quebra(_db):
        raise RuntimeError("banco caiu")

    monkeypatch.setattr(modulo, "importar", quebra)
    assert modulo.main() == 0
    assert "interrompida" in caplog.text


def test_comando_python_m_app_importar_fotos(tmp_path):
    """O comando do CMD do Dockerfile roda e sai com 0 (clone novo: nada a importar)."""
    env = {**os.environ, "UPLOAD_DIR": str(tmp_path / "vazio")}
    r = subprocess.run(
        [sys.executable, "-m", "app.importar_fotos"], cwd=PASTA_BACKEND, env=env, capture_output=True, text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "WARNING" not in r.stderr and "nenhuma foto pendente" in r.stderr
