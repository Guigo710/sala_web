"""Ticket 24: matriz de permissões (§5), login/JWT, exposição de dados e itens de segurança (ticket 25)."""

from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.core.config import obter_config
from app.core.tempo import agora_tz
from app.main import app
from app.models import Professor, Sala
from tests.conftest import token_de

# ---------------------------------------------------------------- matriz §5
# (método, rota, corpo). Ids 1 existem no seed (sala 1, equipamento 1, software 1, horário 1, semestre 1).
ROTAS_ADMIN = [
    ("POST", "/salas", {"nome": "Nova", "tipo": "sala", "capacidade": 10}),
    ("PUT", "/salas/1", {"nome": "Sala 01", "tipo": "sala", "capacidade": 41}),
    ("DELETE", "/salas/1", None),
    ("PUT", "/salas/1/equipamentos", [{"equipamento_id": 1, "quantidade": 2}]),
    ("PUT", "/salas/1/softwares", {"software_ids": [1]}),
    ("POST", "/salas/1/fotos", "FOTO"),
    ("PATCH", "/salas/1/fotos/1", {"legenda": "x"}),
    ("DELETE", "/salas/1/fotos/1", None),
    ("PUT", "/salas/1/fotos/ordem", {"foto_ids": []}),
    ("POST", "/equipamentos", {"nome": "Novo", "descricao": None}),
    ("PUT", "/equipamentos/1", {"nome": "Computador", "descricao": None}),
    ("DELETE", "/equipamentos/1", None),
    ("POST", "/softwares", {"nome": "Novo", "versao": "1", "categoria": None}),
    ("PUT", "/softwares/1", {"nome": "VS Code", "versao": None, "categoria": "IDE"}),
    ("DELETE", "/softwares/1", None),
    ("POST", "/horarios", {"turno": "noite", "ordem": 9, "inicio": "23:00", "fim": "23:30", "dias_semana": [1], "ativo": True}),
    ("PUT", "/horarios/1", {"turno": "manha", "ordem": 1, "inicio": "07:30", "fim": "08:20", "dias_semana": [1, 2, 3, 4, 5, 6], "ativo": True}),
    ("DELETE", "/horarios/14", None),
    ("POST", "/semestres", {"nome": "2040-1", "data_inicio": "2040-02-01", "data_fim": "2040-06-30"}),
    ("PUT", "/semestres/1", {"nome": "2026-1", "data_inicio": "2026-02-02", "data_fim": "2026-06-30"}),
    ("DELETE", "/semestres/1", None),
    ("GET", "/professores", None),
    ("GET", "/professores/1", None),
    ("POST", "/professores", {"rm": "novo123", "nome": "Novo", "senha": "senhaNova1"}),
    ("PUT", "/professores/{prof}", {"nome": "P", "email": None, "papel": "professor", "ativo": True}),
    ("PUT", "/professores/{prof}/senha", {"nova_senha": "outraSenha1"}),
    ("DELETE", "/professores/{prof}", None),
]

ROTAS_PROFESSOR = [
    ("GET", "/auth/me", None),
    ("PUT", "/auth/me/senha", {"senha_atual": "x", "nova_senha": "y" * 8}),
    ("GET", "/reservas/minhas", None),
    ("POST", "/reservas", {"sala_id": 1, "data": "2035-01-09", "horario_ids": [1]}),
    ("POST", "/reservas/recorrentes/previa", {"sala_id": 1, "data_inicio": "2035-01-09", "horario_ids": [1]}),
    ("POST", "/reservas/recorrentes", {"sala_id": 1, "data_inicio": "2035-01-09", "horario_ids": [1], "datas": ["2035-01-09"]}),
    ("GET", "/reservas/grupos/1", None),
    ("POST", "/reservas/1/cancelar", None),
    ("POST", "/reservas/grupos/1/cancelar", None),
]

ROTAS_PUBLICAS = [
    "/saude", "/salas", "/salas/tipos", "/salas/1", "/salas/1/fotos", "/salas/1/disponibilidade?data=2035-01-09",
    "/equipamentos", "/equipamentos/1", "/softwares", "/softwares/categorias", "/softwares/1",
    "/horarios", "/horarios/1", "/semestres", "/semestres/1", "/reservas?mes=2035-01",
]

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def chamar(client, metodo, rota, corpo, headers=None, prof_id=None):
    rota = rota.replace("{prof}", str(prof_id or 1))
    if corpo == "FOTO":
        return client.request(metodo, rota, headers=headers or {}, files={"arquivo": ("a.png", PNG, "image/png")})
    return client.request(metodo, rota, headers=headers or {}, json=corpo)


