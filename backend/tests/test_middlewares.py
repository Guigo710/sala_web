"""Tickets 30 (CORS em toda resposta de erro), 40 (limite de corpo) e 44 (cabeçalhos de segurança)."""

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from app.core import middlewares
from app.core.config import obter_config
from app.main import LIMITE_CORPO_PADRAO, app

ORIGEM_OK = "http://localhost:5173"
ORIGEM_RUIM = "http://evil.example"
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
FOLGA_MULTIPART = 512 * 1024


def _foto(tamanho: int) -> dict:
    return {"arquivo": ("g.jpg", JPG + b"0" * (tamanho - len(JPG)), "image/jpeg")}


def _respostas_de_erro(client: TestClient, admin, professor, sala_id, origem: str) -> dict[str, object]:
    """Uma resposta de cada status de erro do ticket 30, todas com o cabeçalho Origin informado."""
    o = {"Origin": origem}
    limite = obter_config().upload_max_bytes
    return {
        "413-antecipado": client.post(
            f"/salas/{sala_id}/fotos", headers={**admin, **o}, files=_foto(limite + 1024 * 1024)
        ),
        "413-em-blocos": client.post(f"/salas/{sala_id}/fotos", headers={**admin, **o}, files=_foto(limite + 1)),
        "415": client.post(
            f"/salas/{sala_id}/fotos", headers={**admin, **o}, files={"arquivo": ("a.jpg", b"ola", "image/jpeg")}
        ),
        "401": client.get("/auth/me", headers=o),
        "403": client.get("/professores", headers={**professor, **o}),
        "404": client.get("/salas/999999", headers=o),
        "405": client.patch("/salas", headers=o),
        "409": client.post("/salas", headers={**admin, **o}, json={"nome": "Sala 01", "tipo": "sala", "capacidade": 1}),
        "422": client.post("/salas", headers={**admin, **o}, json={"nome": "X", "tipo": "sala", "capacidade": 0}),
    }


ESPERADO = {
    "413-antecipado": (413, "ARQUIVO_GRANDE"),
    "413-em-blocos": (413, "ARQUIVO_GRANDE"),
    "415": (415, "TIPO_ARQUIVO_INVALIDO"),
    "401": (401, "NAO_AUTENTICADO"),
    "403": (403, "SEM_PERMISSAO"),
    "404": (404, "NAO_ENCONTRADO"),
    "405": (405, "METODO_NAO_PERMITIDO"),
    "409": (409, "NOME_DUPLICADO"),
    "422": (422, "VALIDACAO"),
}


# ---------------------------------------------------------------- ticket 30
def test_cors_em_todas_as_respostas_de_erro(client, admin, professor, sala_id):
    for nome, r in _respostas_de_erro(client, admin, professor, sala_id, ORIGEM_OK).items():
        assert (r.status_code, r.json()["codigo"]) == ESPERADO[nome], (nome, r.text)
        assert r.headers.get("access-control-allow-origin") == ORIGEM_OK, nome


def test_sem_cors_para_origem_nao_permitida(client, admin, professor, sala_id):
    for nome, r in _respostas_de_erro(client, admin, professor, sala_id, ORIGEM_RUIM).items():
        assert r.status_code == ESPERADO[nome][0], nome
        assert "access-control-allow-origin" not in r.headers, nome


@pytest.fixture
def servico_quebrado(monkeypatch):
    from app.services import salas as servico

    def explode(*_a, **_k):
        raise RuntimeError("segredo interno: postgresql://user:senha@host/db")

    monkeypatch.setattr(servico, "listar", explode)
    # O fileConfig do Alembic (fixture de esquema) desliga loggers já existentes.
    monkeypatch.setattr(middlewares.log, "disabled", False)


@pytest.mark.parametrize("origem", [ORIGEM_OK, ORIGEM_RUIM])
def test_500_com_cors_envelope_e_stack_trace_so_no_log(servico_quebrado, caplog, origem):
    caplog.set_level(logging.ERROR, logger="sala_web")
    with TestClient(app) as c:  # raise_server_exceptions=True: nada escapa do middleware ErroInterno
        r = c.get("/salas", headers={"Origin": origem})
    assert r.status_code == 500
    assert r.json() == {"detail": "Erro interno no servidor. Tente novamente.", "codigo": "ERRO_INTERNO"}
    assert "Traceback" not in r.text and "segredo" not in r.text
    if origem == ORIGEM_OK:
        assert r.headers["access-control-allow-origin"] == ORIGEM_OK
    else:
        assert "access-control-allow-origin" not in r.headers
    registro = next(rec for rec in caplog.records if rec.name == "sala_web" and rec.exc_info)
    assert isinstance(registro.exc_info[1], RuntimeError)
    assert "Traceback" in caplog.text


# ---------------------------------------------------------------- ticket 40
async def _chamar_asgi(caminho: str, cabecalhos: list[tuple[bytes, bytes]], partes, maximo_partes: int):
    """Chama a aplicação real direto pelo ASGI, entregando o corpo em pedaços (como um upload chunked).

    Devolve (status, corpo, quantos pedaços a aplicação chegou a ler).
    """
    lidos = 0
    enviados: list[dict] = []

    async def receive():
        nonlocal lidos
        if lidos >= maximo_partes:
            return {"type": "http.request", "body": b"", "more_body": False}
        lidos += 1
        return {"type": "http.request", "body": next(partes), "more_body": lidos < maximo_partes}

    async def send(mensagem):
        enviados.append(mensagem)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": caminho,
        "raw_path": caminho.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), (b"origin", ORIGEM_OK.encode()), *cabecalhos],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    inicio = next(m for m in enviados if m["type"] == "http.response.start")
    corpo = b"".join(m.get("body", b"") for m in enviados if m["type"] == "http.response.body")
    return inicio, corpo, lidos


