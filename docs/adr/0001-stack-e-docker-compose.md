# ADR-0001: Stack React + FastAPI + PostgreSQL, executada com Docker Compose

Status: aceito · Data: 2026-11-12 · Autor: Atlas

## Contexto
Trabalho de disciplina, equipe de 3 pessoas, custo zero, rodando localmente ou num servidor da escola.
O `decisoes.md` fixa a stack: React + Vite (FullCalendar gratuito), Python + FastAPI, SQLAlchemy 2.x,
Pydantic v2, Alembic, PostgreSQL. Precisamos que qualquer membro suba tudo com um comando.

## Decisão
- Monorepo com `backend/` e `frontend/` na raiz.
- `docker-compose.yml` com três serviços:
  - `db`: `postgres:16`, volume nomeado `pgdata`, healthcheck `pg_isready`.
  - `backend`: build de `backend/Dockerfile`, porta 8000, sobe só depois do `db` saudável; ao iniciar roda
    `alembic upgrade head`, o seed idempotente (política no ADR-0006) e `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
    Volume nomeado `uploads` montado em `/app/uploads` (fotos).
  - `frontend`: build de `frontend/Dockerfile`, servidor de desenvolvimento do Vite em `0.0.0.0:5173`.
- Configuração só por variáveis de ambiente (`.env`, modelo em `.env.example`); nenhum segredo no repositório.
- PostgreSQL 16 (não SQLite) porque a garantia anti-conflito depende de `EXCLUDE USING gist` (ADR-0003).
- Sem prefixo de versão nas rotas (`/salas`, não `/api/v1/salas`); o projeto tem um único cliente.

## Consequências
- Ambiente idêntico para todos; testes de integração do backend rodam contra Postgres real (não SQLite).
- O frontend no Compose roda em modo dev (hot reload). Build de produção (`npm run build` + servidor
  estático) fica para quando houver deploy.
- Duas formas de rodar: tudo no Docker, ou só `db` no Docker e backend/frontend locais (README de cada pasta).
