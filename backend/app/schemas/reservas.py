from datetime import date

from pydantic import BaseModel

from app.schemas.comum import DataHora, Hora, HorarioAula, Modelo, PessoaResumo, SalaRef, Semestre, texto_opcional


class Reserva(Modelo):
    id: int
    sala: SalaRef
    professor: PessoaResumo
    data: date
    inicio: Hora
    fim: Hora
    horario_inicio_id: int
    horario_fim_id: int
    quantidade_aulas: int
    status: str
    observacao: str | None
    grupo_recorrencia_id: int | None
    criado_em: DataHora
    cancelada_em: DataHora | None
    cancelada_por: PessoaResumo | None
    motivo_cancelamento: str | None
    pode_cancelar: bool


class Conflito(BaseModel):
    data: date
    inicio: Hora
    fim: Hora
    reserva_id: int
    sala_id: int
    professor: PessoaResumo


class ReservaEntrada(BaseModel):
    sala_id: int
    data: date
    horario_ids: list[int]
    observacao: texto_opcional(200) = None
    professor_id: int | None = None


class PreviaEntrada(BaseModel):
    sala_id: int
    data_inicio: date
    horario_ids: list[int]
    professor_id: int | None = None


class RecorrenteEntrada(PreviaEntrada):
    datas: list[date]
    observacao: texto_opcional(200) = None


class OcorrenciaPrevia(BaseModel):
    data: date
    livre: bool
    conflitos: list[Conflito]


class PreviaSaida(BaseModel):
    sala: SalaRef
    semestre: Semestre
    dia_semana: int
    inicio: Hora
    fim: Hora
    horario_ids: list[int]
    ocorrencias: list[OcorrenciaPrevia]
    total: int
    livres: int
    em_conflito: int


class GrupoRecorrencia(BaseModel):
    id: int
    sala: SalaRef
    professor: PessoaResumo
    semestre: Semestre
    dia_semana: int
    inicio: Hora
    fim: Hora
    criado_em: DataHora
    total_ocorrencias: int
    ocorrencias_ativas: int


class GrupoComReservas(BaseModel):
    grupo: GrupoRecorrencia
    reservas: list[Reserva]


class CancelarEntrada(BaseModel):
    motivo: texto_opcional(200) = None


class CancelarGrupoSaida(BaseModel):
    grupo_recorrencia_id: int
    canceladas: int
    reservas_ids: list[int]


class ReservaNaAula(BaseModel):
    id: int
    professor: PessoaResumo
    inicio: Hora
    fim: Hora


class AulaDisponibilidade(BaseModel):
    horario: HorarioAula
    livre: bool
    passou: bool
    reserva: ReservaNaAula | None


class Disponibilidade(BaseModel):
    sala_id: int
    data: date
    dia_semana: int
    aulas: list[AulaDisponibilidade]


