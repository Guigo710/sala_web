from datetime import date, datetime, time
from typing import Any

from sqlalchemy import CheckConstraint, Computed, DateTime, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import TSRANGE, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, coluna_criado_em
from app.models.horario_aula import HorarioAula
from app.models.professor import Professor
from app.models.sala import Sala
from app.models.semestre import Semestre

STATUS_RESERVA = ("ativa", "cancelada")


class GrupoRecorrencia(Base):
    """Une as ocorrências de uma reserva semanal recorrente."""

    __tablename__ = "grupos_recorrencia"
    __table_args__ = (CheckConstraint("dia_semana BETWEEN 1 AND 7", name="grupos_recorrencia_dia_semana_check"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id", ondelete="RESTRICT"))
    professor_id: Mapped[int] = mapped_column(ForeignKey("professores.id", ondelete="RESTRICT"))
    semestre_id: Mapped[int] = mapped_column(ForeignKey("semestres.id", ondelete="RESTRICT"))
    dia_semana: Mapped[int] = mapped_column(SmallInteger)
    inicio: Mapped[time]
    fim: Mapped[time]
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("professores.id", ondelete="RESTRICT"))
    criado_em: Mapped[datetime] = coluna_criado_em()

    sala: Mapped[Sala] = relationship(lazy="joined")
    professor: Mapped[Professor] = relationship(foreign_keys=[professor_id], lazy="joined")
    semestre: Mapped[Semestre] = relationship(lazy="joined")


class Reserva(Base):
    """Bloco de aulas seguidas de um ambiente numa data (ADR-0002)."""

    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint("fim > inicio", name="ck_reservas_fim_maior"),
        CheckConstraint("quantidade_aulas > 0", name="reservas_quantidade_aulas_check"),
        CheckConstraint("status IN ('ativa','cancelada')", name="reservas_status_check"),
        CheckConstraint(
            "(status = 'ativa' AND cancelada_em IS NULL AND cancelada_por_id IS NULL) "
            "OR (status = 'cancelada' AND cancelada_em IS NOT NULL AND cancelada_por_id IS NOT NULL)",
            name="ck_reservas_cancelamento",
        ),
        # Garantia anti-conflito (ADR-0003)
        ExcludeConstraint(
            ("sala_id", "="),
            ("periodo", "&&"),
            name="ex_reservas_sem_sobreposicao",
            using="gist",
            where=text("status = 'ativa'"),
        ),
        Index("ix_reservas_data", "data"),
        Index("ix_reservas_professor_data", "professor_id", "data"),
        Index("ix_reservas_grupo", "grupo_recorrencia_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id", ondelete="RESTRICT"))
    professor_id: Mapped[int] = mapped_column(ForeignKey("professores.id", ondelete="RESTRICT"))
    data: Mapped[date]
    inicio: Mapped[time]
    fim: Mapped[time]
    # Coluna gerada: nunca escrever pelo ORM.
    periodo: Mapped[Any] = mapped_column(
        TSRANGE,
        Computed("tsrange(data + inicio, data + fim, '[)')", persisted=True),
        nullable=True,
        deferred=True,
    )
    horario_inicio_id: Mapped[int] = mapped_column(ForeignKey("horarios_aula.id", ondelete="RESTRICT"))
    horario_fim_id: Mapped[int] = mapped_column(ForeignKey("horarios_aula.id", ondelete="RESTRICT"))
    quantidade_aulas: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(12), default="ativa", server_default="ativa")
    observacao: Mapped[str | None] = mapped_column(String(200))
    grupo_recorrencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("grupos_recorrencia.id", ondelete="RESTRICT")
    )
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("professores.id", ondelete="RESTRICT"))
    criado_em: Mapped[datetime] = coluna_criado_em()
    cancelada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelada_por_id: Mapped[int | None] = mapped_column(ForeignKey("professores.id", ondelete="RESTRICT"))
    motivo_cancelamento: Mapped[str | None] = mapped_column(String(200))

    sala: Mapped[Sala] = relationship(lazy="joined")
    professor: Mapped[Professor] = relationship(foreign_keys=[professor_id], lazy="joined")
    cancelada_por: Mapped[Professor | None] = relationship(foreign_keys=[cancelada_por_id], lazy="joined")
    horario_inicio: Mapped[HorarioAula] = relationship(foreign_keys=[horario_inicio_id])
    horario_fim: Mapped[HorarioAula] = relationship(foreign_keys=[horario_fim_id])
