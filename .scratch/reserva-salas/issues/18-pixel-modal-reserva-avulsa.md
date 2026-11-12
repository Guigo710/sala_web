# 18: Modal de reserva avulsa (aulas seguidas)

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 16, 17
Referências: `docs/api-contrato.md` §4.10 (`POST /reservas`), §4.3 (disponibilidade)

## Critérios de aceite
- [x] Escolhe ambiente, data, turno e aulas seguidas (UI impede buracos e mistura de turnos); aulas ocupadas/passadas desabilitadas usando `/salas/{id}/disponibilidade`.
- [x] Campo observação (≤ 200). Não pede RM (vem do token).
- [x] Admin vê seletor de professor (`professor_id`); professor não.
- [x] `409 CONFLITO_RESERVA` mostra a lista de conflitos; demais erros mostram `detail`.
- [x] Sucesso fecha o modal e atualiza agenda/disponibilidade.
- [x] Opção "Repetir toda semana até o fim do semestre" leva ao fluxo do ticket 19.

## Comments

**Pixel (2026-11-12):** `ModalReserva`: ambiente, data, aulas por turno com `SeletorAulas` (impede buracos e mistura de turnos; ocupadas/passadas desabilitadas via disponibilidade), observação ≤ 200, seletor de professor só para admin. 409 mostra conflitos e recarrega a disponibilidade; sucesso fecha e atualiza agenda/disponibilidade.
