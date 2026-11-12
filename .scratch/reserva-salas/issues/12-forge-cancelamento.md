# 12: Cancelamento de reserva e de grupo

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 11
Referências: `docs/api-contrato.md` §4.10; spec RN07

## Critérios de aceite
- [ ] `POST /reservas/{id}/cancelar`: grava `status=cancelada`, `cancelada_em`, `cancelada_por_id`, `motivo_cancelamento`; nunca apaga.
- [ ] Professor cancela só as próprias (`403` nas outras) e só antes de `data + inicio` (`422 RESERVA_JA_INICIADA`).
- [ ] Admin cancela qualquer uma, a qualquer hora; já cancelada → `409 RESERVA_JA_CANCELADA`.
- [ ] Após cancelar, o mesmo bloco pode ser reservado de novo (constraint parcial).
- [ ] `POST /reservas/grupos/{id}/cancelar` cancela só as ocorrências ativas ainda não iniciadas e devolve `canceladas` e `reservas_ids`.
