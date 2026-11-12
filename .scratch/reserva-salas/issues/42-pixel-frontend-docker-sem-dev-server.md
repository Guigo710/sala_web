# 42: Imagem do frontend roda o dev server do Vite

Status: resolved
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
- [x] `docker compose up --build` serve o build (sem `/src/main.jsx` acessível: `curl :5173/src/main.jsx` ≠ código-fonte).
- [x] Rotas da SPA (`/agenda`, `/admin/ambientes`) abrem direto pela URL.
- [x] `npx playwright test` passa contra o Compose.

**Pixel (2026-11-12):** `frontend/Dockerfile` multi-stage (`node:22-alpine` → `npm ci && npm run build` com `VITE_API_URL` e `VITE_UPLOAD_MAX_MB` como `ARG`; `nginx:1.28-alpine` serve `dist/`). `frontend/nginx.conf`: fallback de SPA para `index.html`, arquivo com extensão inexistente → 404 (`/src/main.jsx` dá 404), cache longo só em `/assets/`, `nosniff`/`X-Frame-Options`/`Referrer-Policy`, só IPv4. Compose (só o serviço `frontend`): build args, porta `5173:80`, sem `environment`. Dev server do Vite agora escuta só em `localhost`. Validado: imagem construída (no sandbox o `npm ci` dentro do build precisou de rede do host + CA do proxy, só no ambiente de validação), `curl` de `/agenda`, `/admin/ambientes`, `/ambientes/3` → 200 com `index.html`; `/src/main.jsx` → 404; bundle sem o mock; `npx playwright test` 5/5 contra o Compose (backend da imagem anterior ao ticket 41). ADR-0001 ainda descreve o frontend do Compose em modo dev: Atlas atualizar.
