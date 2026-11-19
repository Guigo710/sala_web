"""Engine, sessão e dependência `get_db`.

Pool ajustado para um banco que suspende e derruba conexões ociosas (Neon; ADR-0009, ticket 63), e que também
serve para o Postgres do Compose:
- `pool_pre_ping`: testa a conexão antes de usar (reconecta depois que o banco "acordou" ou reiniciou);
- `pool_recycle` (`DB_POOL_RECICLAR_S`, 240 s): descarta conexões antes dos ~5 min de suspensão do Neon;
- `connect_timeout` (`DB_CONEXAO_TIMEOUT_S`, 10 s): tolera o banco acordando sem ficar pendurado;
- SSL: vem da própria URL (`?sslmode=require&channel_binding=require`), repassada intacta ao psycopg.
O fuso da sessão é definido com `SET TIME ZONE` a cada conexão nova (funciona igual no Postgres local, no Neon
e atrás de pooler, que recusa o parâmetro de inicialização `options`).
"""

from collections.abc import Iterator

from psycopg import sql
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ConfigBanco, obter_config_banco

NOME_APLICACAO = "sala_web"


def instalar_fuso(engine: Engine, fuso: str) -> None:
    """`SET TIME ZONE` em toda conexão nova do engine: timestamptz volta já no fuso `TZ`."""

    @event.listens_for(engine, "connect")
    def _definir_fuso(conexao_dbapi, _registro) -> None:  # noqa: ANN001
        cursor = conexao_dbapi.cursor()
        try:
            # SET não aceita parâmetro: o valor de TZ entra como literal escapado pelo psycopg, nunca colado no SQL.
            cursor.execute(sql.SQL("SET TIME ZONE {}").format(sql.Literal(fuso)))
        finally:
            cursor.close()
        # psycopg 3 abre uma transação implícita; fecha para a conexão voltar limpa ao pool.
        conexao_dbapi.commit()


def criar_engine(config: ConfigBanco) -> Engine:
    engine = create_engine(
        config.DATABASE_URL,
        pool_size=config.DB_POOL_TAMANHO,
        max_overflow=config.DB_POOL_EXTRA,
        pool_recycle=config.DB_POOL_RECICLAR_S,
        pool_pre_ping=True,
        pool_timeout=30,
        connect_args={"connect_timeout": config.DB_CONEXAO_TIMEOUT_S, "application_name": NOME_APLICACAO},
        # Erros do banco no log sem os valores da consulta (hash de senha, textos digitados; ticket 68).
        hide_parameters=True,
    )
    instalar_fuso(engine, config.TZ)
    return engine


_config = obter_config_banco()
engine = criar_engine(_config)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
