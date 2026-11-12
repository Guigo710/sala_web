# 11: Reserva recorrente semanal: prévia e confirmação

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 10
Referências: `docs/api-contrato.md` §3.13, §4.10; spec RN06

## Critérios de aceite
- [ ] `POST /reservas/recorrentes/previa` lista `data_inicio`, +7, +14… até `data_fim` do semestre que contém `data_inicio` (inclusive), com `livre`/`conflitos`, `total`, `livres`, `em_conflito`; não grava nada.
- [ ] Sem semestre → `422 SEM_SEMESTRE`.
- [ ] `POST /reservas/recorrentes` cria 1 grupo + 1 reserva por data enviada, numa transação; data fora da série → `422 DATA_FORA_DA_SERIE`.
- [ ] Se qualquer data conflitar, nada é gravado e volta `409 CONFLITO_RESERVA` com todos os conflitos.
- [ ] `GET /reservas/grupos/{id}`: dono ou admin; outro professor → `403`.
