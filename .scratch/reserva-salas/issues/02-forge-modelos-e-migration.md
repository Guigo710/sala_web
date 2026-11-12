# 02: Models SQLAlchemy e migration inicial (com constraint anti-conflito)

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 01
Referências: `docs/api-contrato.md` §2; ADR-0002, ADR-0003

## O que fazer
Models SQLAlchemy 2.x (`Mapped[...]`) para todas as tabelas do §2.1 e migration Alembic `0001` que cria
`btree_gist` e as tabelas **exatamente** como no DDL (nomes de constraints iguais).

## Critérios de aceite
- [ ] `alembic upgrade head` num banco vazio cria tudo; `alembic downgrade base` desfaz.
- [ ] `reservas.periodo` é coluna gerada (`Computed`, persisted) e não é escrita pelo ORM.
- [ ] `ex_reservas_sem_sobreposicao` existe: inserir via SQL duas reservas ativas sobrepostas na mesma sala falha com SQLSTATE `23P01`; se uma estiver `cancelada`, passa; intervalos encostados (`fim = inicio`) passam.
- [ ] `ex_semestres_sem_sobreposicao`, `uq_softwares_nome_versao` (NULLS NOT DISTINCT), `uq_horarios_turno_ordem` e os CHECKs existem.
- [ ] FKs com `ON DELETE` iguais ao contrato.
