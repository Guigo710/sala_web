# 04: Seed idempotente (admin, ambientes, grade, semestres, catálogos)

Status: resolved
Responsável: Forge
Origem: Atlas
Blocked by: 02, 03
Referências: `decisoes.md` (Domínio), `docs/api-contrato.md` §2

## O que fazer
`python -m app.seed`, rodado no start do container; só insere o que não existe (por chave natural).
- Admin a partir de `ADMIN_RM`, `ADMIN_SENHA`, `ADMIN_NOME` (se o RM não existir).
- 14 salas `Sala 01`..`Sala 14` (`tipo=sala`, capacidade 40) e 13 labs `Laboratório 01`..`Laboratório 13`
  (`lab_informatica`, capacidade 30, com Computador ×30 e Projetor ×1). Nomes genéricos, tudo editável.
- Equipamentos: Computador, Projetor, Ar-condicionado, Quadro branco, Lousa digital, Carrinho de notebooks, Caixa de som.
- Softwares de exemplo: VS Code, PostgreSQL 16, Python 3.12, LibreOffice, Git (categorias variadas), associados aos labs.
- Grade (ISO 1..7):
  - manhã (seg–sáb, `[1,2,3,4,5,6]`): 07:30–08:20, 08:20–09:10, 09:30–10:20, 10:20–11:10, 11:10–12:00
  - tarde (seg–sex): 13:00–13:50, 13:50–14:40, 14:50–15:40, 15:40–16:30, 16:30–17:20
  - noite (seg–sex): 19:00–19:50, 19:50–20:40, 20:50–21:40, 21:40–22:30
- Semestres do ano corrente e do seguinte: `AAAA-1` (1ª segunda útil de fev → 30/jun) e `AAAA-2` (1ª segunda de ago → 19/dez ou próximo).

## Critérios de aceite
- [ ] Rodar o seed duas vezes não duplica nada nem dá erro.
- [ ] Após o seed, login com `ADMIN_RM`/`ADMIN_SENHA` funciona e `GET /horarios?dia_semana=6` traz só as 5 aulas da manhã.
- [ ] Nenhum dado real de pessoas ou senhas fixas no código.

## Comments

- **Forge (2026-11-12):** `app/seed.py`. Verificado: rodar 2x não duplica; login admin funciona; `GET /horarios?dia_semana=6` traz as 5 da manhã. Política: catálogos só são semeados com a tabela vazia (não desfaz edições do admin a cada start) → ver ticket 29.
