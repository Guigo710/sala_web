# 23: Testes backend: conflito, concorrência, recorrência e cancelamento

Status: ready-for-agent
Responsável: Sentinela
Origem: Atlas
Blocked by: 10, 11, 12
Referências: spec RN03–RN07; `docs/api-contrato.md` §4.10; ADR-0003

## Critérios de aceite
- [ ] pytest contra Postgres real (banco de teste isolado), fixtures de admin, professor, sala, grade e semestre.
- [ ] Conflito: sobreposição parcial/total → 409; encostadas → 201; cancelada não bloqueia.
- [ ] Concorrência: N requisições simultâneas ao mesmo bloco → exatamente 1 sucesso.
- [ ] Aulas seguidas: turno misto, buraco, aula inativa, aula inválida no dia (inclui sábado/domingo).
- [ ] Recorrência: série correta até o fim do semestre, prévia sem gravar, confirmação atômica, `DATA_FORA_DA_SERIE`, `SEM_SEMESTRE`.
- [ ] Cancelamento: dono antes/depois do início, outro professor (403), admin sempre, grupo só futuras.
- [ ] Tempo controlado (ex.: injetar "agora") para testes determinísticos.
