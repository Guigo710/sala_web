from datetime import datetime

from sqlalchemy import CheckConstraint, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, coluna_atualizado_em, coluna_criado_em
from app.models.equipamento import SalaEquipamento
from app.models.foto import FotoSala
from app.models.software import Software, sala_softwares

# Enum fixo (contrato §2.3): valor -> rótulo
TIPOS_SALA: dict[str, str] = {
    "sala": "Sala de aula",
    "lab_informatica": "Laboratório de informática",
    "lab_ciencias": "Laboratório de ciências",
    "lab_outro": "Outro laboratório",
    "auditorio": "Auditório",
    "outro": "Outro",
}


class Sala(Base):
    """Ambiente reservável (sala de aula, laboratório, auditório...)."""

    __tablename__ = "salas"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('sala','lab_informatica','lab_ciencias','lab_outro','auditorio','outro')",
            name="salas_tipo_check",
        ),
        CheckConstraint("capacidade > 0", name="salas_capacidade_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    tipo: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str | None] = mapped_column(Text)
    capacidade: Mapped[int]
    localizacao: Mapped[str | None] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
    criado_em: Mapped[datetime] = coluna_criado_em()
    atualizado_em: Mapped[datetime] = coluna_atualizado_em()

    equipamentos: Mapped[list[SalaEquipamento]] = relationship(
        back_populates="sala", cascade="all, delete-orphan", passive_deletes=True
    )
    softwares: Mapped[list[Software]] = relationship(secondary=sala_softwares, passive_deletes=True)
    fotos: Mapped[list[FotoSala]] = relationship(
        back_populates="sala", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def tipo_rotulo(self) -> str:
        return TIPOS_SALA.get(self.tipo, self.tipo)
