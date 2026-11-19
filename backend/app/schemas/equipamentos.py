from pydantic import BaseModel

from app.schemas.comum import Modelo, texto, texto_opcional


class EquipamentoEntrada(BaseModel):
    nome: texto(80)
    descricao: texto_opcional() = None


class Equipamento(Modelo):
    id: int
    nome: str
    descricao: str | None
