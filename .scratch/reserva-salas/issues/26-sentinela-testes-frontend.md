# 26: Testes frontend (Vitest + Testing Library)

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 14, 18, 19, 20
Referências: tickets 13–22

## Critérios de aceite
- [x] Cliente da API: Bearer enviado, parse do envelope de erro, 401 limpa sessão.
- [x] Login (sucesso/erro), modal de reserva (bloqueia aulas não seguidas, mostra conflitos), prévia de recorrência (desmarcar, só livres), Minhas reservas (cancelar).
- [x] Utilitário de dia da semana ISO ↔ FullCalendar.
- [x] `npm test` verde.

## Comments

**Sentinela (12/11/2026):** feito. `npm test` → 6 arquivos, 40 testes verdes.
- `src/api/cliente.test.js` (+4): sem token não manda `Authorization`, `erros` do 422, `SEM_CONEXAO`, corpo não-JSON, 401 de visitante não encerra sessão.
- `src/auth/AuthContext.test.jsx` (7): login sucesso (sessão salva, volta para a rota protegida), 401 e 429 no login,
  restauração por `GET /auth/me`, token vencido não é enviado, **401 em rota protegida limpa a sessão e leva ao login**,
  401 na verificação inicial só limpa.
- `src/components/ModalReserva.test.jsx` (8): bloqueia aulas não seguidas (preenche o caminho, troca de turno recomeça,
  ocupada interrompe), 409 mostra conflitos e recarrega a disponibilidade, prévia (conflito desabilitado, desmarcar,
  "marcar todas as livres", envia só as livres selecionadas), conflito na confirmação refaz a prévia, `SEM_SEMESTRE`.
- `src/pages/MinhasReservas.test.jsx` (5): cancelar com motivo, `RESERVA_JA_INICIADA`, cancelar recorrência, filtros.
- Utilitário ISO ↔ FullCalendar já coberto em `src/utils/datas.test.js` (Pixel).
- Apoio: `src/testes/render.jsx`. `vite.config.js` restringe o Vitest a `src/**/*.test.{js,jsx}` (o `e2e/` é do Playwright).
