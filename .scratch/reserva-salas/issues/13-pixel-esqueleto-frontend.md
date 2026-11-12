# 13: Esqueleto do frontend, cliente da API e autenticação

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: (nenhum; desenvolver contra o contrato)
Referências: `docs/api-contrato.md` §1, §4.2; `frontend/README.md`; ADR-0004

## O que fazer
Projeto Vite + React, `Dockerfile` (dev server em `0.0.0.0:5173`), ESLint, Vitest, react-router, layout com
cabeçalho (Agenda, Ambientes, Minhas reservas, Admin, Entrar/Sair). `src/api/cliente.js`: base `VITE_API_URL`,
Bearer automático, parse do envelope de erro (§1.4) numa classe `ErroApi {status, codigo, detail, erros, conflitos}`;
401 em rota protegida → limpa sessão e vai para `/login`. `AuthContext` (token em `localStorage`, `GET /auth/me` ao abrir).
`RotaProtegida` e `RotaAdmin`.

## Critérios de aceite
- [x] `npm run build`, `npm run lint` e `npm test` passam.
- [ ] `docker compose up` serve o app em `:5173` (não verificado de ponta a ponta: ver comentário).
- [x] Um arquivo de conector por recurso em `src/api/` cobrindo **todas** as rotas do contrato.
- [x] Listas em query string enviadas como parâmetro repetido (`tipo=a&tipo=b`).
- [x] Rotas admin inacessíveis para professor/visitante.

## Comments

**Pixel (2026-11-12):** Projeto Vite + React em `frontend/` (Dockerfile node:22-slim, ESLint, Vitest, react-router). `src/api/cliente.js` (VITE_API_URL, Bearer, `ErroApi {status, codigo, detail, erros, conflitos}`, 401 → limpa sessão e vai a /login) e um conector por recurso cobrindo todas as rotas do contrato; listas como parâmetro repetido. `AuthContext` (token em localStorage, `GET /auth/me` ao abrir), `RotaProtegida`, `RotaAdmin`. Build, lint e test passam. Docker: imagem não construída aqui (rede do sandbox bloqueia `npm ci` no build e o Docker Hub limitou pulls); o `CMD` foi testado num container node:22-slim, servindo :5173 e lendo `VITE_API_URL` do ambiente.
