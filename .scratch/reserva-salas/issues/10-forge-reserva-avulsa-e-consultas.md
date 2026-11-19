# 10: Reserva avulsa (aulas seguidas) e consultas de reservas

Status: resolved
Responsável: Forge
Origem: Atlas
Blocked by: 06, 08
Referências: `docs/api-contrato.md` §3.11, §3.12, §4.10; spec RN03–RN05, RN08; ADR-0002, ADR-0003

## O que fazer
Service `services/reservas.py` usando `validar_bloco` (ticket 08), com checagem de conflito que devolve `Conflito[]`, e tradução de `IntegrityError 23P01` para o mesmo 409.
Rotas `POST /reservas`, `GET /reservas`, `GET /reservas/minhas`, `GET /reservas/{id}`.

## Critérios de aceite
- [ ] `horario_ids` de turnos diferentes, com buraco ou inativos → `422 AULAS_NAO_SEGUIDAS`; aula que não vale no dia → `422 AULA_INVALIDA_NO_DIA`.
- [ ] Reserva gravada com `inicio`/`fim` da primeira/última aula, `horario_inicio_id`, `horario_fim_id`, `quantidade_aulas`.
- [ ] Sobreposição → `409 CONFLITO_RESERVA` com `conflitos`; aulas encostadas não conflitam.
- [ ] Duas requisições concorrentes para o mesmo bloco: exatamente uma `201` e outra `409` (nenhum 500).
- [ ] `DATA_PASSADA`, `SALA_INATIVA`, `PROFESSOR_INATIVO` e `403` para professor que envia `professor_id`, conforme contrato.
- [ ] `GET /reservas` exige exatamente um modo de período (`mes` | `data` | `de`+`ate` ≤ 62 dias) → senão `422 INTERVALO_INVALIDO`; filtros `sala_id`, `professor_id`, `status`.
- [ ] Respostas públicas não contêm RM; `pode_cancelar` calculado conforme §3.11.
- [ ] `GET /reservas/minhas` com `periodo` e `status` e ordenação do contrato.

## Comments

- **Forge (2026-11-12):** `services/reservas.py`, `routers/reservas.py`. Verificado: snapshot início/fim, 409 com `conflitos`, encostadas passam, 8 requisições concorrentes → 1×201 + 7×409 (nenhum 500), `DATA_PASSADA`, `SALA_INATIVA`, 403 com `professor_id`, `INTERVALO_INVALIDO`, sem RM na agenda pública.
