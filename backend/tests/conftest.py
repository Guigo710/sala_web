"""Fixtures de teste: banco Postgres real separado (ADR-0001/0003).

Banco de teste: DATABASE_URL_TESTE, ou DATABASE_URL com o nome do banco + "_teste".
O esquema é recriado com Alembic no início da sessão e as tabelas são truncadas a cada teste.
"""

import os
import tempfile
from datetime import date, timedelta

# --- ambiente ANTES de importar a aplicação -------------------------------------------
if "DATABASE_URL_TESTE" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_TESTE"]
else:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class _Url(BaseSettings):
        model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")
        DATABASE_URL: str = "postgresql+psycopg://sala_web:sala_web@localhost:5432/sala_web"

    base, _, nome = _Url().DATABASE_URL.rpartition("/")
    nome = nome.split("?")[0]
    os.environ["DATABASE_URL"] = f"{base}/{nome if nome.endswith('_teste') else nome + '_teste'}"

os.environ.setdefault("JWT_SECRET", "segredo-de-teste-com-tamanho-suficiente")
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="sala_web_uploads_")
os.environ["ADMIN_RM"] = "admin"
os.environ["ADMIN_SENHA"] = "senhaAdmin123"
os.environ["ADMIN_NOME"] = "Administrador"
os.environ.setdefault("TZ", "America/Sao_Paulo")

import pytest  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.seguranca import limite_login  # noqa: E402
from app.core.tempo import hoje  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import executar as executar_seed  # noqa: E402

PASTA_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def esquema():
    cfg = AlembicConfig(os.path.join(PASTA_BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(PASTA_BACKEND, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"].replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def banco_limpo(esquema):
    with engine.begin() as conn:
        tabelas = conn.scalars(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        ).all()
        conn.execute(text(f"TRUNCATE {', '.join(tabelas)} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        executar_seed(db)
    limite_login.limpar()
    yield


@pytest.fixture
def db():
    with SessionLocal() as sessao:
        yield sessao


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _token(client: TestClient, rm: str, senha: str) -> dict[str, str]:
    r = client.post("/auth/login", json={"rm": rm, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return _token(client, "admin", "senhaAdmin123")


@pytest.fixture
def professor(client, admin):
    r = client.post(
        "/professores",
        headers=admin,
        json={"rm": "prof01", "nome": "Professor Um", "senha": "senhaProf1", "papel": "professor"},
    )
    assert r.status_code == 201, r.text
    return _token(client, "prof01", "senhaProf1")


def proximo_dia_semana(iso: int, semanas_a_frente: int = 1) -> date:
    """Próxima data com o dia da semana ISO pedido, pelo menos 1 dia no futuro."""
    d = hoje() + timedelta(days=1)
    while d.isoweekday() != iso:
        d += timedelta(days=1)
    return d + timedelta(weeks=semanas_a_frente - 1)


@pytest.fixture
def aulas_manha(client):
    """Ids das aulas da manhã na ordem (1ª, 2ª, ...)."""
    return [h["id"] for h in client.get("/horarios", params={"turno": "manha"}).json()]


@pytest.fixture
def sala_id(client):
    return client.get("/salas", params={"busca": "Laboratório 01"}).json()[0]["id"]


# ---------------------------------------------------------------- apoio da suíte do Sentinela
from datetime import datetime  # noqa: E402

import app.core.tempo as _tempo  # noqa: E402


class Relogio:
    """"Agora" controlado: `app.core.tempo.agora_tz` passa a devolver o instante definido.

    `agora()`/`hoje()` (usados por services, rotas e regras de cancelamento) derivam dele.
    A emissão/validação de JWT continua no relógio real, então tokens não expiram por causa do teste.
    """

    def __init__(self) -> None:
        self.instante: datetime | None = None

    def definir(self, data: date, hora: str = "10:00") -> None:
        h, m = (int(x) for x in hora.split(":"))
        self.instante = datetime(data.year, data.month, data.day, h, m, tzinfo=_tempo.fuso())

    def __call__(self) -> datetime:
        assert self.instante is not None, "use relogio.definir(...) antes"
        return self.instante


# Data de referência dos testes com tempo controlado: terça-feira, dentro do semestre "2030-1".
TERCA_REF = date(2030, 3, 5)
SEMESTRE_REF = {"nome": "2030-1", "data_inicio": "2030-02-04", "data_fim": "2030-06-25"}  # 25/06/2030 é terça


@pytest.fixture
def relogio(monkeypatch):
    r = Relogio()
    r.definir(TERCA_REF, "06:00")
    monkeypatch.setattr(_tempo, "agora_tz", r)
    return r


@pytest.fixture
def semestre_ref(client, admin):
    r = client.post("/semestres", headers=admin, json=SEMESTRE_REF)
    assert r.status_code == 201, r.text
    return r.json()


def token_de(client: TestClient, rm: str, senha: str) -> dict[str, str]:
    return _token(client, rm, senha)


@pytest.fixture
def novo_professor(client, admin):
    """Fábrica: cria um professor (via API) e devolve (headers, usuario)."""

    def _criar(rm: str, nome: str | None = None, senha: str = "senhaProf1", papel: str = "professor"):
        r = client.post(
            "/professores", headers=admin, json={"rm": rm, "nome": nome or f"Prof {rm}", "senha": senha, "papel": papel}
        )
        assert r.status_code == 201, r.text
        return _token(client, rm, senha), r.json()

    return _criar


@pytest.fixture
def aulas(client):
    """{'manha': [ids por ordem], 'tarde': [...], 'noite': [...]}"""
    return {t: [h["id"] for h in client.get("/horarios", params={"turno": t}).json()] for t in ("manha", "tarde", "noite")}
