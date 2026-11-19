"""Configuração lida só de variáveis de ambiente (modelo em `.env.example`)."""

import re
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


# Origem = esquema + host + porta opcional, sem caminho (contrato §1.5). Host: nome DNS, IPv4 ou [IPv6].
_ORIGEM = re.compile(r"^(https?)://([a-z0-9]([a-z0-9.-]*[a-z0-9])?|\[[0-9a-f:.]+\])(:([0-9]{1,5}))?$")
_PORTA_PADRAO = {"http": "80", "https": "443"}
_EXEMPLO_ORIGEM = "https://sala-web.vercel.app"


def normalizar_origens(texto: str) -> list[str]:
    """`CORS_ORIGENS` → lista de origens exatas (ADR-0009, ticket 62).

    Tira espaços e barra(s) final(is), ignora itens vazios, passa esquema e host para minúsculas (o navegador
    sempre manda assim no `Origin`) e tira a porta padrão (`:443` em https, `:80` em http). Recusa `*` e qualquer
    item que não seja `http(s)://host[:porta]` (com caminho, consulta, usuário...), com ValueError.
    """
    origens: list[str] = []
    for bruto in texto.split(","):
        item = bruto.strip().rstrip("/").strip()
        if not item:
            continue
        if "*" in item:
            raise ValueError(
                f"CORS_ORIGENS: '{item}' não é aceito (sem curingas). Liste as origens do site separadas por "
                f"vírgula, como {_EXEMPLO_ORIGEM}"
            )
        m = _ORIGEM.match(item.lower())
        if m is None or (m.group(5) is not None and not 0 < int(m.group(5)) < 65536):
            raise ValueError(f"CORS_ORIGENS: '{item}' não é uma origem; use algo como {_EXEMPLO_ORIGEM}")
        esquema, host, porta = m.group(1), m.group(2), m.group(5)
        origem = f"{esquema}://{host}" + (f":{porta}" if porta and porta != _PORTA_PADRAO[esquema] else "")
        if origem not in origens:
            origens.append(origem)
    return origens


class ConfigBanco(BaseSettings):
    """Só o necessário para conectar ao banco (usado também pelo Alembic)."""

    model_config = SettingsConfigDict(env_file=_ARQUIVOS_ENV, env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    TZ: str = "America/Sao_Paulo"
    # Pool de conexões (ADR-0009, ticket 63). O Neon suspende o banco após ~5 min sem uso e derruba as
    # conexões ociosas: reciclar antes disso, testar antes de usar e não ficar pendurado se ele não responder.
    DB_POOL_TAMANHO: int = Field(default=5, ge=1)
    DB_POOL_EXTRA: int = Field(default=5, ge=0)
    DB_POOL_RECICLAR_S: int = Field(default=240, ge=1)
    DB_CONEXAO_TIMEOUT_S: int = Field(default=10, ge=1)

    @property
    def host_banco(self) -> str:
        """Só o host da DATABASE_URL, para mensagens de erro (a URL tem a senha e nunca vai para o log)."""
        from sqlalchemy.engine import make_url

        try:
            return make_url(self.DATABASE_URL).host or "(local)"
        except Exception:  # noqa: BLE001
            return "(DATABASE_URL inválida)"


class Config(ConfigBanco):
    # HS256 pede chave de pelo menos 32 bytes (RFC 7518 §3.2); o PyJWT avisa abaixo disso.
    JWT_SECRET: str = Field(min_length=32)
    JWT_EXPIRA_MINUTOS: int = 480
    CORS_ORIGENS: str = "http://localhost:5173"
    # Pasta das fotos antigas, só para a importação (ADR-0010); a API não grava nada nela.
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_MB: int = 5
    # Teto de falhas de login por IP (ADR-0007, adendo 2). 0 desliga só o teto por IP (a contagem por
    # (IP, RM) continua). No Render fica 0: todos os clientes chegam com o IP do balanceador (ADR-0009).
    LOGIN_MAX_FALHAS_IP: int = Field(default=20, ge=0)

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

    @field_validator("CORS_ORIGENS")
    @classmethod
    def _origens_validas(cls, valor: str) -> str:
        return ",".join(normalizar_origens(valor))

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
        """Origens já normalizadas pelo validador (sem barra final; nunca `*`)."""
        return [o for o in self.CORS_ORIGENS.split(",") if o]

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
