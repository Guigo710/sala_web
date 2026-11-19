"""Models SQLAlchemy. Importar daqui garante que todas as tabelas estejam no metadata."""

from app.models.base import Base
from app.models.equipamento import Equipamento, SalaEquipamento
from app.models.foto import FotoSala
from app.models.horario_aula import ORDEM_TURNO, TURNOS, HorarioAula
from app.models.professor import PAPEIS, Professor
from app.models.reserva import STATUS_RESERVA, GrupoRecorrencia, Reserva
from app.models.sala import TIPOS_SALA, Sala
from app.models.semestre import Semestre
from app.models.software import Software, sala_softwares

__all__ = [
    "Base", "Equipamento", "SalaEquipamento", "FotoSala", "HorarioAula", "TURNOS", "ORDEM_TURNO",
    "Professor", "PAPEIS", "Reserva", "GrupoRecorrencia", "STATUS_RESERVA", "Sala", "TIPOS_SALA",
    "Semestre", "Software", "sala_softwares",
]
