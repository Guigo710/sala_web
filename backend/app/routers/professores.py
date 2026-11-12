from typing import Literal

from fastapi import APIRouter, status
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, nao_encontrado
from app.core.seguranca import Admin, Db, hash_senha
from app.models import GrupoRecorrencia, Professor, Reserva
from app.schemas.auth import Usuario
from app.schemas.professores import ProfessorAtualizar, ProfessorCriar, RedefinirSenhaEntrada
from app.services.salas import escapar_like

router = APIRouter(prefix="/professores", tags=["professores"])


def _obter(db: Db, professor_id: int) -> Professor:
    p = db.get(Professor, professor_id)
    if p is None:
        raise nao_encontrado("Professor não encontrado.")
    return p


def _em_si_mesmo(detail: str) -> ErroApi:
    return ErroApi(422, "OPERACAO_EM_SI_MESMO", detail)


def _erro_com_reservas() -> ErroApi:
    return ErroApi(
        409, "PROFESSOR_COM_RESERVAS", "Este professor tem reservas e não pode ser excluído. Desative a conta."
    )


@router.get("", response_model=list[Usuario])
def listar(
    db: Db,
    _: Admin,
    busca: str | None = None,
    papel: Literal["professor", "admin"] | None = None,
    ativo: bool | None = None,
) -> list[Professor]:
    stmt = select(Professor)
    if busca and busca.strip():
        padrao = f"%{escapar_like(busca.strip())}%"
        stmt = stmt.where(or_(Professor.nome.ilike(padrao, escape="\\"), Professor.rm.ilike(padrao, escape="\\")))
    if papel is not None:
        stmt = stmt.where(Professor.papel == papel)
    if ativo is not None:
        stmt = stmt.where(Professor.ativo.is_(ativo))
    return list(db.scalars(stmt.order_by(Professor.nome, Professor.id)))


@router.get("/{professor_id}", response_model=Usuario)
def obter(professor_id: int, db: Db, _: Admin) -> Professor:
    return _obter(db, professor_id)


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def criar(entrada: ProfessorCriar, db: Db, _: Admin) -> Professor:
    duplicado = ErroApi(409, "RM_DUPLICADO", "Já existe uma conta com este RM.")
    if db.scalar(select(Professor.id).where(Professor.rm == entrada.rm)) is not None:
        raise duplicado
    p = Professor(
        rm=entrada.rm,
        nome=entrada.nome,
        email=entrada.email,
        senha_hash=hash_senha(entrada.senha),
        papel=entrada.papel,
        ativo=True,
    )
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise duplicado from None
    db.refresh(p)
    return p


@router.put("/{professor_id}", response_model=Usuario)
def atualizar(professor_id: int, entrada: ProfessorAtualizar, db: Db, admin: Admin) -> Professor:
    p = _obter(db, professor_id)
    if p.id == admin.id and (not entrada.ativo or entrada.papel != "admin"):
        raise _em_si_mesmo("Você não pode desativar a própria conta nem remover o próprio papel de admin.")
    # ADR-0008: mudar o papel ou desativar derruba as sessões da conta; reativar não revive tokens antigos.
    if entrada.papel != p.papel or (p.ativo and not entrada.ativo):
        p.revogar_sessoes()
    p.nome, p.email, p.papel, p.ativo = entrada.nome, entrada.email, entrada.papel, entrada.ativo
    db.commit()
    db.refresh(p)
    return p


@router.put("/{professor_id}/senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(professor_id: int, entrada: RedefinirSenhaEntrada, db: Db, _: Admin) -> None:
    p = _obter(db, professor_id)
    p.senha_hash = hash_senha(entrada.nova_senha)
    p.revogar_sessoes()
    db.commit()


@router.delete("/{professor_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(professor_id: int, db: Db, admin: Admin) -> None:
    p = _obter(db, professor_id)
    if p.id == admin.id:
        raise _em_si_mesmo("Você não pode excluir a própria conta.")
    pid = p.id
    tem_vinculo = db.scalar(
        select(
            exists().where(
                or_(Reserva.professor_id == pid, Reserva.criado_por_id == pid, Reserva.cancelada_por_id == pid)
            )
            | exists().where(or_(GrupoRecorrencia.professor_id == pid, GrupoRecorrencia.criado_por_id == pid))
        )
    )
    if tem_vinculo:
        raise _erro_com_reservas()
    db.delete(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _erro_com_reservas() from None
