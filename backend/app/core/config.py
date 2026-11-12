"""Configuração lida só de variáveis de ambiente (modelo em `.env.example`)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de exemplo do `.env.example`: públicos, nunca podem valer em execução (ticket 25/36).
JWT_SECRET_EXEMPLO = "troque-por-um-segredo-longo-e-aleatorio"
ADMIN_SENHA_EXEMPLO = "troque-esta-senha-admin"
DB_SENHA_EXEMPLO = "troque-esta-senha"

# Procura `.env` na pasta atual e na raiz do repositório (ao rodar de dentro de backend/).
_ARQUIVOS_ENV = (".env", "../.env")


class ConfigBanco(BaseSettings):
    """Só o necessário para conectar ao banco (usado também pelo Alembic)."""

    model_config = SettingsConfigDict(env_file=_ARQUIVOS_ENV, env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    TZ: str = "America/Sao_Paulo"


class Config(ConfigBanco):
    JWT_SECRET: str = Field(min_length=16)
    JWT_EXPIRA_MINUTOS: int = 480
    CORS_ORIGENS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_MB: int = 5

    # Admin inicial (seed). Opcionais: sem eles o seed não cria admin.
    ADMIN_RM: str | None = None
    ADMIN_SENHA: str | None = None
    ADMIN_NOME: str = "Administrador"

    @field_validator("JWT_SECRET")
    @classmethod
    def _segredo_nao_e_o_de_exemplo(cls, valor: str) -> str:
        if valor.strip() == JWT_SECRET_EXEMPLO:
            raise ValueError(
                "JWT_SECRET ainda é o valor de exemplo do .env.example. Gere um segredo com "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\" e coloque no .env."
            )
        return valor

    @property
    def banco_com_senha_de_exemplo(self) -> bool:
        """DATABASE_URL ainda com a senha do .env.example (ticket 43). Só gera aviso: recusar subir
        impediria quem já tem o volume pgdata criado com essa senha de abrir o sistema."""
        from sqlalchemy.engine import make_url

        try:
            return make_url(self.DATABASE_URL).password == DB_SENHA_EXEMPLO
        except Exception:  # noqa: BLE001
            return False

    @property
    def cors_origens(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGENS.split(",") if o.strip()]

    @property
    def upload_dir(self) -> Path:
        return Path(self.UPLOAD_DIR).resolve()

    @property
    def upload_max_bytes(self) -> int:
        return self.UPLOAD_MAX_MB * 1024 * 1024


@lru_cache
def obter_config() -> Config:
    return Config()  # type: ignore[call-arg]


@lru_cache
def obter_config_banco() -> ConfigBanco:
    return ConfigBanco()  # type: ignore[call-arg]