@pytest.mark.parametrize(("metodo", "rota", "corpo"), ROTAS_ADMIN, ids=[f"{m} {r}" for m, r, _ in ROTAS_ADMIN])
def test_rotas_admin(client, admin, professor, novo_professor, metodo, rota, corpo):
    _, alvo = novo_professor("alvo01")
    visitante = chamar(client, metodo, rota, corpo, prof_id=alvo["id"])
    assert (visitante.status_code, visitante.json()["codigo"]) == (401, "NAO_AUTENTICADO")
    prof = chamar(client, metodo, rota, corpo, professor, alvo["id"])
    assert (prof.status_code, prof.json()["codigo"]) == (403, "SEM_PERMISSAO")
    adm = chamar(client, metodo, rota, corpo, admin, alvo["id"])
    # admin passa da autorização; 404 só nas rotas de foto (não há foto 1 no seed)
    assert adm.status_code < 400 or ("/fotos/1" in rota and adm.status_code == 404), adm.text


@pytest.mark.parametrize(("metodo", "rota", "corpo"), ROTAS_PROFESSOR, ids=[f"{m} {r}" for m, r, _ in ROTAS_PROFESSOR])
def test_rotas_de_professor_exigem_token(client, metodo, rota, corpo):
    r = chamar(client, metodo, rota, corpo, {"Authorization": "Bearer nao-e-um-jwt"})
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")
    r = chamar(client, metodo, rota, corpo)
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("rota", ROTAS_PUBLICAS)
def test_rotas_publicas_sem_token_e_com_token_invalido(client, rota):
    assert client.get(rota).status_code == 200
    assert client.get(rota, headers={"Authorization": "Bearer lixo"}).status_code == 200


# ---------------------------------------------------------------- login e JWT
def test_login_sucesso_formato(client):
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer" and corpo["expira_em"]
    assert set(corpo["usuario"]) == {"id", "rm", "nome", "email", "papel", "ativo", "criado_em"}
    claims = jwt.decode(corpo["access_token"], options={"verify_signature": False})
    assert set(claims) == {"sub", "papel", "iat", "exp"}
    assert claims["exp"] - claims["iat"] == obter_config().JWT_EXPIRA_MINUTOS * 60
    assert jwt.get_unverified_header(corpo["access_token"])["alg"] == "HS256"


@pytest.mark.parametrize(
    "credenciais",
    [
        {"rm": "admin", "senha": "errada"},
        {"rm": "naoexiste", "senha": "senhaAdmin123"},
        {"rm": "ADMIN", "senha": "senhaAdmin123"},  # RM é comparado exatamente
        {"rm": "' OR '1'='1", "senha": "' OR '1'='1"},  # SQL injection
    ],
)
def test_login_falha_mensagem_unica(client, credenciais):
    r = client.post("/auth/login", json=credenciais)
    assert r.status_code == 401
    assert r.json() == {"detail": "RM ou senha inválidos.", "codigo": "CREDENCIAIS_INVALIDAS"}


def test_login_validacao_de_tamanho(client):
    assert client.post("/auth/login", json={"rm": "admin", "senha": "x" * 129}).status_code == 422
    assert client.post("/auth/login", json={"rm": "a" * 51, "senha": "x"}).status_code == 422
    assert client.post("/auth/login", data={"username": "admin", "password": "x"}).status_code == 422


def test_conta_inativa_nao_loga_e_token_antigo_para_de_valer(client, admin, novo_professor):
    headers, prof = novo_professor("inat01", senha="senhaInat1")
    assert client.get("/auth/me", headers=headers).status_code == 200
    r = client.put(f"/professores/{prof['id']}", headers=admin, json={"nome": prof["nome"], "email": None, "papel": "professor", "ativo": False})
    assert r.status_code == 200
    r = client.get("/auth/me", headers=headers)
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")
    r = client.post("/auth/login", json={"rm": "inat01", "senha": "senhaInat1"})
    assert r.json() == {"detail": "RM ou senha inválidos.", "codigo": "CREDENCIAIS_INVALIDAS"}


def test_papel_vem_do_banco_nao_do_token(client, admin, novo_professor):
    headers, prof = novo_professor("promo01")
    assert client.get("/professores", headers=headers).status_code == 403
    client.put(f"/professores/{prof['id']}", headers=admin, json={"nome": prof["nome"], "email": None, "papel": "admin", "ativo": True})
    assert client.get("/professores", headers=headers).status_code == 200  # mesmo token, agora admin
    client.put(f"/professores/{prof['id']}", headers=admin, json={"nome": prof["nome"], "email": None, "papel": "professor", "ativo": True})
    assert client.get("/professores", headers=headers).status_code == 403


