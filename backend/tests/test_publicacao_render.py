"""Ticket 62 (ADR-0009): API pronta para o Render: porta `PORT`, CORS de produção, teto de login por IP
configurável e rotas sem redirecionamento de barra final."""

import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as modulo_main
import app.services.auth as servico_auth
from app.core.config import Config, normalizar_origens
from app.core.seguranca import MAX_FALHAS_IP, MAX_FALHAS_PAR, LimiteLogin
from tests.conftest import PASTA_BACKEND

RAIZ = Path(PASTA_BACKEND).parent


def _config(**valores) -> Config:
    return Config(_env_file=None, DATABASE_URL=os.environ["DATABASE_URL"], JWT_SECRET="x" * 40, **valores)


# ---------------------------------------------------------------- LOGIN_MAX_FALHAS_IP
def test_login_max_falhas_ip_padrao_e_validacao(monkeypatch):
    monkeypatch.delenv("LOGIN_MAX_FALHAS_IP", raising=False)
    assert _config().LOGIN_MAX_FALHAS_IP == MAX_FALHAS_IP == 20
    monkeypatch.setenv("LOGIN_MAX_FALHAS_IP", "0")
    assert _config().LOGIN_MAX_FALHAS_IP == 0
    monkeypatch.setenv("LOGIN_MAX_FALHAS_IP", "-1")
    with pytest.raises(ValueError, match="LOGIN_MAX_FALHAS_IP"):
        _config()


def test_limite_login_da_config(monkeypatch):
    import app.core.seguranca as seguranca

    monkeypatch.setattr(seguranca, "obter_config", lambda: _config(LOGIN_MAX_FALHAS_IP=0))
    assert LimiteLogin.da_config().teto_ip_ligado is False
    monkeypatch.setattr(seguranca, "obter_config", lambda: _config(LOGIN_MAX_FALHAS_IP=7))
    limite = LimiteLogin.da_config()
    for i in range(6):
        limite.registrar_falha("1.1.1.1", f"rm{i}")
    assert not limite.bloqueado("1.1.1.1", "outro")
    limite.registrar_falha("1.1.1.1", "rm7")
    assert limite.bloqueado("1.1.1.1", "outro")


def test_teto_ip_zero_so_desliga_o_teto_por_ip():
    limite = LimiteLogin(max_falhas_ip=0)
    for i in range(30):
        limite.registrar_falha("10.0.0.1", f"rm{i:02d}")
        assert not limite.bloqueado("10.0.0.1", f"rm{i:02d}")
    assert not limite.bloqueado("10.0.0.1", "qualquer")
    for _ in range(MAX_FALHAS_PAR):
        limite.registrar_falha("10.0.0.1", "alvo")
    assert limite.bloqueado("10.0.0.1", "alvo")
    assert not limite.bloqueado("10.0.0.1", "outro")
    assert limite.tamanho() == 30 + 1 + 1  # o contador por IP nem guarda nada
    with pytest.raises(ValueError):
        LimiteLogin(max_falhas_ip=-1)


def test_login_pela_api_com_teto_ip_desligado(client, monkeypatch, professor):
    monkeypatch.setattr(servico_auth, "limite_login", LimiteLogin(max_falhas_ip=0))
    for i in range(30):
        r = client.post("/auth/login", json={"rm": f"naoexiste{i:02d}", "senha": "errada"})
        assert (r.status_code, r.json()["codigo"]) == (401, "CREDENCIAIS_INVALIDAS"), i
    assert client.post("/auth/login", json={"rm": "prof01", "senha": "senhaProf1"}).status_code == 200
    for _ in range(MAX_FALHAS_PAR):
        assert client.post("/auth/login", json={"rm": "prof01", "senha": "errada"}).status_code == 401
    r = client.post("/auth/login", json={"rm": "prof01", "senha": "senhaProf1"})
    assert (r.status_code, r.json()["codigo"]) == (429, "MUITAS_TENTATIVAS")
    assert client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"}).status_code == 200


def test_login_pela_api_padrao_mantem_teto_20(client):
    for i in range(MAX_FALHAS_IP):
        assert client.post("/auth/login", json={"rm": f"x{i:02d}", "senha": "errada"}).status_code == 401
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert (r.status_code, r.json()["codigo"]) == (429, "MUITAS_TENTATIVAS")


# ---------------------------------------------------------------- CORS_ORIGENS
def test_normalizar_origens():
    assert normalizar_origens("https://a.vercel.app/ , http://localhost:5173") == [
        "https://a.vercel.app",
        "http://localhost:5173",
    ]
    assert normalizar_origens(" HTTPS://Sala-Web.Vercel.App// ,, https://a.com:443, http://b.com:80,http://[::1]:8000") == [
        "https://sala-web.vercel.app",
        "https://a.com",
        "http://b.com",
        "http://[::1]:8000",
    ]
    assert normalizar_origens("") == []
    assert normalizar_origens("https://a.com,https://a.com/") == ["https://a.com"]


