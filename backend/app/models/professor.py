from datetime import datetime

from sqlalchemy import CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, coluna_atualizado_em, coluna_criado_em

PAPEIS = ("professor", "admin")


class Professor(Base):
    """Conta de usuário (professor ou admin)."""

    __tablename__ = "professores"
    __table_args__ = (CheckConstraint("papel IN ('professor', 'admin')", name="professores_papel_check"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rm: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(160))
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[str] = mapped_column(String(20), default="professor", server_default="professor")
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
    criado_em: Mapped[datetime] = coluna_criado_em()
    atualizado_em: Mapped[datetime] = coluna_atualizado_em()

    @property
    def eh_admin(self) -> bool:
        return self.papel == "admin"