def _forjar(payload, segredo=None, alg="HS256"):
    return jwt.encode(payload, segredo or obter_config().JWT_SECRET, algorithm=alg)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(lambda now: _forjar({"sub": "1", "papel": "admin", "iat": now - 7200, "exp": now - 60}), id="expirado"),
        pytest.param(lambda now: _forjar({"sub": "1", "papel": "admin", "iat": now, "exp": now + 600}, "outro-segredo-qualquer-1234"), id="segredo-errado"),
        pytest.param(lambda now: _forjar({"sub": "1", "papel": "admin", "iat": now}), id="sem-exp"),
        pytest.param(lambda now: _forjar({"papel": "admin", "iat": now, "exp": now + 600}), id="sem-sub"),
        pytest.param(lambda now: _forjar({"sub": "abc", "iat": now, "exp": now + 600}), id="sub-invalido"),
        pytest.param(lambda now: _forjar({"sub": "99999", "iat": now, "exp": now + 600}), id="usuario-inexistente"),
        pytest.param(lambda now: _forjar({"sub": "1", "iat": now, "exp": now + 600}, alg="HS512"), id="alg-HS512"),
        pytest.param(lambda now: jwt.encode({"sub": "1", "exp": now + 600}, key=None, algorithm="none"), id="alg-none"),
    ],
)
def test_token_invalido_rejeitado(client, token):
    now = int(agora_tz().timestamp())
    r = client.get("/professores", headers={"Authorization": f"Bearer {token(now)}"})
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")


def test_token_adulterado(client):
    token = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).json()["access_token"]
    cab, corpo, assinatura = token.split(".")
    adulterado = f"{cab}.{corpo}.{assinatura[:-4]}AAAA"
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {adulterado}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Basic {token}"}).status_code == 401


def test_rate_limit_de_login(client):
    for _ in range(4):
        assert client.post("/auth/login", json={"rm": "admin", "senha": "errada"}).status_code == 401
    # sucesso zera o contador
    assert client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).status_code == 200
    for _ in range(5):
        assert client.post("/auth/login", json={"rm": "x", "senha": "errada"}).status_code == 401
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert (r.status_code, r.json()["codigo"]) == (429, "MUITAS_TENTATIVAS")


def test_troca_de_senha(client, novo_professor):
    headers, _ = novo_professor("troca01", senha="senhaVelha1")
    r = client.put("/auth/me/senha", headers=headers, json={"senha_atual": "errada", "nova_senha": "senhaNova12"})
    assert (r.status_code, r.json()["codigo"]) == (422, "SENHA_ATUAL_INCORRETA")
    r = client.put("/auth/me/senha", headers=headers, json={"senha_atual": "senhaVelha1", "nova_senha": "curta"})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    assert client.put("/auth/me/senha", headers=headers, json={"senha_atual": "senhaVelha1", "nova_senha": "senhaNova12"}).status_code == 204
    assert client.post("/auth/login", json={"rm": "troca01", "senha": "senhaVelha1"}).status_code == 401
    token_de(client, "troca01", "senhaNova12")


def test_senha_guardada_com_bcrypt(db, client, novo_professor):
    novo_professor("hash01", senha="senhaHash1")
    hash_ = db.scalar(select(Professor.senha_hash).where(Professor.rm == "hash01"))
    assert hash_.startswith("$2") and "senhaHash1" not in hash_


def test_admin_nao_opera_em_si_mesmo(client, admin):
    eu = client.get("/auth/me", headers=admin).json()
    for corpo in ({"nome": "A", "email": None, "papel": "admin", "ativo": False}, {"nome": "A", "email": None, "papel": "professor", "ativo": True}):
        r = client.put(f"/professores/{eu['id']}", headers=admin, json=corpo)
        assert (r.status_code, r.json()["codigo"]) == (422, "OPERACAO_EM_SI_MESMO")
    r = client.delete(f"/professores/{eu['id']}", headers=admin)
    assert (r.status_code, r.json()["codigo"]) == (422, "OPERACAO_EM_SI_MESMO")


def test_professores_validacao_e_duplicidade(client, admin):
    base = {"nome": "N", "senha": "senhaBoa12"}
    for rm in ("ab", "a" * 21, "rm com espaco", "rm-traco", "../x"):
        assert client.post("/professores", headers=admin, json={**base, "rm": rm}).status_code == 422, rm
    assert client.post("/professores", headers=admin, json={**base, "rm": "abc", "senha": "1234567"}).status_code == 422
    assert client.post("/professores", headers=admin, json={**base, "rm": "abc", "email": "nao-email"}).status_code == 422
    assert client.post("/professores", headers=admin, json={**base, "rm": "abc", "papel": "root"}).status_code == 422
    assert client.post("/professores", headers=admin, json={**base, "rm": "abc"}).status_code == 201
    r = client.post("/professores", headers=admin, json={**base, "rm": "abc"})
    assert (r.status_code, r.json()["codigo"]) == (409, "RM_DUPLICADO")


