# 45: Dependências do frontend com alertas de segurança (npm audit)

Status: resolved
Responsável: Pixel
Origem: Sentinela
Severidade: baixa
Blocked by: (nenhum)
Referências: ticket 25; `frontend/package.json`

## Achados (`npm audit`, 12/11/2026)
| Pacote | Severidade | Onde | Advisory | Impacto aqui |
|---|---|---|---|---|
| `react-router` / `react-router-dom` 6.30 | moderada | produção | GHSA-wrjc-x8rr-h8h6 (open redirect com `\` em `<Link>`/`navigate`), GHSA-337j-9hxr-rhxg (SSR) | Baixo: o redirect pós-login usa `location.state.de` (não vem da URL) e não há SSR. Corrigido só na 7.18+. |
| `vitest` 3.2 (+ `@vitest/mocker`, `tinypool`) | crítica/moderada | só desenvolvimento | GHSA-82fw-gwwq-j7x9, GHSA-qxg6-89mg-rqv8, GHSA-5gmw-xhrv-c9v3, GHSA-85c8-ppgw-ccpr | Baixo: roda só em dev/CI, não vai para o bundle. |

## O que fazer
- Avaliar a migração para `react-router` 7.18+ (modo "library", mesmas APIs com as flags `v7_*` já ligadas em `main.jsx`).
- Atualizar `vitest` para a versão corrigida (major nova) e conferir `npm test`.
- Manter `npm audit --omit=dev` limpo; registrar exceções no README se alguma ficar.

## Critérios de aceite
- [x] `npm audit --omit=dev` sem alertas.
- [x] `npm run lint`, `npm test`, `npm run build` e `npx playwright test` verdes depois da atualização.

**Pixel (2026-11-12):** `react-router-dom` 6.30 → `react-router` 7.18.5 (pacote único do v7, imports trocados; flags `future` removidas, já eram o padrão no v7). `vitest` 3.2 → 5.1.0 (traz `@vitest/mocker` 5 e sai o `tinypool`). `npm audit`: antes 5 alertas (3 moderadas, 2 críticas; `--omit=dev`: 2 moderadas); depois 0 e 0. `lint`, `test` (55), `build` e `npx playwright test` (5/5, contra o Compose) verdes. Sem exceções a registrar.
