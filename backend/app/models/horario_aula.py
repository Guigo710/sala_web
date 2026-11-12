from datetime import time

from sqlalchemy import CheckConstraint, SmallInteger, String, UniqueConstraint, true
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

TURNOS: dict[str, str] = {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}
ORDEM_TURNO = {"manha": 1, "tarde": 2, "noite": 3}


class HorarioAula(Base):
    """Aula (slot) da grade: turno + ordem + início/fim + dias da semana ISO (1=seg..7=dom)."""

    __tablename__ = "horarios_aula"
    __table_args__ = (
        CheckConstraint("turno IN ('manha','tarde','noite')", name="horarios_aula_turno_check"),
        CheckConstraint("ordem > 0", name="horarios_aula_ordem_check"),
        CheckConstraint("fim > inicio", name="ck_horarios_fim_maior"),
        CheckConstraint(
            "cardinality(dias_semana) > 0 AND dias_semana <@ ARRAY[1,2,3,4,5,6,7]::smallint[]",
            name="ck_horarios_dias",
        ),
        UniqueConstraint("turno", "ordem", name="uq_horarios_turno_ordem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turno: Mapped[str] = mapped_column(String(10))
    ordem: Mapped[int] = mapped_column(SmallInteger)
    inicio: Mapped[time]
    fim: Mapped[time]
    dias_semana: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
