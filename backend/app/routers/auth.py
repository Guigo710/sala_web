from fastapi import APIRouter, Request

from app.core.seguranca import Db, UsuarioAtual
from app.schemas.auth import LoginEntrada, LoginSaida, TrocaSenhaEntrada, Usuario
from app.services import auth as servico

router = APIRouter(prefix="/auth", tags=["auth"])


def _saida(sessao: servico.Sessao) -> LoginSaida:
    return LoginSaida(
        access_token=sessao.token, expira_em=sessao.expira_em, usuario=Usuario.model_validate(sessao.professor)
    )


@router.post("/login", response_model=LoginSaida, summary="Login com RM e senha")
def login(entrada: LoginEntrada, request: Request, db: Db) -> LoginSaida:
    # IP da conexão; o uvicorn só o troca pelo de X-Forwarded-For para proxies de FORWARDED_ALLOW_IPS (ADR-0007).
    ip = request.client.host if request.client else "desconhecido"
    return _saida(servico.login(db, ip, entrada.rm, entrada.senha))


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
    return _saida(servico.trocar_senha(db, usuario, entrada.senha_atual, entrada.nova_senha))
