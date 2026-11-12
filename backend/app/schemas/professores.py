from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, EmailStr, Field

from app.schemas.comum import _vazio_para_none, texto

EmailOpcional = Annotated[EmailStr | None, BeforeValidator(_vazio_para_none)]


class ProfessorCriar(BaseModel):
    rm: str = Field(pattern=r"^[A-Za-z0-9]{3,20}$")
    nome: texto(120)
    email: EmailOpcional = None
    senha: str = Field(min_length=8, max_length=128)
    papel: Literal["professor", "admin"] = "professor"


class ProfessorAtualizar(BaseModel):
    nome: texto(120)
    email: EmailOpcional = None
    papel: Literal["professor", "admin"]
    ativo: bool


class RedefinirSenhaEntrada(BaseModel):
    nova_senha: str = Field(min_length=8, max_length=128)
