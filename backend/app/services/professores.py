"""Contas de professores e admins (contrato §4.7, RN08, ADR-0008)."""

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi
from app.core.seguranca import hash_senha
from app.models import GrupoRecorrencia, Professor, Reserva
from app.schemas.professores import ProfessorAtualizar, ProfessorCriar
from app.services.comum import commit_traduzindo, escapar_like, obter_ou_404

# FKs que impedem excluir uma conta (reservas e grupos, em qualquer papel e status).
_FKS_VINCULOS = (
    "reservas_professor_id_fkey",
    "reservas_criado_por_id_fkey",
    "reservas_cancelada_por_id_fkey",
    "grupos_recorrencia_professor_id_fkey",
    "grupos_recorrencia_criado_por_id_fkey",
)


def _rm_duplicado() -> ErroApi:
    return ErroApi(409, "RM_DUPLICADO", "Já existe uma conta com este RM.")


def _em_si_mesmo(detail: str) -> ErroApi:
    return ErroApi(422, "OPERACAO_EM_SI_MESMO", detail)


def _com_reservas() -> ErroApi:
    return ErroApi(
        409, "PROFESSOR_COM_RESERVAS", "Este professor tem reservas e não pode ser excluído. Desative a conta."
    )


def listar(
    db: Session, busca: str | None = None, papel: str | None = None, ativo: bool | None = None
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


def obter(db: Session, professor_id: int) -> Professor:
    return obter_ou_404(db, Professor, professor_id, "Professor não encontrado.")


def criar(db: Session, entrada: ProfessorCriar) -> Professor:
    if db.scalar(select(Professor.id).where(Professor.rm == entrada.rm)) is not None:
        raise _rm_duplicado()
    p = Professor(
        rm=entrada.rm,
        nome=entrada.nome,
        email=entrada.email,
        senha_hash=hash_senha(entrada.senha),
        papel=entrada.papel,
        ativo=True,
    )
    db.add(p)
    commit_traduzindo(db, {"professores_rm_key": _rm_duplicado()})
    db.refresh(p)
    return p


def atualizar(db: Session, professor_id: int, entrada: ProfessorAtualizar, admin: Professor) -> Professor:
    p = obter(db, professor_id)
    if p.id == admin.id and (not entrada.ativo or entrada.papel != "admin"):
        raise _em_si_mesmo("Você não pode desativar a própria conta nem remover o próprio papel de admin.")
    # ADR-0008: mudar o papel ou desativar derruba as sessões da conta; reativar não revive tokens antigos.
    if entrada.papel != p.papel or (p.ativo and not entrada.ativo):
        p.revogar_sessoes()
    p.nome, p.email, p.papel, p.ativo = entrada.nome, entrada.email, entrada.papel, entrada.ativo
    commit_traduzindo(db)
    db.refresh(p)
    return p


def redefinir_senha(db: Session, professor_id: int, nova_senha: str) -> None:
    """Redefinição pelo admin: troca o hash e derruba todas as sessões da conta (ADR-0008)."""
    p = obter(db, professor_id)
    p.senha_hash = hash_senha(nova_senha)
    p.revogar_sessoes()
    commit_traduzindo(db)


def excluir(db: Session, professor_id: int, admin: Professor) -> None:
    p = obter(db, professor_id)
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
        raise _com_reservas()
    db.delete(p)
    commit_traduzindo(db, {fk: _com_reservas() for fk in _FKS_VINCULOS})
