# 19: Reserva recorrente com prévia de conflitos

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 18
Referências: `docs/api-contrato.md` §4.10 (`/reservas/recorrentes/previa`, `/reservas/recorrentes`); spec RN06

## Critérios de aceite
- [x] Chama a prévia e lista cada data com status livre/em conflito (e quem ocupa), totais e semestre.
- [x] Datas livres vêm marcadas; professor pode desmarcar; datas em conflito não podem ser marcadas.
- [x] Botões "Reservar só as livres selecionadas" e "Desistir".
- [x] `409` na confirmação: avisa e refaz a prévia automaticamente. `422 SEM_SEMESTRE` mostra mensagem clara.

## Comments

**Pixel (2026-11-12):** Opção "Repetir toda semana" chama a prévia; `PreviaRecorrencia` lista datas livres/em conflito (com quem ocupa), totais e semestre; livres marcadas e desmarcáveis, conflitos bloqueados. Botões "Reservar só as livres selecionadas", "Voltar" e "Desistir". 409 avisa e refaz a prévia; 422 SEM_SEMESTRE com mensagem própria. Na recorrência, aulas ocupadas na 1ª data podem ser escolhidas (a prévia mostra o conflito).
