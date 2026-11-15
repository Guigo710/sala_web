from typing import Literal

from fastapi import APIRouter, Query, status

from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.schemas.comum import HorarioAula as HorarioSaida
from app.schemas.horarios import HorarioAtualizar, HorarioEntrada
from app.services import horarios as servico

router = APIRouter(prefix="/horarios", tags=["horários"])


@router.get("", response_model=list[HorarioSaida])
def listar(
    db: Db,
    usuario: UsuarioOpcional,
    dia_semana: int | None = Query(None, ge=1, le=7),
    turno: Literal["manha", "tarde", "noite"] | None = None,
    incluir_inativos: bool = False,
) -> list[HorarioSaida]:
    aulas = servico.listar(db, usuario, dia_semana=dia_semana, turno=turno, incluir_inativos=incluir_inativos)
    return [HorarioSaida.model_validate(h) for h in aulas]


@router.get("/{horario_id}", response_model=HorarioSaida)
def obter(horario_id: int, db: Db) -> HorarioSaida:
    return HorarioSaida.model_validate(servico.obter(db, horario_id))


@router.post("", response_model=HorarioSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: HorarioEntrada, db: Db, _: Admin) -> HorarioSaida:
    return HorarioSaida.model_validate(servico.criar(db, entrada))


@router.put("/{horario_id}", response_model=HorarioSaida)
def atualizar(horario_id: int, entrada: HorarioAtualizar, db: Db, _: Admin) -> HorarioSaida:
    return HorarioSaida.model_validate(servico.atualizar(db, horario_id, entrada))


@router.delete("/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(horario_id: int, db: Db, _: Admin) -> None:
    servico.excluir(db, horario_id)
