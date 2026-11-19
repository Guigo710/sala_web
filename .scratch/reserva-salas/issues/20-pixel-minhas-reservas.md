# 20: Minhas reservas (ver e cancelar uma ou o grupo)

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.10 (`/reservas/minhas`, cancelar, grupos)

## Critérios de aceite
- [x] Abas Futuras / Passadas, filtro de status; reservas recorrentes identificadas.
- [x] Cancelar uma (com motivo opcional e confirmação) quando `pode_cancelar`.
- [x] Em reserva com `grupo_recorrencia_id`, opção "Cancelar todas as próximas desta recorrência", mostrando quantas foram canceladas.
- [x] Erros `RESERVA_JA_INICIADA` e `RESERVA_JA_CANCELADA` mostram `detail` e atualizam a lista.

## Comments

**Pixel (2026-11-12):** `/minhas-reservas`: abas Futuras/Passadas (teclado), filtro de situação, selo "Semanal" e "Cancelada". Cancelar uma (motivo opcional, confirmação) quando `pode_cancelar`; "Cancelar todas as próximas desta recorrência" mostra antes quantas serão canceladas e depois o total devolvido. RESERVA_JA_INICIADA/RESERVA_JA_CANCELADA mostram `detail` e atualizam a lista.
