# 28: CI no GitHub Actions

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 23, 26
Referências: ADR-0001

## Critérios de aceite
- [x] `.github/workflows/ci.yml` em push e pull request.
- [x] Job backend: serviço `postgres:16`, instala deps, `alembic upgrade head`, `pytest`.
- [x] Job frontend: `npm ci`, `npm run lint`, `npm test`, `npm run build`.
- [x] Sem segredos reais no workflow (valores de teste).

## Comments

**Sentinela (12/11/2026):** feito. `.github/workflows/ci.yml` (push e pull_request), três jobs:
- `backend`: serviço `postgres:16`, Python 3.12, instala deps (usa `requirements-dev.txt` se existir, ticket 36),
  `alembic upgrade head`, `pytest -ra`.
- `frontend`: Node 22, `npm ci`, `npm run lint`, `npm test`, `npm run build`.
- `e2e` (depois dos dois): Postgres + migrations + seed + uvicorn, build de produção + `vite preview`, `npx playwright test`,
  logs e `test-results/` como artefato.
Só valores de teste (sem segredos). O workflow não rodou no GitHub daqui; os passos foram reproduzidos localmente
(backend com ambiente limpo e `DATABASE_URL_TESTE`: 227 passed; frontend lint/test/build ok; E2E 5 passed).
