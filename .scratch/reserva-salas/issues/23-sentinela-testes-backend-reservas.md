# 23: Testes backend: conflito, concorrência, recorrência e cancelamento

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 10, 11, 12
Referências: spec RN03–RN07; `docs/api-contrato.md` §4.10; ADR-0003

## Critérios de aceite
- [x] pytest contra Postgres real (banco de teste isolado), fixtures de admin, professor, sala, grade e semestre.
- [x] Conflito: sobreposição parcial/total → 409; encostadas → 201; cancelada não bloqueia.
- [x] Concorrência: N requisições simultâneas ao mesmo bloco → exatamente 1 sucesso.
- [x] Aulas seguidas: turno misto, buraco, aula inativa, aula inválida no dia (inclui sábado/domingo).
- [x] Recorrência: série correta até o fim do semestre, prévia sem gravar, confirmação atômica, `DATA_FORA_DA_SERIE`, `SEM_SEMESTRE`.
- [x] Cancelamento: dono antes/depois do início, outro professor (403), admin sempre, grupo só futuras.
- [x] Tempo controlado (ex.: injetar "agora") para testes determinísticos.

## Comments

**Sentinela (12/11/2026):** feito.
- `backend/tests/conftest.py`: fixture `relogio` (injeta "agora" via `app.core.tempo.agora_tz`; JWT segue no relógio real),
  `semestre_ref` (2030-1), `novo_professor`, `aulas`.
- `backend/tests/test_reservas_conflito.py` (39 testes): matriz de sobreposição (parcial/total/contém/encostada),
  cancelada não bloqueia, constraint `ex_reservas_sem_sobreposicao` com INSERT direto (SQLSTATE 23P01), service "cego"
  → constraint vira o mesmo 409 com `conflitos`; concorrência com `threading.Barrier` (8 professores no mesmo bloco → 1×201;
  blocos parcialmente sobrepostos → 1×201; duas recorrências disputando datas → uma grava tudo, a outra nada);
  aulas seguidas (turno misto, buraco, inativa, sábado/domingo, ordem dos ids), `DATA_PASSADA` no limite exato,
  `SALA_INATIVA`, `professor_id`, snapshot de horário.
- `backend/tests/test_recorrencia_cancelamento.py` (41 testes): série até `data_fim` inclusive, prévia sem gravar,
  confirmação atômica, `DATA_FORA_DA_SERIE` (dia errado, antes do início, depois do fim), `SEM_SEMESTRE`, datas
  vazias/repetidas, grupo (dono/outro/admin), cancelamento do dono no limite (09:29 ok, 09:30 → 422), outro professor 403,
  admin sempre, grupo só futuras (professor e admin), `pode_cancelar`, `/reservas/minhas`, intervalos da agenda, disponibilidade.
- Concorrência rodada 5× seguidas sem falha. Mutação conferida: trocar `>=` por `>` no cancelamento derruba o teste.
