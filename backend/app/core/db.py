"""Engine, sessão e dependência `get_db`."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_config_banco

_config = obter_config_banco()

engine = create_engine(
    _config.DATABASE_URL,
    pool_pre_ping=True,
    # Sessão do Postgres no fuso local: timestamptz volta já em America/Sao_Paulo.
    connect_args={"options": f"-c timezone={_config.TZ}"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
