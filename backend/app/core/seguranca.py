"""Hash de senha (bcrypt), JWT HS256 e dependências de acesso (ADR-0004)."""

import threading
import time as _time
from datetime import datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.db import get_db
from app.core.erros import ErroApi
from app.core.tempo import agora_tz
from app.models import Professor

ALGORITMO = "HS256"
_bearer = HTTPBearer(auto_error=False, description="Token JWT obtido em POST /auth/login")


# ---------------------------------------------------------------- senha
def _bytes_senha(senha: str) -> bytes:
    # bcrypt considera só os primeiros 72 bytes; cortamos explicitamente (bcrypt>=5 recusa > 72).
    return senha.encode("utf-8")[:72]


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_bytes_senha(senha), bcrypt.gensalt()).decode("ascii")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bytes_senha(senha), senha_hash.encode("ascii"))
    except ValueError:
        return False


# Hash fixo para gastar o mesmo tempo quando o RM não existe (evita enumeração por tempo).
_HASH_FALSO = hash_senha("senha-inexistente-para-tempo-constante")


def verificar_senha_ou_falso(senha: str, professor: Professor | None) -> bool:
    if professor is None:
        verificar_senha(senha, _HASH_FALSO)
        return False
    return verificar_senha(senha, professor.senha_hash)


# ---------------------------------------------------------------- JWT
def criar_token(professor: Professor) -> tuple[str, datetime]:
    config = obter_config()
    emitido = agora_tz().replace(microsecond=0)
    expira = emitido + timedelta(minutes=config.JWT_EXPIRA_MINUTOS)
    payload = {
        "sub": str(professor.id),
        "papel": professor.papel,
        "iat": int(emitido.timestamp()),
        "exp": int(expira.timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITMO), expira


def _id_do_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, obter_config().JWT_SECRET, algorithms=[ALGORITMO], options={"require": ["sub", "exp"]}
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------- dependências
def usuario_opcional(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Professor | None:
    """Rotas públicas: token válido de conta ativa → professor; qualquer outra coisa → visitante."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        return None
    professor_id = _id_do_token(credenciais.credentials)
    if professor_id is None:
        return None
    professor = db.get(Professor, professor_id)
    if professor is None or not professor.ativo:
        return None
    return professor


def usuario_atual(usuario: Annotated[Professor | None, Depends(usuario_opcional)]) -> Professor:
    if usuario is None:
        raise ErroApi(401, "NAO_AUTENTICADO", "Faça login para continuar.")
    return usuario


def exigir_admin(usuario: Annotated[Professor, Depends(usuario_atual)]) -> Professor:
    if not usuario.eh_admin:
        raise ErroApi(403, "SEM_PERMISSAO", "Apenas administradores podem fazer isso.")
    return usuario


UsuarioOpcional = Annotated[Professor | None, Depends(usuario_opcional)]
UsuarioAtual = Annotated[Professor, Depends(usuario_atual)]
Admin = Annotated[Professor, Depends(exigir_admin)]
Db = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------- rate limit de login
class LimiteLogin:
    """5 falhas do mesmo IP em 5 min bloqueiam o IP por 5 min (em memória, por processo)."""

    def __init__(self, max_falhas: int = 5, janela_s: int = 300, bloqueio_s: int = 300) -> None:
        self.max_falhas = max_falhas
        self.janela_s = janela_s
        self.bloqueio_s = bloqueio_s
        self._falhas: dict[str, list[float]] = {}
        self._bloqueado_ate: dict[str, float] = {}
        self._lock = threading.Lock()

    def bloqueado(self, ip: str) -> bool:
        with self._lock:
            ate = self._bloqueado_ate.get(ip)
            if ate is None:
                return False
            if _time.monotonic() >= ate:
                del self._bloqueado_ate[ip]
                self._falhas.pop(ip, None)
                return False
            return True

    def registrar_falha(self, ip: str) -> None:
        agora_s = _time.monotonic()
        with self._lock:
            falhas = [t for t in self._falhas.get(ip, []) if agora_s - t < self.janela_s]
            falhas.append(agora_s)
            self._falhas[ip] = falhas
            if len(falhas) >= self.max_falhas:
                self._bloqueado_ate[ip] = agora_s + self.bloqueio_s

    def registrar_sucesso(self, ip: str) -> None:
        with self._lock:
            self._falhas.pop(ip, None)

    def limpar(self) -> None:
        with self._lock:
            self._falhas.clear()
            self._bloqueado_ate.clear()


limite_login = LimiteLogin()
