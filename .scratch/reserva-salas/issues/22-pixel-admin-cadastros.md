# 22: Admin: equipamentos, softwares, professores, horários e semestres

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.5–§4.9

## Critérios de aceite
- [x] CRUD de equipamentos e softwares (categoria com sugestões de `/softwares/categorias`).
- [x] Professores: listar/buscar, criar (RM, nome, e-mail, senha inicial, papel), editar, ativar/desativar, redefinir senha, excluir.
- [x] Horários: tabela por turno, criar/editar com dias da semana (checkboxes seg–dom, ISO 1..7), ativar/desativar.
- [x] Semestres: criar/editar/excluir.
- [x] Todos os códigos de erro do contrato (`409`/`422`) mostrados com `detail` no formulário.

## Comments

**Pixel (2026-11-12):** Admin: equipamentos e softwares (categoria com sugestões de `/softwares/categorias`), professores (busca/filtros, criar, editar, ativar/desativar, redefinir senha, excluir com atalho para desativar), horários por turno (dias seg–dom ISO 1..7, ativar/desativar), semestres. Erros 409/422 aparecem com `detail` (e `erros`) dentro do formulário.
