# 32: `ativo` obrigatório no PUT de salas e horários

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: média
Blocked by: (nenhum)
Referências: `docs/api-contrato.md` §1.6, §4.3 (`PUT /salas/{id}`), §4.8 (`PUT /horarios/{id}`); ticket 29 (ponto 4)

## Problema
O `POST` e o `PUT` usam o mesmo schema, com `ativo: bool = True`:
- `SalaEntrada` (`backend/app/schemas/salas.py:16-22`), usado em `routers/salas.py:89` e `:98`;
- `HorarioEntrada` (`backend/app/schemas/horarios.py:10-16`), usado em `routers/horarios.py:89` e `:97`.

Um `PUT` que esquece `ativo` **reativa** um ambiente ou uma aula desativados. O contrato 1.1 (§1.6) passa a exigir
`ativo` no `PUT`. O Pixel já envia sempre o campo (`frontend/src/utils/salas.js:10`,
`frontend/src/pages/admin/AdminHorarios.jsx:32`), então a mudança não quebra o frontend.

## O que fazer
- Criar `SalaAtualizar` e `HorarioAtualizar`: os mesmos campos, mas com `ativo: bool` obrigatório. Herdar do
  schema de entrada e sobrescrever só `ativo`, para não duplicar validações.
- Usar os novos schemas nos dois `PUT`. O `POST` não muda (padrão `true`).

## Critérios de aceite
- [ ] `PUT /salas/{id}` sem `ativo` → `422 VALIDACAO`, com `erros[0].campo == "body.ativo"`; com `ativo` funciona como antes.
- [ ] `PUT /horarios/{id}` sem `ativo` → idem.
- [ ] `POST /salas` e `POST /horarios` sem `ativo` continuam criando com `ativo = true`.
- [ ] O OpenAPI (`/docs`) mostra `ativo` como obrigatório nos dois `PUT`.
- [ ] Teste cobrindo os quatro casos.

## Comments
