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

COPY . .
RUN mkdir -p /app/uploads

EXPOSE 8000

# Migrations -> seed idempotente -> API
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
