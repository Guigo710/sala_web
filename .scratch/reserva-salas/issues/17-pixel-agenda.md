# 17: Agenda (FullCalendar mês, semana e dia)

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.11, §4.10 (`GET /reservas`); GLOSSARY (dia da semana)

## Critérios de aceite
- [x] Só plugins gratuitos: `daygrid`, `timegrid`, `interaction`; locale pt-br.
- [x] Busca por `de`/`ate` a partir do intervalo visível (`ate = end - 1 dia`), filtro opcional por ambiente.
- [x] Evento mostra ambiente, horário e nome do professor; cor por ambiente ou tipo.
- [x] Clicar num dia vazio (logado) abre o modal de reserva com a data; clicar num evento mostra detalhes e, se `pode_cancelar`, botão cancelar.
- [x] `slotMinTime`/`slotMaxTime` derivados de `GET /horarios`.

## Comments

**Pixel (2026-11-12):** `/agenda`: FullCalendar (daygrid, timegrid, interaction) pt-br, eventos de `GET /reservas?de&ate` (`ate = end - 1 dia`), filtro por ambiente (`?sala=`), cor por tipo com legenda, slotMin/MaxTime e dias ocultos derivados de `GET /horarios`. Clique em dia (logado, não passado) abre o modal; clique em evento mostra detalhes e cancelar quando `pode_cancelar`.
