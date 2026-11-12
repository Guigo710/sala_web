from pydantic import BaseModel

from app.schemas.comum import Modelo, texto, texto_opcional


class SoftwareEntrada(BaseModel):
    nome: texto(80)
    versao: texto_opcional(40) = None
    categoria: texto_opcional(60) = None


class Software(Modelo):
    id: int
    nome: str
    versao: str | None
    categoria: str | None
