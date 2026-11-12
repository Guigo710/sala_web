"""Hash de senha (bcrypt), JWT HS256 e dependências de acesso (ADR-0004)."""

import threading
import time as _time
from collections.abc import Callable
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
        "ver": professor.token_versao,
        "iat": int(emitido.timestamp()),
        "exp": int(expira.timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITMO), expira


def _claims_do_token(token: str) -> tuple[int, int] | None:
    """(id do professor, versão do token) de um JWT válido; `None` se inválido/expirado/sem `ver`."""
    try:
        payload = jwt.decode(
            token, obter_config().JWT_SECRET, algorithms=[ALGORITMO], options={"require": ["sub", "exp", "ver"]}
        )
        versao = payload["ver"]
        if not isinstance(versao, int) or isinstance(versao, bool):
            return None
        return int(payload["sub"]), versao
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------- dependências
def usuario_opcional(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Professor | None:
    """Rotas públicas: token válido de conta ativa → professor; qualquer outra coisa → visitante.

    Token revogado (`ver` diferente de `token_versao`, ADR-0008) é tratado como inválido.
    """
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        return None
    claims = _claims_do_token(credenciais.credentials)
    if claims is None:
        return None
    professor_id, versao = claims
    professor = db.get(Professor, professor_id)
    if professor is None or not professor.ativo or professor.token_versao != versao:
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


# ---------------------------------------------------------------- rate limit de login (ADR-0007)
MAX_FALHAS_PAR = 5  # falhas do mesmo par (IP, RM) que bloqueiam o par
MAX_FALHAS_IP = 20  # falhas do mesmo IP, de qualquer RM, que bloqueiam o IP
JANELA_S = 300  # janela de contagem
BLOQUEIO_S = 300  # duração do bloqueio


class _Contador:
    """Falhas recentes e bloqueios por chave; descarta o que venceu (não cresce sem limite)."""

    def __init__(self, max_falhas: int, janela_s: float, bloqueio_s: float) -> None:
        self.max_falhas = max_falhas
        self.janela_s = janela_s
        self.bloqueio_s = bloqueio_s
        self.falhas: dict[object, list[float]] = {}
        self.bloqueado_ate: dict[object, float] = {}

    def bloqueado(self, chave: object, agora_s: float) -> bool:
        ate = self.bloqueado_ate.get(chave)
        if ate is None:
            return False
        if agora_s >= ate:
            del self.bloqueado_ate[chave]
            self.falhas.pop(chave, None)
            return False
        return True

    def registrar_falha(self, chave: object, agora_s: float) -> None:
        falhas = [t for t in self.falhas.get(chave, []) if agora_s - t < self.janela_s]
        falhas.append(agora_s)
        self.falhas[chave] = falhas
        if len(falhas) >= self.max_falhas:
            self.bloqueado_ate[chave] = agora_s + self.bloqueio_s

    def zerar(self, chave: object) -> None:
        self.falhas.pop(chave, None)

    def descartar_vencidos(self, agora_s: float) -> None:
        for chave in [c for c, ate in self.bloqueado_ate.items() if agora_s >= ate]:
            del self.bloqueado_ate[chave]
        for chave in list(self.falhas):
            recentes = [t for t in self.falhas[chave] if agora_s - t < self.janela_s]
            if recentes:
                self.falhas[chave] = recentes
            else:
                del self.falhas[chave]

    def limpar(self) -> None:
        self.falhas.clear()
        self.bloqueado_ate.clear()


class LimiteLogin:
    """Limite de tentativas de login em memória, por processo (ADR-0007).

    - par (IP, RM digitado): `max_falhas_par` falhas na janela bloqueiam o par;
    - IP: `max_falhas_ip` falhas na janela, de qualquer RM, bloqueiam o IP.
    O RM entra na chave exatamente como digitado (mesmo critério da busca do login).
    `relogio` (segundos, monotônico) pode ser trocado nos testes.
    """

    def __init__(
        self,
        max_falhas_par: int = MAX_FALHAS_PAR,
        max_falhas_ip: int = MAX_FALHAS_IP,
        janela_s: float = JANELA_S,
        bloqueio_s: float = BLOQUEIO_S,
        relogio: Callable[[], float] = _time.monotonic,
    ) -> None:
        self.relogio = relogio
        self._par = _Contador(max_falhas_par, janela_s, bloqueio_s)
        self._ip = _Contador(max_falhas_ip, janela_s, bloqueio_s)
        self._lock = threading.Lock()

    def bloqueado(self, ip: str, rm: str) -> bool:
        agora_s = self.relogio()
        with self._lock:
            # avalia os dois (cada um descarta o próprio bloqueio vencido)
            par = self._par.bloqueado((ip, rm), agora_s)
            por_ip = self._ip.bloqueado(ip, agora_s)
            return par or por_ip

    def registrar_falha(self, ip: str, rm: str) -> None:
        agora_s = self.relogio()
        with self._lock:
            self._par.descartar_vencidos(agora_s)
            self._ip.descartar_vencidos(agora_s)
            self._par.registrar_falha((ip, rm), agora_s)
            self._ip.registrar_falha(ip, agora_s)

    def registrar_sucesso(self, ip: str, rm: str) -> None:
        """Login certo zera só as falhas do par (não as do IP)."""
        with self._lock:
            self._par.zerar((ip, rm))

    def tamanho(self) -> int:
        """Quantidade de entradas guardadas (falhas + bloqueios), para testes e diagnóstico."""
        with self._lock:
            return sum(len(c.falhas) + len(c.bloqueado_ate) for c in (self._par, self._ip))

    def limpar(self) -> None:
        with self._lock:
            self._par.limpar()
            self._ip.limpar()


limite_login = LimiteLogin()
