"""Ticket 63 (ADR-0009): pool de conexões e fuso adequados ao Neon (banco que suspende, SSL, sem `options`)."""

import logging
import os
import socket
import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

import app.main as modulo_main
from app.core.config import ConfigBanco
from app.core.db import criar_engine, engine


def _config_banco(**valores) -> ConfigBanco:
    return ConfigBanco(_env_file=None, **{"DATABASE_URL": os.environ["DATABASE_URL"], **valores})


def test_pool_com_os_padroes_do_ticket():
    pool = engine.pool
    assert pool.size() == 5
    assert pool._max_overflow == 5
    assert pool._recycle == 240
    assert pool._pre_ping is True
    assert pool._timeout == 30


def test_pool_configuravel_por_ambiente(monkeypatch):
    for nome, valor in (("DB_POOL_TAMANHO", "2"), ("DB_POOL_EXTRA", "0"), ("DB_POOL_RECICLAR_S", "60"), ("DB_CONEXAO_TIMEOUT_S", "3")):
        monkeypatch.setenv(nome, valor)
    config = ConfigBanco(_env_file=None)
    outro = criar_engine(config)
    try:
        assert (outro.pool.size(), outro.pool._max_overflow, outro.pool._recycle) == (2, 0, 60)
        assert config.DB_CONEXAO_TIMEOUT_S == 3
    finally:
        outro.dispose()
    monkeypatch.setenv("DB_POOL_TAMANHO", "0")
    with pytest.raises(ValueError):
        ConfigBanco(_env_file=None)


def test_sessao_no_fuso_por_set_time_zone_sem_options():
    assert "options" not in engine.url.query
    with engine.connect() as conn:
        assert conn.scalar(text("SHOW TimeZone")) == "America/Sao_Paulo"
        assert conn.scalar(text("SELECT current_setting('application_name')")) == "sala_web"
        # o SET vale para a sessão inteira (não ficou preso numa transação desfeita)
        conn.rollback()
        assert conn.scalar(text("SHOW TimeZone")) == "America/Sao_Paulo"
        assert conn.scalar(text("SELECT to_char(now(), 'TZH')")) == "-03"
        # a opção de inicialização não foi usada
        assert conn.scalar(text("SELECT setting FROM pg_settings WHERE name = 'TimeZone'")) == "America/Sao_Paulo"
        assert conn.scalar(text("SELECT source FROM pg_settings WHERE name = 'TimeZone'")) == "session"


def test_fuso_vem_de_tz_e_e_literal_seguro():
    outro = criar_engine(_config_banco(TZ="UTC"))
    try:
        with outro.connect() as conn:
            assert conn.scalar(text("SHOW TimeZone")) == "UTC"
    finally:
        outro.dispose()
    malicioso = criar_engine(_config_banco(TZ="UTC'; CREATE TABLE invasao (x int); --"))
    try:
        with pytest.raises(DBAPIError):
            with malicioso.connect():
                pass
    finally:
        malicioso.dispose()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT to_regclass('invasao')")) is None


def test_reconecta_depois_que_o_banco_derruba_as_conexoes(client, admin):
    """Simula o Neon suspendendo: o servidor encerra todas as conexões da API; a próxima requisição funciona."""
    assert client.get("/salas").status_code == 200
    assert client.get("/auth/me", headers=admin).status_code == 200
    assert engine.pool.checkedin() >= 1
    with engine.connect() as conn:
        meu_pid = conn.scalar(text("SELECT pg_backend_pid()"))
    outro = criar_engine(_config_banco())
    try:
        with outro.connect() as conn:
            derrubadas = conn.scalar(
                text(
                    "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity "
                    "WHERE application_name = 'sala_web' AND datname = current_database() AND pid <> pg_backend_pid()"
                )
            )
            conn.commit()
    finally:
        outro.dispose()
    assert derrubadas >= 1 and meu_pid is not None
    for _ in range(3):
        assert client.get("/salas").status_code == 200
        assert client.get("/auth/me", headers=admin).status_code == 200
        assert client.get("/saude").json() == {"status": "ok"}


@pytest.fixture
def banco_mudo():
    """Porta TCP que aceita a conexão e nunca responde (banco pendurado/acordando): só o timeout tira dali."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(16)
    try:
        yield servidor.getsockname()[1]
    finally:
        servidor.close()


def test_saude_503_rapido_com_banco_fora_do_ar_sem_vazar_senha(client, monkeypatch, caplog, banco_mudo):
    senha = "senha-super-secreta-123"
    config = _config_banco(
        DATABASE_URL=f"postgresql+psycopg://sala_web:{senha}@127.0.0.1:{banco_mudo}/sala_web?sslmode=prefer",
        DB_CONEXAO_TIMEOUT_S=2,
    )
    fora = criar_engine(config)
    monkeypatch.setattr(modulo_main, "SessionLocal", sessionmaker(bind=fora))
    caplog.set_level(logging.DEBUG)
    try:
        inicio = time.monotonic()
        r = client.get("/saude")
        decorrido = time.monotonic() - inicio
    finally:
        fora.dispose()
    assert (r.status_code, r.json()) == (503, {"status": "erro"})
    # esperou o connect_timeout (não ficou pendurado, nem falhou por outro motivo antes)
    assert config.DB_CONEXAO_TIMEOUT_S - 0.5 <= decorrido <= config.DB_CONEXAO_TIMEOUT_S + 1, decorrido
    assert "Banco indisponível em 127.0.0.1 (OperationalError)" in caplog.text
    assert senha not in caplog.text


def test_saude_503_com_conexao_recusada(client, monkeypatch, caplog):
    senha = "outra-senha-secreta-456"
    fora = criar_engine(_config_banco(DATABASE_URL=f"postgresql+psycopg://u:{senha}@127.0.0.1:1/x"))
    monkeypatch.setattr(modulo_main, "SessionLocal", sessionmaker(bind=fora))
    try:
        r = client.get("/saude")
    finally:
        fora.dispose()
    assert r.status_code == 503 and senha not in caplog.text


def test_ssl_require_na_url_chega_ao_driver():
    """`?sslmode=require` (Neon) é repassado ao psycopg. Se o Postgres local tiver SSL, a sessão fica cifrada."""
    url = os.environ["DATABASE_URL"]
    url_ssl = url + ("&" if "?" in url else "?") + "sslmode=require"
    ssl = criar_engine(_config_banco(DATABASE_URL=url_ssl))
    try:
        with ssl.connect() as conn:
            cifrada = conn.scalar(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"))
            assert cifrada is True
            assert conn.scalar(text("SHOW TimeZone")) == "America/Sao_Paulo"
    except DBAPIError as erro:
        if "SSL" in str(erro) and "not support" in str(erro):
            pytest.skip("Postgres local sem SSL")
        raise
    finally:
        ssl.dispose()
