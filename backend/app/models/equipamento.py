from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Equipamento(Base):
    __tablename__ = "equipamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)


class SalaEquipamento(Base):
    """Associação sala–equipamento com quantidade e especificação."""

    __tablename__ = "sala_equipamentos"
    __table_args__ = (CheckConstraint("quantidade > 0", name="sala_equipamentos_quantidade_check"),)

    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id", ondelete="CASCADE"), primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(
        ForeignKey("equipamentos.id", ondelete="CASCADE"), primary_key=True
    )
    quantidade: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    especificacao: Mapped[str | None] = mapped_column(String(255))

    equipamento: Mapped[Equipamento] = relationship(lazy="joined")
    sala: Mapped["Sala"] = relationship(back_populates="equipamentos")  # noqa: F821
