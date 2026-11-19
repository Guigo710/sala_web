# 27: E2E com Playwright

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 17, 18, 20, 04
Referências: spec H05–H08

## Critérios de aceite
- [x] Com o Compose de pé e o seed: login como professor criado pelo admin → reservar 2 aulas seguidas → ver na agenda → cancelar em Minhas reservas → sumir da agenda.
- [x] Segundo cenário: tentar reservar o mesmo bloco com outro professor mostra o conflito.
- [x] Roda com um comando documentado (`npx playwright test`).

## Comments

**Sentinela (12/11/2026):** feito. `frontend/e2e/reservas.spec.js` + `frontend/playwright.config.js`
(`@playwright/test` 1.63.0, mesma versão dos navegadores instalados). Comando: `npx playwright test` (ou `npm run e2e`),
documentado em `frontend/README.md`.
Cenários: admin cria professor pela UI → professor reserva 2 aulas seguidas → vê na agenda (mês) → outro professor
vê o bloco ocupado e recebe o 409 real numa corrida → recorrência com prévia (conflito listado, desmarca uma livre,
grava só as selecionadas) → cancela em Minhas reservas e some da agenda → cancela a série.
Resultado: **5 passed** contra o dev server e **5 passed** contra o build de produção (`vite preview`).
Rodado com Postgres local + uvicorn + Vite (sem Docker: limites de rede no ambiente). O job `e2e` do CI repete isso.
