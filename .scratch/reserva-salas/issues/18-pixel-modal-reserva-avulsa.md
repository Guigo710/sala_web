# 18: Modal de reserva avulsa (aulas seguidas)

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 16, 17
Referências: `docs/api-contrato.md` §4.10 (`POST /reservas`), §4.3 (disponibilidade)

## Critérios de aceite
- [ ] Escolhe ambiente, data, turno e aulas seguidas (UI impede buracos e mistura de turnos); aulas ocupadas/passadas desabilitadas usando `/salas/{id}/disponibilidade`.
- [ ] Campo observação (≤ 200). Não pede RM (vem do token).
- [ ] Admin vê seletor de professor (`professor_id`); professor não.
- [ ] `409 CONFLITO_RESERVA` mostra a lista de conflitos; demais erros mostram `detail`.
- [ ] Sucesso fecha o modal e atualiza agenda/disponibilidade.
- [ ] Opção "Repetir toda semana até o fim do semestre" leva ao fluxo do ticket 19.
