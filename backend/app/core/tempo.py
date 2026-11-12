"""Hora local de referência (America/Sao_Paulo, variável TZ). O banco guarda date + time sem fuso."""

from datetime import date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import obter_config_banco


@lru_cache
def fuso() -> ZoneInfo:
    return ZoneInfo(obter_config_banco().TZ)


def agora_tz() -> datetime:
    """Agora, com fuso."""
    return datetime.now(fuso())


def agora() -> datetime:
    """Agora em hora local, sem fuso (comparável a `datetime.combine(data, inicio)`)."""
    return agora_tz().replace(tzinfo=None)


def hoje() -> date:
    return agora().date()


def momento(data: date, hora: time) -> datetime:
    return datetime.combine(data, hora)
