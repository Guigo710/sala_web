# 13: Esqueleto do frontend, cliente da API e autenticação

Status: ready-for-agent
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
- [ ] `npm run build`, `npm run lint` e `npm test` passam; `docker compose up` serve o app em `:5173`.
- [ ] Um arquivo de conector por recurso em `src/api/` cobrindo **todas** as rotas do contrato.
- [ ] Listas em query string enviadas como parâmetro repetido (`tipo=a&tipo=b`).
- [ ] Rotas admin inacessíveis para professor/visitante.
