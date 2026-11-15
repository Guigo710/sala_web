# 34: Seed de semestres só com tabela vazia

Status: resolved
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
- [x] Banco vazio → seed cria 4 semestres; rodar de novo não cria nada.
- [x] Excluir um semestre de partida e rodar o seed → ele **não** volta.
- [x] Com um semestre qualquer cadastrado pelo admin → seed não cria nenhum.
- [x] Teste do seed cobrindo os três casos.

## Comments

**Forge (15/11/2026):** feito (ADR-0006). `seed_semestres` só roda com a tabela vazia; docstring de `app/seed.py` e "Notas de implementação" do `backend/README.md` atualizadas (tabela esvaziada recebe de novo os dados de partida; admin de `ADMIN_RM` excluído é recriado). Testes em `tests/test_ordens_atlas_rodada3.py`: banco vazio → 4 semestres e nada na segunda vez; semestre excluído não volta; semestre do admin impede o seed.
