# 19: Reserva recorrente com prévia de conflitos

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 18
Referências: `docs/api-contrato.md` §4.10 (`/reservas/recorrentes/previa`, `/reservas/recorrentes`); spec RN06

## Critérios de aceite
- [ ] Chama a prévia e lista cada data com status livre/em conflito (e quem ocupa), totais e semestre.
- [ ] Datas livres vêm marcadas; professor pode desmarcar; datas em conflito não podem ser marcadas.
- [ ] Botões "Reservar só as livres selecionadas" e "Desistir".
- [ ] `409` na confirmação: avisa e refaz a prévia automaticamente. `422 SEM_SEMESTRE` mostra mensagem clara.
