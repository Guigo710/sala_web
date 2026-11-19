from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Query, status

from app.core.seguranca import Db, UsuarioAtual, UsuarioOpcional
from app.schemas import reservas as sr
from app.services import apresentacao, recorrencia
from app.services import reservas as servico

router = APIRouter(prefix="/reservas", tags=["reservas"])

StatusFiltro = Literal["ativa", "cancelada", "todas"]


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
    lista = servico.agenda(db, mes, data, de, ate, sala_id, professor_id, status_)
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
    return apresentacao.grupo_com_reservas(grupo, reservas, usuario)


@router.get("/grupos/{grupo_id}", response_model=sr.GrupoComReservas)
def obter_grupo(grupo_id: int, db: Db, usuario: UsuarioAtual) -> sr.GrupoComReservas:
    grupo, reservas = servico.grupo_com_reservas(db, grupo_id, usuario)
    return apresentacao.grupo_com_reservas(grupo, reservas, usuario)


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
