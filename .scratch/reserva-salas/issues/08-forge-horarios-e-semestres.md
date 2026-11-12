# 08: Horários de aula e semestres (CRUD)

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 03
Referências: `docs/api-contrato.md` §4.8, §4.9; ADR-0002

## O que fazer
Além dos CRUDs, criar `services/aulas.py` com `validar_bloco(db, horario_ids, data) -> (aulas, inicio, fim)` implementando RN03
(`AULAS_NAO_SEGUIDAS`, `AULA_INVALIDA_NO_DIA`, 404, `VALIDACAO`), reusado pelos tickets 06, 10 e 11.

## Critérios de aceite
- [ ] Rotas de §4.8 e §4.9 com acessos e códigos do contrato.
- [ ] `GET /horarios?dia_semana=N` filtra por `N = ANY(dias_semana)`; ordenação manha → tarde → noite, por `ordem`.
- [ ] Horário ativo sobrepondo outro ativo em dia comum → `409 HORARIO_SOBREPOSTO`; turno+ordem repetidos → `409 ORDEM_DUPLICADA`.
- [ ] Excluir horário referenciado por reserva → `409 HORARIO_EM_USO`.
- [ ] Semestres sobrepostos → `409 SEMESTRE_SOBREPOSTO`; `GET /semestres/atual` devolve o que contém hoje ou o próximo; nenhum → `404`.
- [ ] `validar_bloco` com testes unitários mínimos (turno misto, buraco, inativa, dia inválido, ordem dos ids indiferente).
- [ ] Excluir semestre com grupo de recorrência → `409 SEMESTRE_EM_USO`.
