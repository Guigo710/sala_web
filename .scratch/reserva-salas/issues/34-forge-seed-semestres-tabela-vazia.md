# 34: Seed de semestres só com tabela vazia

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: baixa
Blocked by: (nenhum)
Referências: **ADR-0006**; ticket 29 (ponto 12)

## Problema
`seed_semestres` (`backend/app/seed.py:146-158`) insere, a cada start, os semestres do ano corrente e do seguinte
que ainda não existem pelo nome e não se sobrepõem a nenhum outro. Com isso:
- se o admin exclui "2027-1" (ex.: para cadastrar com outras datas depois), o restart recria o semestre;
- a cada virada de ano o seed cria semestres sozinho, o que é dado fixo no código, contra `decisoes.md`.

O ADR-0006 manda tratar semestres como as outras tabelas de partida.

## O que fazer
- `seed_semestres`: `if not _tabela_vazia(db, Semestre): return`. Com a tabela vazia, criar os semestres do ano
  corrente e do seguinte, como hoje.
- Atualizar a docstring de `seed.py:1-10` e a seção "Notas de implementação" do `backend/README.md`, incluindo as
  consequências do ADR-0006 (tabela esvaziada volta a receber os dados de partida; admin com `ADMIN_RM` excluído é recriado).

## Critérios de aceite
- [ ] Banco vazio → seed cria 4 semestres; rodar de novo não cria nada.
- [ ] Excluir um semestre de partida e rodar o seed → ele **não** volta.
- [ ] Com um semestre qualquer cadastrado pelo admin → seed não cria nenhum.
- [ ] Teste do seed cobrindo os três casos.

## Comments
