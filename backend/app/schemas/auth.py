
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.comum import DataHora, Modelo


class LoginEntrada(BaseModel):
    rm: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=128)


class Usuario(Modelo):
    id: int
    rm: str
    nome: str
    email: str | None
    papel: Literal["professor", "admin"]
    ativo: bool
    criado_em: DataHora


class LoginSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em: DataHora
    usuario: Usuario


class TrocaSenhaEntrada(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)


