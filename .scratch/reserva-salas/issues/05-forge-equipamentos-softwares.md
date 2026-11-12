# 05: CRUD de equipamentos e softwares

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 03
Referências: `docs/api-contrato.md` §4.5, §4.6

## Critérios de aceite
- [ ] Todas as rotas de §4.5 e §4.6 com os acessos e códigos do contrato.
- [ ] `GET /softwares/categorias` devolve categorias distintas, não nulas, ordenadas.
- [ ] Nome duplicado → `409 NOME_DUPLICADO` (softwares: mesmo nome+versão, inclusive versão nula).
- [ ] Excluir equipamento/software remove as associações com salas (`204`).
