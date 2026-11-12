"""Tipos e objetos JSON compartilhados (contrato §1.2, §3)."""

from datetime import date, datetime, time
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, PlainSerializer, StringConstraints

from app.core.tempo import fuso


def _fmt_data_hora(v: datetime) -> str:
    if v.tzinfo is None:
        v = v.replace(tzinfo=fuso())
    return v.astimezone(fuso()).isoformat(timespec="seconds")


def _fmt_hora(v: time) -> str:
    return v.strftime("%H:%M")


def _hora_sem_segundos(v: time) -> time:
    return v.replace(second=0, microsecond=0, tzinfo=None)


def _vazio_para_none(v: Any) -> Any:
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


# Saída
DataHora = Annotated[datetime, PlainSerializer(_fmt_data_hora, return_type=str)]
Hora = Annotated[time, PlainSerializer(_fmt_hora, return_type=str)]
# Entrada: aceita HH:MM ou HH:MM:SS (segundos descartados); sai sempre HH:MM.
HoraEntrada = Annotated[time, AfterValidator(_hora_sem_segundos), PlainSerializer(_fmt_hora, return_type=str)]


def texto(max_len: int, min_len: int = 1) -> Any:
    """Texto obrigatório, sem espaços nas pontas."""
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_len, max_length=max_len)]


def texto_opcional(max_len: int | None = None) -> Any:
    """Texto opcional: vazio vira null."""
    return Annotated[
        Annotated[str, StringConstraints(max_length=max_len)] | None, BeforeValidator(_vazio_para_none)
    ]


class Modelo(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PessoaResumo(Modelo):
    id: int
    nome: str


class SalaRef(Modelo):
    id: int
    nome: str
    tipo: str


class Semestre(Modelo):
    id: int
    nome: str
    data_inicio: date
    data_fim: date


class HorarioAula(Modelo):
    id: int
    turno: str
    ordem: int
    inicio: Hora
    fim: Hora
    dias_semana: list[int]
    ativo: bool


class Erro(BaseModel):
    """Envelope de erro (documentação)."""

    detail: str
    codigo: str
