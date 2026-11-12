# 41: Tokens antigos continuam válidos depois de trocar ou redefinir a senha

Status: needs-triage
Responsável: Forge
Origem: Sentinela
Severidade: média
Blocked by: decisão do Atlas (ADR-0004)
Referências: ticket 25; ADR-0004; `backend/app/core/seguranca.py:63-95`; `routers/auth.py:41-46`; `routers/professores.py:92-96`

## Problema
`PUT /auth/me/senha` e `PUT /professores/{id}/senha` trocam o hash, mas o JWT já emitido continua valendo até
expirar (padrão 8 h). Cenário: o professor percebe que alguém usou a conta dele (ou o admin redefine a senha de uma
conta comprometida) e quem tem o token roubado continua reservando/cancelando em nome dele pelo resto do dia.
Desativar a conta resolve (o `ativo` é lido do banco), mas troca de senha não.

## Sugestão
- Coluna `professores.senha_alterada_em` (timestamptz). Ao validar o token, rejeitar se `iat < senha_alterada_em`.
  Migration nova; sem mudança de rotas.
- Como mexe no modelo e no ADR-0004, o Atlas decide (abrir ADR curto ou anotar no ADR-0004).

## Critérios de aceite
- [ ] Token emitido antes de `PUT /auth/me/senha` → `401 NAO_AUTENTICADO` depois da troca; novo login funciona.
- [ ] Idem para `PUT /professores/{id}/senha` (redefinição pelo admin).
- [ ] Teste automatizado para os dois casos.
