from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, coluna_criado_em


class FotoSala(Base):
    __tablename__ = "fotos_sala"
    __table_args__ = (Index("ix_fotos_sala_sala_ordem", "sala_id", "ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id", ondelete="CASCADE"))
    arquivo: Mapped[str] = mapped_column(String(255), unique=True)  # relativo a UPLOAD_DIR
    legenda: Mapped[str | None] = mapped_column(String(200))
    ordem: Mapped[int] = mapped_column(default=0, server_default="0")
    criado_em: Mapped[datetime] = coluna_criado_em()

    sala: Mapped["Sala"] = relationship(back_populates="fotos")  # noqa: F821

    @property
    def url(self) -> str:
        return f"/uploads/{self.arquivo}"
