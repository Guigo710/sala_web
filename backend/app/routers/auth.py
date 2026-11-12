from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.erros import ErroApi
from app.core.seguranca import (
    Db,
    UsuarioAtual,
    criar_token,
    hash_senha,
    limite_login,
    verificar_senha,
    verificar_senha_ou_falso,
)
from app.models import Professor
from app.schemas.auth import LoginEntrada, LoginSaida, TrocaSenhaEntrada, Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginSaida, summary="Login com RM e senha")
def login(entrada: LoginEntrada, request: Request, db: Db) -> LoginSaida:
    # IP da conexão; o uvicorn só o troca pelo de X-Forwarded-For para proxies de FORWARDED_ALLOW_IPS (ADR-0007).
    ip = request.client.host if request.client else "desconhecido"
    if limite_login.bloqueado(ip, entrada.rm):
        raise ErroApi(
            429, "MUITAS_TENTATIVAS", "Muitas tentativas de login. Aguarde 5 minutos e tente novamente."
        )
    professor = db.scalars(select(Professor).where(Professor.rm == entrada.rm)).first()
    if not verificar_senha_ou_falso(entrada.senha, professor) or professor is None or not professor.ativo:
        limite_login.registrar_falha(ip, entrada.rm)
        raise ErroApi(401, "CREDENCIAIS_INVALIDAS", "RM ou senha inválidos.")
    limite_login.registrar_sucesso(ip, entrada.rm)
    token, expira = criar_token(professor)
    return LoginSaida(access_token=token, expira_em=expira, usuario=Usuario.model_validate(professor))


@router.get("/me", response_model=Usuario, summary="Conta logada")
def me(usuario: UsuarioAtual) -> Usuario:
    return Usuario.model_validate(usuario)


@router.put(
    "/me/senha",
    response_model=LoginSaida,
    summary="Trocar a própria senha",
    description="Devolve um token novo para a sessão atual; todos os tokens anteriores da conta deixam de valer (ADR-0008).",
)
def trocar_senha(entrada: TrocaSenhaEntrada, usuario: UsuarioAtual, db: Db) -> LoginSaida:
    if not verificar_senha(entrada.senha_atual, usuario.senha_hash):
        raise ErroApi(422, "SENHA_ATUAL_INCORRETA", "A senha atual está incorreta.")
    usuario.senha_hash = hash_senha(entrada.nova_senha)
    usuario.revogar_sessoes()
    db.commit()
    db.refresh(usuario)
    token, expira = criar_token(usuario)
    return LoginSaida(access_token=token, expira_em=expira, usuario=Usuario.model_validate(usuario))
