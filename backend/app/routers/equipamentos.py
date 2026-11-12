from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, nao_encontrado
from app.core.seguranca import Admin, Db
from app.models import Equipamento
from app.schemas.equipamentos import Equipamento as EquipamentoSaida
from app.schemas.equipamentos import EquipamentoEntrada
from app.services.salas import escapar_like

router = APIRouter(prefix="/equipamentos", tags=["equipamentos"])

_DUPLICADO = "Já existe um equipamento com este nome."


def _obter(db: Db, equipamento_id: int) -> Equipamento:
    eq = db.get(Equipamento, equipamento_id)
    if eq is None:
        raise nao_encontrado("Equipamento não encontrado.")
    return eq


def _checar_nome(db: Db, nome: str, ignorar_id: int | None = None) -> None:
    stmt = select(Equipamento.id).where(Equipamento.nome == nome)
    if ignorar_id is not None:
        stmt = stmt.where(Equipamento.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise ErroApi(409, "NOME_DUPLICADO", _DUPLICADO)


def _salvar(db: Db, eq: Equipamento) -> Equipamento:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroApi(409, "NOME_DUPLICADO", _DUPLICADO) from None
    db.refresh(eq)
    return eq


@router.get("", response_model=list[EquipamentoSaida])
def listar(db: Db, busca: str | None = None) -> list[Equipamento]:
    stmt = select(Equipamento)
    if busca and busca.strip():
        stmt = stmt.where(Equipamento.nome.ilike(f"%{escapar_like(busca.strip())}%", escape="\\"))
    return list(db.scalars(stmt.order_by(func.lower(Equipamento.nome), Equipamento.id)))


@router.get("/{equipamento_id}", response_model=EquipamentoSaida)
def obter(equipamento_id: int, db: Db) -> Equipamento:
    return _obter(db, equipamento_id)


@router.post("", response_model=EquipamentoSaida, status_code=status.HTTP_201_CREATED)
def criar(entrada: EquipamentoEntrada, db: Db, _: Admin) -> Equipamento:
    _checar_nome(db, entrada.nome)
    eq = Equipamento(**entrada.model_dump())
    db.add(eq)
    return _salvar(db, eq)


@router.put("/{equipamento_id}", response_model=EquipamentoSaida)
def atualizar(equipamento_id: int, entrada: EquipamentoEntrada, db: Db, _: Admin) -> Equipamento:
    eq = _obter(db, equipamento_id)
    _checar_nome(db, entrada.nome, ignorar_id=eq.id)
    eq.nome, eq.descricao = entrada.nome, entrada.descricao
    return _salvar(db, eq)


@router.delete("/{equipamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(equipamento_id: int, db: Db, _: Admin) -> None:
    db.delete(_obter(db, equipamento_id))  # associações caem por ON DELETE CASCADE
    db.commit()
