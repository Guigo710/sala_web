"""Ticket 33: routers finos, helpers únicos e tradução de IntegrityError por nome de constraint."""

import ast
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi
from app.main import app
from app.models import Sala
from app.schemas import salas as ss
from app.services.comum import commit_traduzindo, escapar_like, obter_ou_404

PASTA_APP = Path(__file__).resolve().parents[1] / "app"
ROUTERS = sorted((PASTA_APP / "routers").glob("*.py"))


@pytest.mark.parametrize("arquivo", ROUTERS, ids=[r.name for r in ROUTERS])
def test_router_sem_consulta_nem_transacao(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    assert not re.search(r"db\.(commit|execute|scalar|scalars|add|delete)|select\(", texto)
    for no in ast.walk(ast.parse(texto)):
        if isinstance(no, ast.ImportFrom) and no.module:
            assert not no.module.startswith("sqlalchemy"), no.module
            assert not no.module.startswith("app.routers"), no.module
        if isinstance(no, ast.Import):
            assert not any(a.name.startswith(("sqlalchemy", "app.routers")) for a in no.names)


def test_helpers_definidos_uma_vez_so():
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in PASTA_APP.rglob("*.py"))
    for nome in ("obter_ou_404", "commit_traduzindo", "escapar_like"):
        assert len(re.findall(rf"^def {nome}\(", codigo, flags=re.M)) == 1, nome
    assert not re.search(r"^def _obter\(", codigo, flags=re.M)  # as sete cópias de _obter viraram obter_ou_404


def test_escapar_like():
    assert escapar_like("50%_a\\b") == "50\\%\\_a\\\\b"


def test_obter_ou_404(db):
    assert obter_ou_404(db, Sala, 1, "x").id == 1
    with pytest.raises(ErroApi) as erro:
        obter_ou_404(db, Sala, 999999, "Ambiente não encontrado.")
    assert (erro.value.status, erro.value.codigo, erro.value.detail) == (404, "NAO_ENCONTRADO", "Ambiente não encontrado.")


def test_commit_traduzindo_constraint_conhecida(db):
    db.add(Sala(nome="Sala 01", tipo="sala", capacidade=10))
    with pytest.raises(ErroApi) as erro:
        commit_traduzindo(db, {"salas_nome_key": ErroApi(409, "NOME_DUPLICADO", "dup")})
    assert erro.value.codigo == "NOME_DUPLICADO"
    assert db.query(Sala).filter(Sala.nome == "Sala 01").count() == 1  # rollback feito, sessão utilizável


def test_commit_traduzindo_constraint_desconhecida_relanca(db):
    db.add(Sala(nome="Sala CHECK", tipo="sala", capacidade=0))  # viola salas_capacidade_check
    with pytest.raises(IntegrityError):
        commit_traduzindo(db, {"salas_nome_key": ErroApi(409, "NOME_DUPLICADO", "dup")})
    assert db.query(Sala).count() == 27


def test_violacao_de_check_nao_mapeada_vira_500(monkeypatch, admin):
    """Antes, qualquer IntegrityError virava 409 NOME_DUPLICADO; agora constraint inesperada → 500 com log."""
    original = ss.SalaEntrada.model_dump

    def com_capacidade_invalida(self, *a, **k):
        return original(self, *a, **k) | {"capacidade": 0}

    monkeypatch.setattr(ss.SalaEntrada, "model_dump", com_capacidade_invalida)
    with TestClient(app) as c:
        r = c.post("/salas", headers=admin, json={"nome": "Sala Check", "tipo": "sala", "capacidade": 10})
    assert r.status_code == 500
    assert r.json() == {"detail": "Erro interno no servidor. Tente novamente.", "codigo": "ERRO_INTERNO"}


def test_corrida_no_nome_ainda_vira_409(monkeypatch, client, admin):
    """Sem a pré-checagem (corrida), a constraint do banco continua dando a mensagem certa."""
    from app.services import salas as servico

    monkeypatch.setattr(servico, "_checar_nome", lambda *a, **k: None)
    r = client.post("/salas", headers=admin, json={"nome": "Sala 01", "tipo": "sala", "capacidade": 10})
    assert (r.status_code, r.json()) == (409, {"detail": "Já existe um ambiente com este nome.", "codigo": "NOME_DUPLICADO"})


def test_apresentacao_so_converte_sem_consultar_o_banco():
    """A conversão para o contrato recebe os dados prontos do service; quem consulta é o service."""
    texto = (PASTA_APP / "services" / "apresentacao.py").read_text(encoding="utf-8")
    assert "sqlalchemy" not in texto and not re.search(r"\bdb\b", texto)
