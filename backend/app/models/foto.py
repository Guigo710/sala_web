from datetime import datetime

from sqlalchemy import ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, coluna_criado_em


class FotoSala(Base):
    __tablename__ = "fotos_sala"
    __table_args__ = (Index("ix_fotos_sala_sala_ordem", "sala_id", "ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id", ondelete="CASCADE"))
    # Nome público da foto: "salas/{sala_id}/{uuid4}.jpg" (url = "/uploads/" + arquivo). ADR-0010.
    arquivo: Mapped[str] = mapped_column(String(255), unique=True)
    # Bytes do JPEG reduzido. Carregado só sob demanda (listas, detalhe, capa e galeria nunca os leem);
    # acesso sem `undefer` levanta erro em vez de fazer uma consulta escondida. Nulo só em foto antiga cujo
    # arquivo não foi achado na importação.
    conteudo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True, deferred_raiseload=True)
    tipo_mime: Mapped[str | None] = mapped_column(String(30))
    tamanho: Mapped[int | None]
    legenda: Mapped[str | None] = mapped_column(String(200))
    ordem: Mapped[int] = mapped_column(default=0, server_default="0")
    criado_em: Mapped[datetime] = coluna_criado_em()

    sala: Mapped["Sala"] = relationship(back_populates="fotos")  # noqa: F821

    @property
    def url(self) -> str:
        return f"/uploads/{self.arquivo}"
