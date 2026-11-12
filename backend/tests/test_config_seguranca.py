"""Ticket 25: configuração segura por padrão (segredos de exemplo do .env.example não valem)."""

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import ADMIN_SENHA_EXEMPLO, JWT_SECRET_EXEMPLO, Config
from app.models import Professor


@pytest.mark.parametrize("segredo", [JWT_SECRET_EXEMPLO, f" {JWT_SECRET_EXEMPLO} ", "curto", ""])
def test_jwt_secret_de_exemplo_ou_curto_impede_a_api_de_subir(segredo):
    with pytest.raises(ValidationError) as erro:
        Config(JWT_SECRET=segredo)
    assert "JWT_SECRET" in str(erro.value)


def test_jwt_secret_proprio_e_aceito():
    assert Config(JWT_SECRET="um-segredo-de-verdade-1234567890").JWT_SECRET.startswith("um-segredo")


def test_seed_nao_cria_admin_com_senha_de_exemplo(db, monkeypatch, caplog):
    import app.seed as seed

    config = Config(JWT_SECRET="um-segredo-de-verdade-1234567890", ADMIN_RM="admin2", ADMIN_SENHA=ADMIN_SENHA_EXEMPLO)
    monkeypatch.setattr(seed, "obter_config", lambda: config)
    monkeypatch.setattr(seed.log, "disabled", False)  # o fileConfig do Alembic desliga loggers existentes
    seed.seed_admin(db)
    db.commit()
    assert db.scalar(select(Professor).where(Professor.rm == "admin2")) is None
    assert "ADMIN_SENHA ainda é o valor de exemplo" in caplog.text
