# 17: Agenda (FullCalendar mês, semana e dia)

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.11, §4.10 (`GET /reservas`); GLOSSARY (dia da semana)

## Critérios de aceite
- [ ] Só plugins gratuitos: `daygrid`, `timegrid`, `interaction`; locale pt-br.
- [ ] Busca por `de`/`ate` a partir do intervalo visível (`ate = end - 1 dia`), filtro opcional por ambiente.
- [ ] Evento mostra ambiente, horário e nome do professor; cor por ambiente ou tipo.
- [ ] Clicar num dia vazio (logado) abre o modal de reserva com a data; clicar num evento mostra detalhes e, se `pode_cancelar`, botão cancelar.
- [ ] `slotMinTime`/`slotMaxTime` derivados de `GET /horarios`.
