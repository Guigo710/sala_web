# ADR-0006: Seed só preenche tabela vazia, nunca atualiza nem apaga

Status: aceito · Data: 2026-11-12 · Autor: Atlas · Origem: ticket 29 (ponto 12)

## Contexto
O seed (`python -m app.seed`) roda a **cada start** do container backend (ADR-0001). O ticket 04 pedia
"só insere o que não existe, por chave natural". Com chave natural, se o admin renomeia "Sala 01" para
"Sala Maker" ou a exclui, o próximo restart recria "Sala 01". Isso contraria `decisoes.md`: tudo é editável
pelo admin e o seed é só ponto de partida.

Alternativas consideradas:
1. Chave natural (nome): desfaz renomeações e exclusões do admin a cada restart.
2. Migration de dados no Alembic (roda uma vez por banco): garante "uma vez só", mas mistura dados de
   exemplo com o esquema e polui o banco de testes, que é recriado com Alembic a cada execução.
3. **Seed por tabela: insere os dados de partida só quando a tabela está vazia.**

## Decisão
Opção 3, com estas regras:
- **Admin inicial**: criado a partir de `ADMIN_RM`/`ADMIN_SENHA`/`ADMIN_NOME` se não existir conta com esse RM.
  Uma conta existente nunca é alterada (senha, papel e `ativo` ficam como o admin deixou).
- **Equipamentos, softwares, ambientes (com suas associações), grade de aulas e semestres**: cada tabela
  recebe os dados de partida **somente se estiver vazia**.
- O seed **nunca** atualiza nem apaga linhas.
- Semestres de partida: os dois do ano corrente e os dois do seguinte, gerados na primeira execução.
  Daí em diante o admin cadastra os semestres novos.

## Consequências
- Edições do admin sobrevivem a restarts.
- Se o admin esvaziar uma tabela inteira (ex.: apagar todos os equipamentos), o próximo restart recoloca
  os dados de partida daquela tabela. Comportamento aceito e documentado no README do backend.
- Excluir a conta do admin inicial com `ADMIN_RM` ainda definido faz o restart recriá-la. Isso serve de
  recuperação de acesso; para impedir, retire `ADMIN_RM`/`ADMIN_SENHA` do `.env`.
- Implementação: ticket 34 (semestres passam a seguir a mesma regra das demais tabelas).
