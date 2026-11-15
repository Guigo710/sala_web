"""Login com limite de tentativas (ADR-0007) e troca da própria senha (ADR-0008)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi
from app.core.seguranca import criar_token, hash_senha, limite_login, verificar_senha, verificar_senha_ou_falso
from app.models import Professor
from app.services.comum import commit_traduzindo


@dataclass(frozen=True)
class Sessao:
    token: str
    expira_em: datetime
    professor: Professor


def _emitir(professor: Professor) -> Sessao:
    token, expira = criar_token(professor)
    return Sessao(token=token, expira_em=expira, professor=professor)


def login(db: Session, ip: str, rm: str, senha: str) -> Sessao:
    """`ip` é o da conexão (o uvicorn só o troca pelo de X-Forwarded-For para proxies de FORWARDED_ALLOW_IPS)."""
    if limite_login.bloqueado(ip, rm):
        raise ErroApi(
            429, "MUITAS_TENTATIVAS", "Muitas tentativas de login. Aguarde 5 minutos e tente novamente."
        )
    professor = db.scalars(select(Professor).where(Professor.rm == rm)).first()
    if not verificar_senha_ou_falso(senha, professor) or professor is None or not professor.ativo:
        limite_login.registrar_falha(ip, rm)
        raise ErroApi(401, "CREDENCIAIS_INVALIDAS", "RM ou senha inválidos.")
    limite_login.registrar_sucesso(ip, rm)
    return _emitir(professor)


def trocar_senha(db: Session, usuario: Professor, senha_atual: str, nova_senha: str) -> Sessao:
    """Troca a própria senha, derruba todas as sessões da conta e devolve um token novo para esta."""
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise ErroApi(422, "SENHA_ATUAL_INCORRETA", "A senha atual está incorreta.")
    usuario.senha_hash = hash_senha(nova_senha)
    usuario.revogar_sessoes()
    commit_traduzindo(db)
    db.refresh(usuario)
    return _emitir(usuario)
