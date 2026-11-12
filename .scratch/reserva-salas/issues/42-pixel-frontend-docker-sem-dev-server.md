# 42: Imagem do frontend roda o dev server do Vite

Status: ready-for-agent
Responsável: Pixel
Origem: Sentinela
Severidade: média
Blocked by: (nenhum)
Referências: ticket 25; ADR-0001; `frontend/Dockerfile`; `docker-compose.yml` (serviço `frontend`)

## Problema
O `Dockerfile` do frontend faz `npm run dev -- --host 0.0.0.0`. O dev server do Vite não é feito para ficar exposto
na rede: serve o código-fonte (`/src/...`), o `/@fs/` e o HMR, e já teve várias falhas de leitura arbitrária de
arquivos (`server.fs.deny` bypass). Na escola ele fica acessível a qualquer máquina da rede. Também carrega o
`src/api/mock` (só fica fora do bundle de produção) se alguém subir com `VITE_USE_MOCK=true`.

## O que fazer
- Build multi-stage: `npm ci && npm run build` com `VITE_API_URL` como `ARG`, e servir `dist/` com um servidor
  estático (ex.: `nginx:alpine` com fallback de SPA para `index.html`), ou no mínimo `vite preview`.
- Manter o `npm run dev` para desenvolvimento local, fora da imagem.
- O E2E (`npx playwright test`) e o CI (`ci.yml`, job `e2e`) já rodam contra o build de produção (`vite preview`).

## Critérios de aceite
- [ ] `docker compose up --build` serve o build (sem `/src/main.jsx` acessível: `curl :5173/src/main.jsx` ≠ código-fonte).
- [ ] Rotas da SPA (`/agenda`, `/admin/ambientes`) abrem direto pela URL.
- [ ] `npx playwright test` passa contra o Compose.
