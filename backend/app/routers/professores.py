from typing import Literal

from fastapi import APIRouter, status

from app.core.seguranca import Admin, Db
from app.schemas.auth import Usuario
from app.schemas.professores import ProfessorAtualizar, ProfessorCriar, RedefinirSenhaEntrada
from app.services import professores as servico

router = APIRouter(prefix="/professores", tags=["professores"])


@router.get("", response_model=list[Usuario])
def listar(
    db: Db,
    _: Admin,
    busca: str | None = None,
    papel: Literal["professor", "admin"] | None = None,
    ativo: bool | None = None,
) -> list[Usuario]:
    return [Usuario.model_validate(p) for p in servico.listar(db, busca, papel, ativo)]


@router.get("/{professor_id}", response_model=Usuario)
def obter(professor_id: int, db: Db, _: Admin) -> Usuario:
    return Usuario.model_validate(servico.obter(db, professor_id))


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def criar(entrada: ProfessorCriar, db: Db, _: Admin) -> Usuario:
    return Usuario.model_validate(servico.criar(db, entrada))


@router.put("/{professor_id}", response_model=Usuario)
def atualizar(professor_id: int, entrada: ProfessorAtualizar, db: Db, admin: Admin) -> Usuario:
    return Usuario.model_validate(servico.atualizar(db, professor_id, entrada, admin))


@router.put(
    "/{professor_id}/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Redefine a senha e encerra todas as sessões da conta (ADR-0008), inclusive a do próprio admin.",
)
def redefinir_senha(professor_id: int, entrada: RedefinirSenhaEntrada, db: Db, _: Admin) -> None:
    servico.redefinir_senha(db, professor_id, entrada.nova_senha)


@router.delete("/{professor_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(professor_id: int, db: Db, admin: Admin) -> None:
    servico.excluir(db, professor_id, admin)
