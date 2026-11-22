# Backend sala_web: FastAPI + Alembic + seed (ADR-0001). Roda igual no Compose e no Render (ADR-0009).
FROM python:3.12-slim

# UPLOAD_DIR: pasta das fotos antigas, só lida pela importação (ADR-0010); a API não grava nada nela.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo \
    UPLOAD_DIR=/app/uploads

WORKDIR /app

# Só as dependências de produção, com versões exatas (ticket 36); pytest/httpx ficam no requirements-dev.txt.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Usuário sem privilégios (ticket 51), com uid/gid fixos. O código fica com root (só leitura para "app").
# Desde a rodada 5 (ADR-0010) o processo não grava em disco: as fotos ficam no banco.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

COPY . .
# Ponto de montagem do volume antigo de fotos (só leitura no Compose; não existe no Render).
RUN mkdir -p /app/uploads

USER 10001:10001

EXPOSE 8000

# Migrations -> seed idempotente -> importação das fotos antigas (idempotente, nunca falha) -> API.
# Porta: $PORT no Render (ele define a variável), 8000 no Compose. Um ÚNICO worker, de propósito: os limites
# de tentativas (login, troca de senha) ficam em memória, por processo (ADR-0009, ADR-0007 adendo 2).
# Não acrescente --workers.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && python -m app.importar_fotos && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
