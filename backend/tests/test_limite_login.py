"""Ticket 31 / ADR-0007: limite de login por par (IP, RM) com teto por IP, relógio controlável."""

import random
import string

import pytest

from app.core import seguranca
from app.core.seguranca import BLOQUEIO_S, JANELA_S, MAX_FALHAS_IP, MAX_FALHAS_PAR, LimiteLogin


class RelogioFalso:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def avancar(self, segundos: float) -> None:
        self.t += segundos


@pytest.fixture
def relogio():
    return RelogioFalso()


@pytest.fixture
def limite(relogio):
    return LimiteLogin(relogio=relogio)


def test_constantes_do_adr():
    assert (MAX_FALHAS_PAR, MAX_FALHAS_IP, JANELA_S, BLOQUEIO_S) == (5, 20, 300, 300)


def test_par_bloqueia_so_o_proprio_rm(limite):
    for _ in range(MAX_FALHAS_PAR - 1):
        limite.registrar_falha("10.0.0.1", "A")
    assert not limite.bloqueado("10.0.0.1", "A")
    limite.registrar_falha("10.0.0.1", "A")
    assert limite.bloqueado("10.0.0.1", "A")
    assert not limite.bloqueado("10.0.0.1", "B")  # mesmo IP, outro RM
    assert not limite.bloqueado("10.0.0.2", "A")  # mesmo RM, outro IP


def test_rm_exatamente_como_digitado(limite):
    for _ in range(MAX_FALHAS_PAR):
        limite.registrar_falha("10.0.0.1", "abc")
    assert limite.bloqueado("10.0.0.1", "abc")
    assert not limite.bloqueado("10.0.0.1", "ABC")
    assert not limite.bloqueado("10.0.0.1", " abc")


def test_teto_por_ip_com_rms_variados(limite):
    for i in range(MAX_FALHAS_IP - 1):
        limite.registrar_falha("10.0.0.1", f"rm{i}")  # 1 falha por RM: nenhum par chega a 5
    assert not limite.bloqueado("10.0.0.1", "qualquer")
    limite.registrar_falha("10.0.0.1", "rm-final")
    assert limite.bloqueado("10.0.0.1", "qualquer")
    assert limite.bloqueado("10.0.0.1", "rm0")
    assert not limite.bloqueado("10.0.0.2", "qualquer")


def test_bloqueio_expira_em_5_minutos(limite, relogio):
    for _ in range(MAX_FALHAS_PAR):
        limite.registrar_falha("ip", "A")
    relogio.avancar(BLOQUEIO_S - 1)
    assert limite.bloqueado("ip", "A")
    relogio.avancar(1)
    assert not limite.bloqueado("ip", "A")
    # expirado, recomeça do zero: uma falha não bloqueia de novo
    limite.registrar_falha("ip", "A")
    assert not limite.bloqueado("ip", "A")


def test_bloqueio_por_ip_expira(limite, relogio):
    for i in range(MAX_FALHAS_IP):
        limite.registrar_falha("ip", f"r{i}")
    assert limite.bloqueado("ip", "x")
    relogio.avancar(BLOQUEIO_S)
    assert not limite.bloqueado("ip", "x")


def test_falhas_fora_da_janela_nao_contam(limite, relogio):
    for _ in range(MAX_FALHAS_PAR - 1):
        limite.registrar_falha("ip", "A")
    relogio.avancar(JANELA_S)
    limite.registrar_falha("ip", "A")
    assert not limite.bloqueado("ip", "A")


def test_sucesso_zera_so_o_par(limite):
    for i in range(MAX_FALHAS_PAR - 1):
        limite.registrar_falha("ip", "A")
    for i in range(MAX_FALHAS_IP - 2 * (MAX_FALHAS_PAR - 1)):
        limite.registrar_falha("ip", f"outro{i}")
    limite.registrar_sucesso("ip", "A")
    limite.registrar_falha("ip", "A")
    assert not limite.bloqueado("ip", "A")  # o par recomeçou
    for _ in range(MAX_FALHAS_PAR - 2):
        limite.registrar_falha("ip", "B")
    # as falhas do IP não foram zeradas pelo sucesso: chegou a 20
    assert limite.bloqueado("ip", "B")


def test_estruturas_descartam_entradas_vencidas(limite, relogio):
    sorteio = random.Random(31)
    for _ in range(500):
        ip = f"10.0.{sorteio.randint(0, 3)}.{sorteio.randint(0, 255)}"
        rm = "".join(sorteio.choices(string.ascii_letters + string.digits, k=8))
        limite.registrar_falha(ip, rm)
        relogio.avancar(0.1)
    assert limite.tamanho() > 0
    relogio.avancar(max(JANELA_S, BLOQUEIO_S) + 1)
    limite.registrar_falha("1.1.1.1", "ultimo")  # registrar uma falha faz a limpeza
    # sobram só as duas entradas da última falha (par e IP)
    assert limite.tamanho() == 2
    assert set(limite._par.falhas) == {("1.1.1.1", "ultimo")}
    assert set(limite._ip.falhas) == {"1.1.1.1"}
    assert not limite._par.bloqueado_ate and not limite._ip.bloqueado_ate


def test_limpar(limite):
    for _ in range(MAX_FALHAS_IP):
        limite.registrar_falha("ip", "A")
    limite.limpar()
    assert limite.tamanho() == 0 and not limite.bloqueado("ip", "A")


# ---------------------------------------------------------------- pela API, com o relógio controlado
def test_api_login_certo_durante_e_depois_do_bloqueio(client, monkeypatch, relogio):
    monkeypatch.setattr(seguranca.limite_login, "relogio", relogio)
    for _ in range(MAX_FALHAS_PAR):
        assert client.post("/auth/login", json={"rm": "admin", "senha": "errada"}).status_code == 401
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert (r.status_code, r.json()["codigo"]) == (429, "MUITAS_TENTATIVAS")
    relogio.avancar(BLOQUEIO_S)
    assert client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).status_code == 200
    # o login certo zerou as falhas do par: 4 novas falhas não bloqueiam
    for _ in range(MAX_FALHAS_PAR - 1):
        assert client.post("/auth/login", json={"rm": "admin", "senha": "errada"}).status_code == 401
    assert client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).status_code == 200


def test_api_teto_por_ip_expira(client, monkeypatch, relogio, novo_professor):
    novo_professor("ipteto1", senha="senhaIp123")
    monkeypatch.setattr(seguranca.limite_login, "relogio", relogio)
    for i in range(MAX_FALHAS_IP):
        assert client.post("/auth/login", json={"rm": f"nao{i}", "senha": "errada"}).status_code == 401
    r = client.post("/auth/login", json={"rm": "ipteto1", "senha": "senhaIp123"})
    assert (r.status_code, r.json()["codigo"]) == (429, "MUITAS_TENTATIVAS")
    relogio.avancar(BLOQUEIO_S)
    assert client.post("/auth/login", json={"rm": "ipteto1", "senha": "senhaIp123"}).status_code == 200
