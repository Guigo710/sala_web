import calendar
import re
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Query, status

from app.core.erros import ErroApi
from app.core.seguranca import Db, UsuarioAtual, UsuarioOpcional
from app.schemas import reservas as sr
from app.services import apresentacao, recorrencia
from app.services import reservas as servico

router = APIRouter(prefix="/reservas", tags=["reservas"])

MAX_DIAS_INTERVALO = 62
StatusFiltro = Literal["ativa", "cancelada", "todas"]


def _intervalo_invalido(detail: str) -> ErroApi:
    return ErroApi(422, "INTERVALO_INVALIDO", detail)


def resolver_intervalo(mes: str | None, data: date | None, de: date | None, ate: date | None) -> tuple[date, date]:
    """Exatamente um modo: mes | data | de+ate (≤ 62 dias, inclusivos)."""
    modos = sum([mes is not None, data is not None, de is not None or ate is not None])
    if modos != 1:
        raise _intervalo_invalido("Informe exatamente um período: mes, data ou de + ate.")
    if mes is not None:
        m = re.fullmatch(r"(\d{4})-(\d{2})", mes)
        if not m or not 1 <= int(m.group(2)) <= 12:
            raise _intervalo_invalido("Mês inválido; use AAAA-MM.")
        ano, num = int(m.group(1)), int(m.group(2))
        return date(ano, num, 1), date(ano, num, calendar.monthrange(ano, num)[1])
    if data is not None:
        return data, data
    if de is None or ate is None:
        raise _intervalo_invalido("Informe de e ate juntos.")
    if ate < de:
        raise _intervalo_invalido("A data final deve ser igual ou posterior à inicial.")
    if (ate - de).days + 1 > MAX_DIAS_INTERVALO:
        raise _intervalo_invalido(f"O período pode ter no máximo {MAX_DIAS_INTERVALO} dias.")
    return de, ate


@router.get("", response_model=list[sr.Reserva], summary="Agenda (período obrigatório)")
def agenda(
    db: Db,
    usuario: UsuarioOpcional,
    mes: str | None = None,
    data: date | None = None,
    de: date | None = None,
    ate: date | None = None,
    sala_id: Annotated[list[int] | None, Query()] = None,
    professor_id: int | None = None,
    status_: Annotated[StatusFiltro, Query(alias="status")] = "ativa",
) -> list[sr.Reserva]:
    inicio, fim = resolver_intervalo(mes, data, de, ate)
    lista = servico.listar_agenda(db, inicio, fim, sala_id, professor_id, status_)
    return apresentacao.reservas(lista, usuario)


@router.get("/minhas", response_model=list[sr.Reserva], summary="Minhas reservas")
def minhas(
    db: Db,
    usuario: UsuarioAtual,
    periodo: Literal["futuras", "passadas", "todas"] = "futuras",
    status_: Annotated[StatusFiltro, Query(alias="status")] = "ativa",
) -> list[sr.Reserva]:
    return apresentacao.reservas(servico.listar_minhas(db, usuario, periodo, status_), usuario)


@router.post("", response_model=sr.Reserva, status_code=status.HTTP_201_CREATED, summary="Reserva avulsa")
def criar(entrada: sr.ReservaEntrada, db: Db, usuario: UsuarioAtual) -> sr.Reserva:
    reserva = servico.criar_avulsa(
        db, usuario, entrada.sala_id, entrada.data, entrada.horario_ids, entrada.observacao, entrada.professor_id
    )
    return apresentacao.reserva(reserva, usuario)


@router.post("/recorrentes/previa", response_model=sr.PreviaSaida, summary="Prévia da recorrência (não grava)")
def previa(entrada: sr.PreviaEntrada, db: Db, usuario: UsuarioAtual) -> sr.PreviaSaida:
    return recorrencia.previa(db, usuario, entrada)


@router.post(
    "/recorrentes",
    response_model=sr.GrupoComReservas,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar reserva recorrente",
)
def confirmar(entrada: sr.RecorrenteEntrada, db: Db, usuario: UsuarioAtual) -> sr.GrupoComReservas:
    grupo, reservas = recorrencia.confirmar(db, usuario, entrada)
    return sr.GrupoComReservas(
        grupo=apresentacao.grupo(db, grupo), reservas=apresentacao.reservas(reservas, usuario)
    )


@router.get("/grupos/{grupo_id}", response_model=sr.GrupoComReservas)
def obter_grupo(grupo_id: int, db: Db, usuario: UsuarioAtual) -> sr.GrupoComReservas:
    grupo = servico.obter_grupo(db, grupo_id, usuario)
    return sr.GrupoComReservas(
        grupo=apresentacao.grupo(db, grupo),
        reservas=apresentacao.reservas(servico.reservas_do_grupo(db, grupo.id), usuario),
    )


@router.post("/grupos/{grupo_id}/cancelar", response_model=sr.CancelarGrupoSaida)
def cancelar_grupo(
    grupo_id: int,
    db: Db,
    usuario: UsuarioAtual,
    entrada: Annotated[sr.CancelarEntrada | None, Body()] = None,
) -> sr.CancelarGrupoSaida:
    ids = servico.cancelar_grupo(db, grupo_id, usuario, entrada.motivo if entrada else None)
    return sr.CancelarGrupoSaida(grupo_recorrencia_id=grupo_id, canceladas=len(ids), reservas_ids=ids)


@router.get("/{reserva_id}", response_model=sr.Reserva)
def obter(reserva_id: int, db: Db, usuario: UsuarioOpcional) -> sr.Reserva:
    return apresentacao.reserva(servico.obter(db, reserva_id), usuario)


@router.post("/{reserva_id}/cancelar", response_model=sr.Reserva)
def cancelar(
    reserva_id: int,
    db: Db,
    usuario: UsuarioAtual,
    entrada: Annotated[sr.CancelarEntrada | None, Body()] = None,
) -> sr.Reserva:
    reserva = servico.cancelar(db, reserva_id, usuario, entrada.motivo if entrada else None)
    return apresentacao.reserva(reserva, usuario)
