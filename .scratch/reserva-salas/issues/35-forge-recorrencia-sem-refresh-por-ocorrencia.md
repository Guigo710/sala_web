# 35: Confirmação de recorrência sem um refresh por ocorrência

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: baixa
Blocked by: (nenhum)
Referências: `docs/api-contrato.md` §4.10 (`POST /reservas/recorrentes`); spec RN06

## Problema
Depois do commit, `recorrencia.confirmar` faz `db.refresh(r)` para cada reserva criada
(`backend/app/services/recorrencia.py:125-127`). Cada refresh é um `SELECT` com os joins de `sala`, `professor`
e `cancelada_por` (`models/reserva.py:91-93`). Num semestre isso dá 15 a 20 consultas para montar a resposta;
o padrão N+1 que as listagens já evitam.

As listagens (`GET /reservas`, `/reservas/minhas`, `/salas`, disponibilidade, grupo) foram conferidas e usam
um número fixo de consultas (`joined`/`selectinload`/`contains_eager`). Os índices atuais bastam para o volume
da v1: nenhum índice novo é pedido.

## O que fazer
- Depois do commit, recarregar as ocorrências com **uma** consulta (reaproveitar `services/reservas.reservas_do_grupo`)
  e devolver essa lista, ordenada por data.
- `db.refresh(grupo)` pode continuar (é um só).

## Critérios de aceite
- [ ] Confirmar uma recorrência de N datas executa um número de `SELECT`s que **não cresce com N** (teste contando
  as consultas com evento `before_cursor_execute` do SQLAlchemy, para N = 2 e N = 15).
- [ ] Resposta idêntica à de antes (mesmos campos, `reservas` ordenadas por data).

## Comments
