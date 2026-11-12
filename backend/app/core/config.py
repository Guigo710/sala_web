"""Configuração lida só de variáveis de ambiente (modelo em `.env.example`)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
