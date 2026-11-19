# ADR-0003: Garantia anti-conflito com constraint de exclusão (btree_gist + tsrange)

Status: aceito · Data: 2026-11-12 · Autor: Atlas

## Contexto
Regra principal: nunca duas reservas ativas sobrepostas na mesma sala. Uma checagem só no service
(`SELECT` antes do `INSERT`) tem condição de corrida: duas requisições simultâneas veem a sala livre e
ambas gravam. Reservas canceladas permanecem na tabela (histórico) e não podem bloquear.

Alternativas consideradas:
1. UNIQUE parcial `(sala_id, data, horario_id) WHERE status='ativa'`: exige uma linha por aula (rejeitado no ADR-0002)
   e não detecta sobreposição se a grade mudar.
2. Lock pessimista (`SELECT ... FOR UPDATE` na sala / advisory lock): funciona, mas depende de todo código
   lembrar do lock.
3. **Constraint de exclusão do PostgreSQL sobre intervalo de tempo.**

## Decisão
Opção 3, mais validação no service:
```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
-- em reservas:
periodo tsrange GENERATED ALWAYS AS (tsrange(data + inicio, data + fim, '[)')) STORED,
CONSTRAINT ex_reservas_sem_sobreposicao
    EXCLUDE USING gist (sala_id WITH =, periodo WITH &&) WHERE (status = 'ativa')
```
- Intervalo semiaberto `[)`: aulas encostadas (08:20 fim / 08:20 início) não conflitam.
- `btree_gist` permite `=` em inteiro dentro de índice GiST.
- O service faz a checagem antes (para listar os conflitos com mensagem amigável) e trata a violação
  `23P01` / `ex_reservas_sem_sobreposicao` como o mesmo `409 CONFLITO_RESERVA`.
- Recorrência: todas as ocorrências numa única transação; uma violação desfaz tudo.
- Cancelar (`status → 'cancelada'`) tira a linha do predicado e libera o horário automaticamente.

## Consequências
- Integridade garantida mesmo com concorrência e com inserções fora da API.
- Exige PostgreSQL (não roda em SQLite); os testes usam Postgres real.
- A mesma técnica é usada para impedir semestres sobrepostos (`daterange`).
