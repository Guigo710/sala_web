"""Ticket 41 / ADR-0008: revogação de tokens por `token_versao` (contrato 1.2)."""

import os

import jwt
import pytest
from alembic.config import Config as AlembicConfig
from sqlalchemy import select, text

from alembic import command
from app.core.config import obter_config
from app.core.tempo import agora_tz
from app.models import Professor
from tests.conftest import PASTA_BACKEND, token_de


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, rm: str, senha: str) -> str:
    r = client.post("/auth/login", json={"rm": rm, "senha": senha})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _vale(client, token: str) -> bool:
    r = client.get("/auth/me", headers=_bearer(token))
    assert r.status_code in (200, 401), r.text
    if r.status_code == 401:
        assert r.json()["codigo"] == "NAO_AUTENTICADO"
    return r.status_code == 200


def _versao(db, rm: str) -> int:
    db.expire_all()
    return db.scalar(select(Professor.token_versao).where(Professor.rm == rm))


def _put_professor(client, admin, prof: dict, **campos):
    corpo = {"nome": prof["nome"], "email": prof["email"], "papel": prof["papel"], "ativo": prof["ativo"]} | campos
    r = client.put(f"/professores/{prof['id']}", headers=admin, json=corpo)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- migration
def test_migration_0002_sobe_e_desce_com_dados(db):
    cfg = AlembicConfig(os.path.join(PASTA_BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(PASTA_BACKEND, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"].replace("%", "%%"))
    db.close()
    try:
        command.downgrade(cfg, "-1")
        with db.bind.connect() as conn:
            colunas = conn.scalars(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'professores'")
            ).all()
            assert "token_versao" not in colunas
            assert conn.scalar(text("SELECT count(*) FROM professores")) >= 1  # dados preservados
    finally:
        command.upgrade(cfg, "head")
    with db.bind.connect() as conn:
        versoes = conn.scalars(text("SELECT token_versao FROM professores")).all()
    assert versoes and set(versoes) == {0}


# ---------------------------------------------------------------- claim ver
def test_token_traz_claim_ver(client):
    claims = jwt.decode(_login(client, "admin", "senhaAdmin123"), options={"verify_signature": False})
    assert claims["ver"] == 0


def test_token_sem_ver_e_invalido(client, professor, sala_id, aulas):
    eu = client.get("/auth/me", headers=professor).json()
    agora = int(agora_tz().timestamp())
    antigo = jwt.encode(
        {"sub": str(eu["id"]), "papel": "professor", "iat": agora, "exp": agora + 600},
        obter_config().JWT_SECRET,
        algorithm="HS256",
    )
    r = client.get("/auth/me", headers=_bearer(antigo))
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")
    # rota pública: tratado como visitante
    from tests.conftest import proximo_dia_semana

    data = proximo_dia_semana(3).isoformat()
    criada = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": data, "horario_ids": [aulas["manha"][0]]})
    assert criada.status_code == 201, criada.text
    r = client.get("/reservas", params={"data": data}, headers=_bearer(antigo))
    assert r.status_code == 200
    assert [x["pode_cancelar"] for x in r.json()] == [False]
    assert client.get("/reservas", params={"data": data}, headers=professor).json()[0]["pode_cancelar"] is True


@pytest.mark.parametrize("ver", ["0", None, True, 1.0])
def test_claim_ver_de_tipo_errado_e_invalida(client, ver):
    agora = int(agora_tz().timestamp())
    token = jwt.encode(
        {"sub": "1", "papel": "admin", "ver": ver, "iat": agora, "exp": agora + 600},
        obter_config().JWT_SECRET,
        algorithm="HS256",
    )
    assert not _vale(client, token)


# ---------------------------------------------------------------- PUT /auth/me/senha
def test_troca_da_propria_senha_devolve_token_novo_e_derruba_os_outros(client, db, novo_professor):
    novo_professor("troca02", senha="senhaVelha1")
    atual = _login(client, "troca02", "senhaVelha1")
    outro_dispositivo = _login(client, "troca02", "senhaVelha1")
    assert _vale(client, atual) and _vale(client, outro_dispositivo)  # dois logins convivem

    r = client.put("/auth/me/senha", headers=_bearer(atual), json={"senha_atual": "senhaVelha1", "nova_senha": "senhaNova12"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert set(corpo) == {"access_token", "token_type", "expira_em", "usuario"}
    assert corpo["token_type"] == "bearer" and corpo["usuario"]["rm"] == "troca02"
    assert "token_versao" not in corpo["usuario"]
    novo = corpo["access_token"]

    assert _vale(client, novo)
    assert not _vale(client, atual)
    assert not _vale(client, outro_dispositivo)
    assert _versao(db, "troca02") == 1
    assert jwt.decode(novo, options={"verify_signature": False})["ver"] == 1
    assert client.post("/auth/login", json={"rm": "troca02", "senha": "senhaVelha1"}).status_code == 401
    token_de(client, "troca02", "senhaNova12")


@pytest.mark.parametrize(
    ("corpo", "codigo"),
    [
        ({"senha_atual": "errada", "nova_senha": "senhaNova12"}, "SENHA_ATUAL_INCORRETA"),
        ({"senha_atual": "senhaVelha1", "nova_senha": "curta"}, "VALIDACAO"),
    ],
)
def test_troca_de_senha_com_erro_nao_revoga(client, db, novo_professor, corpo, codigo):
    novo_professor("troca03", senha="senhaVelha1")
    atual = _login(client, "troca03", "senhaVelha1")
    r = client.put("/auth/me/senha", headers=_bearer(atual), json=corpo)
    assert (r.status_code, r.json()["codigo"]) == (422, codigo)
    assert _vale(client, atual)
    assert _versao(db, "troca03") == 0


def test_openapi_da_troca_de_senha_documenta_200_com_token(client):
    operacao = client.get("/openapi.json").json()["paths"]["/auth/me/senha"]["put"]
    assert "204" not in operacao["responses"]
    esquema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert esquema["$ref"].endswith("/LoginSaida")


# ---------------------------------------------------------------- PUT /professores/{id}/senha
def test_redefinicao_pelo_admin_revoga_so_a_conta_alvo(client, db, admin, novo_professor):
    alvo_headers, alvo = novo_professor("alvo02", senha="senhaAlvo1")
    outro_headers, _ = novo_professor("outro02", senha="senhaOutro1")
    r = client.put(f"/professores/{alvo['id']}/senha", headers=admin, json={"nova_senha": "senhaNova12"})
    assert r.status_code == 204
    assert client.get("/auth/me", headers=alvo_headers).status_code == 401
    assert client.get("/auth/me", headers=outro_headers).status_code == 200
    assert client.get("/auth/me", headers=admin).status_code == 200
    token_de(client, "alvo02", "senhaNova12")
    assert _versao(db, "alvo02") == 1 and _versao(db, "outro02") == 0


def test_admin_redefinindo_a_propria_senha_perde_a_sessao(client, admin):
    eu = client.get("/auth/me", headers=admin).json()
    assert client.put(f"/professores/{eu['id']}/senha", headers=admin, json={"nova_senha": "senhaAdminNova1"}).status_code == 204
    assert client.get("/auth/me", headers=admin).status_code == 401
    token_de(client, "admin", "senhaAdminNova1")


# ---------------------------------------------------------------- PUT /professores/{id}
def test_mudar_papel_revoga(client, db, admin, novo_professor):
    headers, prof = novo_professor("papel02")
    _put_professor(client, admin, prof, papel="admin")
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert _versao(db, "papel02") == 1
    novo = token_de(client, "papel02", "senhaProf1")
    assert client.get("/professores", headers=novo).status_code == 200


def test_mudar_nome_email_ou_put_igual_nao_revoga(client, db, admin, novo_professor):
    headers, prof = novo_professor("nome02")
    prof = _put_professor(client, admin, prof, nome="Outro Nome", email="novo@escola.edu.br")
    prof = _put_professor(client, admin, prof)  # PUT sem mudança nenhuma
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert _versao(db, "nome02") == 0


def test_desativar_revoga_e_reativar_nao_revive(client, db, admin, novo_professor):
    headers, prof = novo_professor("ativo02", senha="senhaAtivo1")
    prof = _put_professor(client, admin, prof, ativo=False)
    assert _versao(db, "ativo02") == 1
    prof = _put_professor(client, admin, prof, ativo=False)  # continuar inativo não incrementa
    assert _versao(db, "ativo02") == 1
    prof = _put_professor(client, admin, prof, ativo=True)  # reativação não incrementa
    assert _versao(db, "ativo02") == 1
    r = client.get("/auth/me", headers=headers)
    assert (r.status_code, r.json()["codigo"]) == (401, "NAO_AUTENTICADO")
    assert client.get("/auth/me", headers=token_de(client, "ativo02", "senhaAtivo1")).status_code == 200


def test_put_com_erro_nao_revoga(client, db, admin, novo_professor):
    headers, prof = novo_professor("erro02")
    r = client.put(f"/professores/{prof['id']}", headers=admin, json={"nome": "", "papel": "admin", "ativo": False})
    assert r.status_code == 422
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert _versao(db, "erro02") == 0


def test_login_nao_incrementa(client, db, novo_professor):
    novo_professor("login02", senha="senhaLogin1")
    tokens = [_login(client, "login02", "senhaLogin1") for _ in range(3)]
    assert all(_vale(client, t) for t in tokens)
    assert _versao(db, "login02") == 0


def test_usuario_nunca_expoe_token_versao(client, admin):
    for u in client.get("/professores", headers=admin).json():
        assert "token_versao" not in u
    assert "token_versao" not in client.get("/auth/me", headers=admin).json()
