# 16: Detalhe do ambiente (galeria, equipamentos, softwares, disponibilidade do dia)

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.7, §4.3

## Critérios de aceite
- [ ] Galeria com miniaturas e visualização ampliada (teclado: setas e Esc), legendas, `alt` com legenda/nome.
- [ ] Tabela de equipamentos com quantidade e especificação; lista de softwares com versão e categoria.
- [ ] Seletor de data mostrando `GET /salas/{id}/disponibilidade` (livre/ocupada/passou, nome do professor).
- [ ] Botão "Reservar" (logado) abre o modal do ticket 18 com a sala e data preenchidas.
