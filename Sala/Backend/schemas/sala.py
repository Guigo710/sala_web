'''from typing import Optional

from pydantic import BaseModel

from schemas.equipamento import EquipamentoResponse


class SalaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    capacidade: int
    foto_url: Optional[str] = None


class SalaCreate(SalaBase):
    equipamento_ids: list[int] = []


class SalaResponse(SalaBase):
    id: int
    equipamentos: list[EquipamentoResponse] = []

    class Config:
        from_attributes = True'''