# 20: Minhas reservas (ver e cancelar uma ou o grupo)

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.10 (`/reservas/minhas`, cancelar, grupos)

## Critérios de aceite
- [ ] Abas Futuras / Passadas, filtro de status; reservas recorrentes identificadas.
- [ ] Cancelar uma (com motivo opcional e confirmação) quando `pode_cancelar`.
- [ ] Em reserva com `grupo_recorrencia_id`, opção "Cancelar todas as próximas desta recorrência", mostrando quantas foram canceladas.
- [ ] Erros `RESERVA_JA_INICIADA` e `RESERVA_JA_CANCELADA` mostram `detail` e atualizam a lista.
