from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import obter_config_banco
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL vem do ambiente (DATABASE_URL), a menos que já tenha sido definida (ex.: testes).
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", obter_config_banco().DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def _timeout_conexao() -> int:
    try:
        return obter_config_banco().DB_CONEXAO_TIMEOUT_S
    except Exception:  # noqa: BLE001  (sem DATABASE_URL no ambiente, ex.: URL definida pelos testes)
        return 10


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # NullPool: uma conexão só, fechada ao terminar. SSL (`?sslmode=require`, Neon) vem da própria URL.
    # Timeout de conexão como o da API (ticket 63): banco suspenso acorda; banco fora do ar não pendura o deploy.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": _timeout_conexao(), "application_name": "sala_web-alembic"},
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
