# ADR-0001: Stack React + FastAPI + PostgreSQL, executada com Docker Compose

Status: aceito · Data: 2026-11-12 · Atualizado: 2026-11-15 (tickets 42 e 43) · Autor: Atlas

## Contexto
Trabalho de disciplina, equipe de 3 pessoas, custo zero, rodando localmente ou num servidor da escola.
O `decisoes.md` fixa a stack: React + Vite (FullCalendar gratuito), Python + FastAPI, SQLAlchemy 2.x,
Pydantic v2, Alembic, PostgreSQL. Precisamos que qualquer membro suba tudo com um comando.

## Decisão
- Monorepo com `backend/` e `frontend/` na raiz.
- `docker-compose.yml` com três serviços:
  - `db`: `postgres:16`, volume nomeado `pgdata`, healthcheck `pg_isready`. Porta publicada **só em loopback**
    (`127.0.0.1:${DB_PORTA_HOST:-5432}:5432`, ticket 43): serve para rodar o backend fora do Docker na mesma
    máquina, mas o banco não fica acessível pela rede da escola. O backend do Compose usa a rede interna (host `db`).
  - `backend`: build de `backend/Dockerfile`, porta 8000, sobe só depois do `db` saudável; ao iniciar roda
    `alembic upgrade head`, o seed idempotente (política no ADR-0006) e `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
    Volume nomeado `uploads` montado em `/app/uploads` (fotos).
  - `frontend`: build de produção multi-stage de `frontend/Dockerfile` (ticket 42): `node:22-alpine` roda
    `npm ci && npm run build`; `nginx:1.28-alpine` serve o `dist/` com `frontend/nginx.conf` (fallback de SPA para
    `index.html`, arquivo inexistente com extensão → 404, cache longo só em `/assets/`, cabeçalhos `nosniff`,
    `X-Frame-Options`, `Referrer-Policy`). Porta `5173` no host apontando para a `80` do container.
    `VITE_API_URL` e `VITE_UPLOAD_MAX_MB` são **build args** (o Vite grava os valores no JavaScript gerado):
    mudou alguma delas no `.env`, rode `docker compose up --build`. O serviço não tem `environment`.
- Configuração só por variáveis de ambiente (`.env`, modelo em `.env.example`); nenhum segredo no repositório.
- PostgreSQL 16 (não SQLite) porque a garantia anti-conflito depende de `EXCLUDE USING gist` (ADR-0003).
- Sem prefixo de versão nas rotas (`/salas`, não `/api/v1/salas`); o projeto tem um único cliente.

## Consequências
- Ambiente idêntico para todos; testes de integração do backend rodam contra Postgres real (não SQLite).
- O frontend no Compose é o build de produção: sem hot reload, sem código-fonte (`/src/...`), `/@fs/` ou HMR
  expostos na rede. O dev server do Vite (`npm run dev`, só em `localhost`) fica para o desenvolvimento local,
  fora da imagem. O E2E (Playwright) e o CI rodam contra build de produção.
- O Postgres não é alcançável de outras máquinas mesmo com a senha de exemplo; ainda assim, troque
  `POSTGRES_PASSWORD` (o backend avisa no log quando a `DATABASE_URL` usa a senha de exemplo).
- Duas formas de rodar: tudo no Docker, ou só `db` no Docker e backend (`uvicorn`) e frontend (`npm run dev`)
  locais, na mesma máquina do banco (README de cada pasta).
