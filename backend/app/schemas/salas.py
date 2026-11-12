from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.comum import DataHora, Modelo, texto, texto_opcional
from app.schemas.softwares import Software

TipoSala = Literal["sala", "lab_informatica", "lab_ciencias", "lab_outro", "auditorio", "outro"]


class TipoSalaSaida(BaseModel):
    valor: str
    rotulo: str


class SalaEntrada(BaseModel):
    nome: texto(80)
    tipo: TipoSala
    descricao: texto_opcional() = None
    capacidade: int = Field(gt=0, le=2_147_483_647)
    localizacao: texto_opcional(120) = None
    ativo: bool = True


class SalaEquipamento(BaseModel):
    equipamento_id: int
    nome: str
    quantidade: int
    especificacao: str | None


class SalaEquipamentoEntrada(BaseModel):
    equipamento_id: int
    quantidade: int = Field(default=1, ge=1, le=2_147_483_647)
    especificacao: texto_opcional(255) = None


class SalaSoftwaresEntrada(BaseModel):
    software_ids: list[int]


class Foto(Modelo):
    id: int
    sala_id: int
    url: str
    legenda: str | None
    ordem: int
    criado_em: DataHora


class SalaResumo(BaseModel):
    id: int
    nome: str
    tipo: str
    tipo_rotulo: str
    capacidade: int
    localizacao: str | None
    ativo: bool
    foto_capa_url: str | None
    equipamentos: list[SalaEquipamento]


class SalaDetalhe(SalaResumo):
    descricao: str | None
    fotos: list[Foto]
    softwares: list[Software]
    criado_em: DataHora
    atualizado_em: DataHora


class FotoLegendaEntrada(BaseModel):
    legenda: texto_opcional(200) = None


class FotoOrdemEntrada(BaseModel):
    foto_ids: list[int]
