# 01: Esqueleto do backend (FastAPI, config, erros, Dockerfile)

Status: resolved
Responsável: Forge
Origem: Atlas
Blocked by: (nenhum)
Referências: `docs/api-contrato.md` §1, §4.1; ADR-0001; `backend/README.md`

## O que fazer
Criar a estrutura `backend/app/...` descrita em `backend/README.md`, `requirements.txt`, `Dockerfile`
(Python 3.12; entrypoint: `alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000`),
`core/config.py` lendo as variáveis do `.env.example`, `core/db.py`, CORS por `CORS_ORIGENS`,
`StaticFiles` em `/uploads`, rota `GET /saude`, e o envelope de erro (§1.4) incluindo handler de
`RequestValidationError` (`codigo: VALIDACAO`, `erros: [{campo, mensagem}]`) e de exceção genérica (`ERRO_INTERNO`).

## Critérios de aceite
- [ ] `docker compose up --build` sobe `db` e `backend`; `GET http://localhost:8000/saude` → `200 {"status":"ok"}`.
- [ ] `/docs` (Swagger) abre.
- [ ] Um corpo inválido em qualquer rota devolve `422` no formato `{detail, codigo: "VALIDACAO", erros: [...]}`.
- [ ] Existe uma exceção `ErroApi(status, codigo, detail, **extras)` usada pelos services.
- [ ] Nenhum segredo fixo no código; tudo vem de variáveis de ambiente.

## Comments

- **Forge (2026-11-12):** Esqueleto em `backend/app` (core/config, db, erros, seguranca, tempo), `requirements.txt`, `Dockerfile` (python:3.12-slim). Envelope §1.4 com handlers de `RequestValidationError` (mensagens em português), `HTTPException` e `Exception` (`ERRO_INTERNO`). Verificado: `/saude` 200, `/docs` 200, compose `db`+`backend` sobe (imagem construída localmente). O serviço `frontend` do compose é do Pixel e não foi testado aqui.
