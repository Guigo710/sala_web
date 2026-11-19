from fastapi import APIRouter, status

from app.core.seguranca import Admin, Db
from app.schemas.equipamentos import Equipamento as EquipamentoSaida
from app.schemas.equipamentos import EquipamentoEntrada
from app.services import equipamentos as servico

router = APIRouter(prefix="/equipamentos", tags=["equipamentos"])


@router.get("", response_model=list[EquipamentoSaida])
def listar(db: Db, busca: str | None = None) -> list[EquipamentoSaida]:
    return [EquipamentoSaida.model_validate(e) for e in servico.listar(db, busca)]


@router.get("/{equipamento_id}", response_model=EquipamentoSaida)
def obter(equipamento_id: int, db: Db) -> EquipamentoSaida:
    return EquipamentoSaida.model_validate(servico.obter(db, equipamento_id))


@router.post("", response_model=EquipamentoSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: EquipamentoEntrada, db: Db, _: Admin) -> EquipamentoSaida:
    return EquipamentoSaida.model_validate(servico.criar(db, entrada))


@router.put("/{equipamento_id}", response_model=EquipamentoSaida)
def atualizar(equipamento_id: int, entrada: EquipamentoEntrada, db: Db, _: Admin) -> EquipamentoSaida:
    return EquipamentoSaida.model_validate(servico.atualizar(db, equipamento_id, entrada))


@router.delete("/{equipamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(equipamento_id: int, db: Db, _: Admin) -> None:
    servico.excluir(db, equipamento_id)
