'''from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from database import Base

sala_equipamento = Table(
    "sala_equipamento",
    Base.metadata,
    Column("sala_id", Integer, ForeignKey("salas.id"), primary_key=True),
    Column("equipamento_id", Integer, ForeignKey("equipamentos.id"), primary_key=True),
)


class Sala(Base):
    __tablename__ = "salas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    capacidade = Column(Integer, nullable=False)
    foto_url = Column(String, nullable=True)

    equipamentos = relationship("Equipamento", secondary=sala_equipamento, backref="salas")
    reservas = relationship("Reserva", back_populates="sala")'''