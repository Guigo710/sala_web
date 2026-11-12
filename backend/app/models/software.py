from sqlalchemy import Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

sala_softwares = Table(
    "sala_softwares",
    Base.metadata,
    Column("sala_id", ForeignKey("salas.id", ondelete="CASCADE"), primary_key=True),
    Column("software_id", ForeignKey("softwares.id", ondelete="CASCADE"), primary_key=True),
)


class Software(Base):
    __tablename__ = "softwares"
    __table_args__ = (
        UniqueConstraint("nome", "versao", name="uq_softwares_nome_versao", postgresql_nulls_not_distinct=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    versao: Mapped[str | None] = mapped_column(String(40))
    categoria: Mapped[str | None] = mapped_column(String(60))
