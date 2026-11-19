from datetime import date

from sqlalchemy import CheckConstraint, String, func, literal
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Semestre(Base):
    """Período letivo; limita a recorrência semanal."""

    __tablename__ = "semestres"
    __table_args__ = (CheckConstraint("data_fim > data_inicio", name="ck_semestres_datas"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    data_inicio: Mapped[date]
    data_fim: Mapped[date]


Semestre.__table__.append_constraint(  # type: ignore[attr-defined]
    ExcludeConstraint(
        (func.daterange(Semestre.data_inicio, Semestre.data_fim, literal("[]")), "&&"),
        name="ex_semestres_sem_sobreposicao",
        using="gist",
    )
)