@pytest.mark.parametrize(
    ("valor", "trecho"),
    [
        ("*", "sem curingas"),
        ("https://a.vercel.app,*", "sem curingas"),
        ("https://*.vercel.app", "sem curingas"),
        ("https://a.vercel.app/agenda", "não é uma origem"),
        ("a.vercel.app", "não é uma origem"),
        ("https://a.vercel.app?x=1", "não é uma origem"),
        ("https://usuario@a.vercel.app", "não é uma origem"),
        ("ftp://a.vercel.app", "não é uma origem"),
        ("https://a.com:99999", "não é uma origem"),
        ("https://", "não é uma origem"),
    ],
)
def test_origem_invalida_recusada(valor, trecho):
    with pytest.raises(ValueError, match=trecho) as erro:
        _config(CORS_ORIGENS=valor)
    assert "CORS_ORIGENS" in str(erro.value)
    assert "https://sala-web.vercel.app" in str(erro.value)


def _app_com(monkeypatch, cors: str):
    config = _config(CORS_ORIGENS=cors)
    monkeypatch.setattr(modulo_main, "obter_config", lambda: config)
    return modulo_main.criar_app()


def test_preflight_com_barra_final_e_espacos(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="sala_web")
    app = _app_com(monkeypatch, "https://a.vercel.app/ , http://localhost:5173")
    assert "CORS liberado para: https://a.vercel.app, http://localhost:5173" in caplog.text
    with TestClient(app) as c:
        r = c.options(
            "/salas",
            headers={"Origin": "https://a.vercel.app", "Access-Control-Request-Method": "GET"},
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "https://a.vercel.app"
        r = c.options(
            "/salas", headers={"Origin": "https://b.vercel.app", "Access-Control-Request-Method": "GET"}
        )
        assert "access-control-allow-origin" not in r.headers


@pytest.mark.parametrize("valor", ["*", "https://a.vercel.app/agenda"])
def test_api_nao_sobe_com_cors_invalido(valor):
    env = {**os.environ, "CORS_ORIGENS": valor}
    r = subprocess.run(
        [sys.executable, "-c", "import app.main"], cwd=PASTA_BACKEND, env=env, capture_output=True, text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert "CORS_ORIGENS" in r.stderr and "https://sala-web.vercel.app" in r.stderr
    assert valor in r.stderr


# ---------------------------------------------------------------- barra final
def test_barra_final_nao_redireciona(client, admin):
    for rota in ("/salas/", "/reservas/", "/horarios/", "/auth/me/"):
        r = client.get(rota, headers=admin, follow_redirects=False)
        assert r.status_code == 404, (rota, r.status_code)
        assert "location" not in r.headers
        assert r.json()["codigo"] == "NAO_ENCONTRADO"
    assert client.get("/salas").status_code == 200


# ---------------------------------------------------------------- porta e worker (Dockerfile)
def test_dockerfile_porta_do_render_e_um_worker():
    dockerfile = (Path(PASTA_BACKEND) / "Dockerfile").read_text(encoding="utf-8")
    cmd = next(linha for linha in dockerfile.splitlines() if linha.startswith("CMD"))
    assert "--port ${PORT:-8000}" in cmd
    assert "--workers" not in cmd
    assert re.search(r"alembic upgrade head && python -m app\.seed && python -m app\.importar_fotos && .*uvicorn", cmd)
    assert "USER 10001:10001" in dockerfile


def test_env_example_documenta_variaveis_novas():
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for nome in ("LOGIN_MAX_FALHAS_IP", "DB_POOL_TAMANHO", "DB_POOL_EXTRA", "DB_POOL_RECICLAR_S", "DB_CONEXAO_TIMEOUT_S"):
        assert nome in exemplo, nome
    assert re.search(r"LOGIN_MAX_FALHAS_IP.*\n?.*no Render use 0", exemplo) or "no Render use 0" in exemplo


# ---------------------------------------------------------------- render.yaml (ticket 64)
def test_render_yaml_sem_segredos_e_com_os_campos_do_guia():
    import yaml

    blueprint = yaml.safe_load((RAIZ / "render.yaml").read_text(encoding="utf-8"))
    (servico,) = blueprint["services"]
    esperado = {
        "type": "web", "name": "sala-web-api", "runtime": "docker", "plan": "free", "region": "virginia",
        "branch": "main", "rootDir": "backend", "dockerfilePath": "./Dockerfile", "dockerContext": ".",
        "healthCheckPath": "/saude", "autoDeploy": True,
    }
    assert {k: servico.get(k) for k in esperado} == esperado
    assert (RAIZ / servico["rootDir"] / servico["dockerfilePath"]).is_file()
    variaveis = {v["key"]: v for v in servico["envVars"]}
    for segredo in ("DATABASE_URL", "CORS_ORIGENS", "ADMIN_RM", "ADMIN_SENHA"):
        assert variaveis[segredo] == {"key": segredo, "sync": False}, segredo
    assert variaveis["JWT_SECRET"] == {"key": "JWT_SECRET", "generateValue": True}
    fixos = {k: v["value"] for k, v in variaveis.items() if "value" in v}
    assert fixos == {
        "ADMIN_NOME": "Administrador", "TZ": "America/Sao_Paulo", "JWT_EXPIRA_MINUTOS": "480",
        "UPLOAD_MAX_MB": "5", "LOGIN_MAX_FALHAS_IP": "0",
    }
    assert "PORT" not in variaveis and "UPLOAD_DIR" not in variaveis
    # todos os nomes existem na configuração da API
    from app.core.config import Config

    assert set(variaveis) <= set(Config.model_fields)
