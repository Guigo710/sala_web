# 27: E2E com Playwright

Status: ready-for-agent
Responsável: Sentinela
Origem: Atlas
Blocked by: 17, 18, 20, 04
Referências: spec H05–H08

## Critérios de aceite
- [ ] Com o Compose de pé e o seed: login como professor criado pelo admin → reservar 2 aulas seguidas → ver na agenda → cancelar em Minhas reservas → sumir da agenda.
- [ ] Segundo cenário: tentar reservar o mesmo bloco com outro professor mostra o conflito.
- [ ] Roda com um comando documentado (`npx playwright test`).
