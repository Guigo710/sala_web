# 28: CI no GitHub Actions

Status: ready-for-agent
Responsável: Sentinela
Origem: Atlas
Blocked by: 23, 26
Referências: ADR-0001

## Critérios de aceite
- [ ] `.github/workflows/ci.yml` em push e pull request.
- [ ] Job backend: serviço `postgres:16`, instala deps, `alembic upgrade head`, `pytest`.
- [ ] Job frontend: `npm ci`, `npm run lint`, `npm test`, `npm run build`.
- [ ] Sem segredos reais no workflow (valores de teste).
