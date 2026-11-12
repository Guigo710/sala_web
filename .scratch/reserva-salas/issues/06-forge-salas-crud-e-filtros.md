# 06: Salas: CRUD, associações, tipos, filtros e disponibilidade

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 05, 08
Referências: `docs/api-contrato.md` §3.6, §3.7, §4.3

## Critérios de aceite
- [ ] `GET /salas/tipos`, `GET /salas`, `GET /salas/{id}`, `POST`, `PUT`, `DELETE`, `PUT /salas/{id}/equipamentos`, `PUT /salas/{id}/softwares` conforme contrato.
- [ ] Filtros combinados com E: `tipo` (repetível, OU entre valores), `capacidade_min`, `equipamento_id` e `software_id` (repetíveis, sala precisa ter **todos**), `busca`.
- [ ] `data` + `horario_ids` devolve só salas sem reserva ativa sobreposta ao bloco; um sem o outro → `422 VALIDACAO`; aulas inválidas → `422 AULAS_NAO_SEGUIDAS`/`AULA_INVALIDA_NO_DIA` (reusar `validar_bloco` do ticket 08).
- [ ] Inativas não aparecem nem por `{id}` (404) para não-admin; admin as vê com `incluir_inativas=true` e por id.
- [ ] `GET /salas/{id}/disponibilidade?data=` devolve as aulas do dia com `livre`, `passou` e `reserva`.
- [ ] `DELETE` com qualquer reserva → `409 SALA_COM_RESERVAS`; sem reservas apaga fotos (arquivos inclusive).
- [ ] `foto_capa_url` e ordenações conforme §3.6/§3.7.
