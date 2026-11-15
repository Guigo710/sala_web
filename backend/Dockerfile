# Backend sala_web: FastAPI + Alembic + seed (ADR-0001)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo \
    UPLOAD_DIR=/app/uploads

WORKDIR /app

# Só as dependências de produção, com versões exatas (ticket 36); pytest/httpx ficam no requirements-dev.txt.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Usuário sem privilégios (ticket 51), com uid/gid fixos: o serviço "uploads-permissoes" do Compose usa o número.
# O código fica com root (só leitura para "app"); só /app/uploads é dele. Um volume nomeado novo
# herda o dono desta pasta; um volume antigo, criado por root, é corrigido pelo "uploads-permissoes".
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

COPY . .
RUN mkdir -p /app/uploads && chown app:app /app/uploads

USER 10001:10001

EXPOSE 8000

# Migrations -> seed idempotente -> API
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
