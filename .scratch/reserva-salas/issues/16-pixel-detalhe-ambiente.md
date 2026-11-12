# 16: Detalhe do ambiente (galeria, equipamentos, softwares, disponibilidade do dia)

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.7, §4.3

## Critérios de aceite
- [x] Galeria com miniaturas e visualização ampliada (teclado: setas e Esc), legendas, `alt` com legenda/nome.
- [x] Tabela de equipamentos com quantidade e especificação; lista de softwares com versão e categoria.
- [x] Seletor de data mostrando `GET /salas/{id}/disponibilidade` (livre/ocupada/passou, nome do professor).
- [x] Botão "Reservar" (logado) abre o modal do ticket 18 com a sala e data preenchidas.

## Comments

**Pixel (2026-11-12):** `/ambientes/:id`: galeria com miniaturas e visualização ampliada (setas, Esc, alt com legenda), tabela de equipamentos, softwares com versão/categoria, seletor de data com `GET /salas/{id}/disponibilidade` (livre/ocupada com professor/já passou), botão Reservar abre o modal com sala e data.
