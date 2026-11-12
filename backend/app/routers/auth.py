from fastapi import APIRouter, Request, status
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
    ip = request.client.host if request.client else "desconhecido"
    if limite_login.bloqueado(ip):
        raise ErroApi(
            429, "MUITAS_TENTATIVAS", "Muitas tentativas de login. Aguarde 5 minutos e tente novamente."
        )
    professor = db.scalars(select(Professor).where(Professor.rm == entrada.rm)).first()
    if not verificar_senha_ou_falso(entrada.senha, professor) or professor is None or not professor.ativo:
        limite_login.registrar_falha(ip)
        raise ErroApi(401, "CREDENCIAIS_INVALIDAS", "RM ou senha inválidos.")
    limite_login.registrar_sucesso(ip)
    token, expira = criar_token(professor)
    return LoginSaida(access_token=token, expira_em=expira, usuario=Usuario.model_validate(professor))


@router.get("/me", response_model=Usuario, summary="Conta logada")
def me(usuario: UsuarioAtual) -> Usuario:
    return Usuario.model_validate(usuario)


@router.put("/me/senha", status_code=status.HTTP_204_NO_CONTENT, summary="Trocar a própria senha")
def trocar_senha(entrada: TrocaSenhaEntrada, usuario: UsuarioAtual, db: Db) -> None:
    if not verificar_senha(entrada.senha_atual, usuario.senha_hash):
        raise ErroApi(422, "SENHA_ATUAL_INCORRETA", "A senha atual está incorreta.")
    usuario.senha_hash = hash_senha(entrada.nova_senha)
    db.commit()
