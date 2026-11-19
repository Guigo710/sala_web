"""Ticket 50: limite de tentativas de `senha_atual` em `PUT /auth/me/senha`, por conta (mecanismo do ADR-0007)."""

import pytest

from app.core import seguranca
from app.core.seguranca import BLOQUEIO_S, JANELA_S, MAX_FALHAS_TROCA, LimiteTrocaSenha

ROTA = "/auth/me/senha"


class RelogioFalso:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def avancar(self, segundos: float) -> None:
        self.t += segundos


@pytest.fixture
def relogio(monkeypatch):
    r = RelogioFalso()
    monkeypatch.setattr(seguranca.limite_troca_senha, "relogio", r)
    return r


def _chutar(client, headers, vezes=MAX_FALHAS_TROCA):
    for _ in range(vezes):
        r = client.put(ROTA, headers=headers, json={"senha_atual": "errada", "nova_senha": "senhaNova123"})
        assert (r.status_code, r.json()["codigo"]) == (422, "SENHA_ATUAL_INCORRETA")


def _certa(client, headers, atual="senhaProf1", nova="senhaNova123"):
    return client.put(ROTA, headers=headers, json={"senha_atual": atual, "nova_senha": nova})


def test_constante():
    assert MAX_FALHAS_TROCA == 5


def test_sexta_tentativa_mesmo_certa_da_429(client, professor, relogio):
    _chutar(client, professor)
    r = _certa(client, professor)
    assert r.status_code == 429
    corpo = r.json()
    assert corpo["codigo"] == "MUITAS_TENTATIVAS"
    assert set(corpo) == {"codigo", "detail"}
    # a senha não mudou: o login com a senha antiga continua valendo
    assert client.post("/auth/login", json={"rm": "prof01", "senha": "senhaProf1"}).status_code == 200


def test_mesmo_envelope_do_login(client, professor, relogio):
    _chutar(client, professor)
    troca = _certa(client, professor)
    for _ in range(seguranca.MAX_FALHAS_PAR):
        client.post("/auth/login", json={"rm": "admin", "senha": "errada"})
    login = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert troca.status_code == login.status_code == 429
    assert set(troca.json()) == set(login.json())
    assert troca.json()["codigo"] == login.json()["codigo"]


def test_outra_conta_nao_e_afetada(client, professor, admin, relogio):
    _chutar(client, professor)
    assert _certa(client, professor).status_code == 429
    r = _certa(client, admin, atual="senhaAdmin123", nova="senhaAdmin456")
    assert r.status_code == 200, r.text


def test_limite_vence_depois_do_bloqueio(client, professor, relogio):
    _chutar(client, professor)
    relogio.avancar(BLOQUEIO_S - 1)
    assert _certa(client, professor).status_code == 429
    relogio.avancar(1)
    r = _certa(client, professor)
    assert r.status_code == 200, r.text


def test_acerto_zera_o_contador(client, professor, relogio):
    _chutar(client, professor, MAX_FALHAS_TROCA - 1)
    r = _certa(client, professor)
    assert r.status_code == 200
    novo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    _chutar(client, novo, MAX_FALHAS_TROCA - 1)
    assert _certa(client, novo, atual="senhaNova123", nova="senhaOutra123").status_code == 200


def test_falhas_fora_da_janela_nao_contam(client, professor, relogio):
    _chutar(client, professor, MAX_FALHAS_TROCA - 1)
    relogio.avancar(JANELA_S)
    _chutar(client, professor, 1)
    assert _certa(client, professor).status_code == 200


def test_bloqueio_vale_para_qualquer_token_da_conta(client, professor, relogio):
    _chutar(client, professor)
    r = client.post("/auth/login", json={"rm": "prof01", "senha": "senhaProf1"})
    outro = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert _certa(client, outro).status_code == 429


def test_nao_mexe_no_limite_de_login(client, professor, relogio):
    _chutar(client, professor)
    assert seguranca.limite_login.tamanho() == 0


def test_estrutura_descarta_vencidos():
    relogio = RelogioFalso()
    limite = LimiteTrocaSenha(relogio=relogio)
    for i in range(200):
        limite.registrar_falha(i)
    assert limite.tamanho() == 200
    relogio.avancar(max(JANELA_S, BLOQUEIO_S) + 1)
    limite.registrar_falha(999)
    assert limite.tamanho() == 1
    limite.limpar()
    assert limite.tamanho() == 0 and not limite.bloqueado(999)
