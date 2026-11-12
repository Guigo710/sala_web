# 22: Admin: equipamentos, softwares, professores, horários e semestres

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.5–§4.9

## Critérios de aceite
- [ ] CRUD de equipamentos e softwares (categoria com sugestões de `/softwares/categorias`).
- [ ] Professores: listar/buscar, criar (RM, nome, e-mail, senha inicial, papel), editar, ativar/desativar, redefinir senha, excluir.
- [ ] Horários: tabela por turno, criar/editar com dias da semana (checkboxes seg–dom, ISO 1..7), ativar/desativar.
- [ ] Semestres: criar/editar/excluir.
- [ ] Todos os códigos de erro do contrato (`409`/`422`) mostrados com `detail` no formulário.