# ---------------------------------------------------------------- exposição de dados
def _chaves(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _chaves(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _chaves(x)


def test_respostas_publicas_nunca_trazem_rm_nem_senha(client, admin, professor, sala_id, aulas, semestre_ref):
    d = "2030-03-05"
    reserva = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": d, "horario_ids": [aulas["manha"][0]]}).json()
    client.post(f"/reservas/{reserva['id']}/cancelar", headers=admin)
    reserva = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": d, "horario_ids": [aulas["manha"][0]]}).json()
    respostas = [
        client.get("/reservas", params={"data": d, "status": "todas"}).json(),
        client.get(f"/reservas/{reserva['id']}").json(),
        client.get(f"/salas/{sala_id}/disponibilidade", params={"data": d}).json(),
        client.post("/reservas", headers=admin, json={"sala_id": sala_id, "data": d, "horario_ids": [aulas["manha"][0]]}).json(),
        client.post("/reservas/recorrentes/previa", headers=admin, json={"sala_id": sala_id, "data_inicio": d, "horario_ids": [aulas["manha"][0]]}).json(),
        client.get("/reservas/minhas", headers=professor).json(),
        client.get(f"/salas/{sala_id}").json(),
    ]
    for corpo in respostas:
        chaves = set(_chaves(corpo))
        assert not chaves & {"rm", "senha", "senha_hash"}, corpo
    # visão admin de contas traz RM, nunca hash
    for u in client.get("/professores", headers=admin).json():
        assert "rm" in u and "senha_hash" not in u and "senha" not in u


# ---------------------------------------------------------------- SQL injection / erros / CORS
@pytest.mark.parametrize("busca", ["'; DROP TABLE salas; --", "%", "_", "\\", "Sala' OR '1'='1"])
def test_busca_nao_injeta_sql(client, db, busca):
    r = client.get("/salas", params={"busca": busca})
    assert r.status_code == 200
    assert r.json() == []  # %, _ e \ são literais (escapados no ILIKE)
    assert db.scalar(select(func.count()).select_from(Sala)) == 27
    for rota in ("/professores", "/equipamentos", "/softwares"):
        params = {"busca": busca}
        headers = token_de(client, "admin", "senhaAdmin123") if rota == "/professores" else {}
        assert client.get(rota, params=params, headers=headers).status_code == 200


def test_erro_500_sem_stack_trace(monkeypatch):
    from app.services import salas as servico

    def explode(*_a, **_k):
        raise RuntimeError("segredo interno: postgresql://user:senha@host/db")

    monkeypatch.setattr(servico, "listar", explode)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/salas")
    assert r.status_code == 500
    assert r.json() == {"detail": "Erro interno no servidor. Tente novamente.", "codigo": "ERRO_INTERNO"}
    assert "Traceback" not in r.text and "segredo" not in r.text


def test_404_e_405_no_envelope(client):
    assert client.get("/nao-existe").json()["codigo"] == "NAO_ENCONTRADO"
    r = client.patch("/salas")
    assert r.status_code == 405 and r.json()["codigo"] == "METODO_NAO_PERMITIDO"


def test_cors_so_para_origens_configuradas(client):
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}
    ok = client.options("/reservas", headers={"Origin": "http://localhost:5173", **preflight})
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in ok.headers
    ruim = client.options("/reservas", headers={"Origin": "http://evil.example", **preflight})
    assert "access-control-allow-origin" not in ruim.headers
    simples = client.get("/salas/tipos", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in simples.headers


def test_documentacao_sem_segredos(client):
    texto = client.get("/openapi.json").text
    assert obter_config().JWT_SECRET not in texto


def test_tabelas_intactas_depois_de_tudo(db):
    assert db.scalar(text("SELECT count(*) FROM pg_tables WHERE tablename = 'salas'")) == 1


def test_token_expira_conforme_config(client):
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).json()
    from datetime import datetime

    expira = datetime.fromisoformat(r["expira_em"])
    delta = expira - agora_tz()
    assert timedelta(minutes=obter_config().JWT_EXPIRA_MINUTOS - 1) < delta <= timedelta(minutes=obter_config().JWT_EXPIRA_MINUTOS)