BLOCO = 64 * 1024
CINQUENTA_MB = 50 * 1024 * 1024


def test_upload_chunked_acima_do_limite_para_de_ler_cedo(client, sala_id):
    """Sem Content-Length nem token: 413 ARQUIVO_GRANDE sem ler os 50 MB (antes, o corpo todo era lido)."""
    fronteira = b"xyz"
    preambulo = (
        b"--" + fronteira + b"\r\n"
        b'Content-Disposition: form-data; name="arquivo"; filename="a.jpg"\r\n'
        b"Content-Type: image/jpeg\r\n\r\n" + JPG
    )

    def gerador():
        yield preambulo
        while True:
            yield b"0" * BLOCO

    maximo = CINQUENTA_MB // BLOCO
    inicio, corpo, lidos = asyncio.run(
        _chamar_asgi(
            f"/salas/{sala_id}/fotos",
            [(b"content-type", b"multipart/form-data; boundary=" + fronteira), (b"transfer-encoding", b"chunked")],
            gerador(),
            maximo,
        )
    )
    assert inicio["status"] == 413
    assert b'"codigo": "ARQUIVO_GRANDE"' in corpo or b'"codigo":"ARQUIVO_GRANDE"' in corpo
    cabecalhos = dict(inicio["headers"])
    assert cabecalhos[b"access-control-allow-origin"] == ORIGEM_OK.encode()
    limite_middleware = obter_config().upload_max_bytes + FOLGA_MULTIPART
    assert lidos * BLOCO <= limite_middleware + 2 * BLOCO  # parou logo depois do limite
    assert lidos < maximo / 5


def test_login_com_corpo_grande_413_antes_do_parse(client):
    # Content-Length de 5 MB: recusado antes de ler o corpo
    r = client.post(
        "/auth/login",
        content=b'{"rm": "admin", "senha": "' + b"x" * (5 * 1024 * 1024) + b'"}',
        headers={"Content-Type": "application/json", "Origin": ORIGEM_OK},
    )
    assert (r.status_code, r.json()["codigo"]) == (413, "CORPO_GRANDE")
    assert r.headers["access-control-allow-origin"] == ORIGEM_OK

    # Sem Content-Length (chunked): cortado contando os bytes
    def gerador():
        yield b'{"rm": "admin", "senha": "'
        while True:
            yield b"x" * BLOCO

    inicio, corpo, lidos = asyncio.run(
        _chamar_asgi("/auth/login", [(b"content-type", b"application/json")], gerador(), 5 * 1024 * 1024 // BLOCO)
    )
    assert inicio["status"] == 413 and b"CORPO_GRANDE" in corpo
    assert lidos * BLOCO <= LIMITE_CORPO_PADRAO + 2 * BLOCO


def test_corpo_chunked_pelo_testclient(client, admin, sala_id):
    """Corpo sem Content-Length (gerador → Transfer-Encoding: chunked) também é contado."""
    r = client.post(
        "/auth/login",
        content=(p for p in [b'{"rm": "admin", "senha": "', b"x" * (LIMITE_CORPO_PADRAO + 1), b'"}']),
        headers={"Content-Type": "application/json"},
    )
    assert "content-length" not in r.request.headers
    assert (r.status_code, r.json()["codigo"]) == (413, "CORPO_GRANDE")
    # corpo pequeno chunked continua funcionando
    r = client.post(
        "/auth/login",
        content=(p for p in [b'{"rm": "admin", ', b'"senha": "senhaAdmin123"}']),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text


def test_corpo_no_limite_passa(client, admin):
    # 1 MB exato de JSON em rota comum não é barrado pelo middleware (a validação do schema decide)
    corpo = b'{"nome": "' + b"a" * (LIMITE_CORPO_PADRAO - 64) + b'", "tipo": "sala", "capacidade": 1}'
    assert len(corpo) <= LIMITE_CORPO_PADRAO
    r = client.post("/salas", headers={**admin, "Content-Type": "application/json"}, content=corpo)
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")


# ---------------------------------------------------------------- ticket 44
def test_cabecalhos_de_seguranca_na_api(client):
    r = client.get("/salas")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    erro = client.get("/nao-existe")
    assert erro.headers["x-content-type-options"] == "nosniff"


def test_cabecalhos_de_seguranca_em_uploads(client, admin, sala_id):
    foto = client.post(f"/salas/{sala_id}/fotos", headers=admin, files={"arquivo": ("a.jpg", JPG, "image/jpeg")}).json()
    r = client.get(foto["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-disposition"] == "inline"
    assert "sandbox" in r.headers["content-security-policy"]
    assert "max-age" in r.headers["cache-control"]
    assert client.get("/uploads/salas/999/nao-existe.jpg").headers["x-content-type-options"] == "nosniff"
