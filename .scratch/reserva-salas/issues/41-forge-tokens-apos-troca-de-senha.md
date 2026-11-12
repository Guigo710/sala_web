# 41: Tokens antigos continuam válidos depois de trocar ou redefinir a senha

Status: ready-for-agent
Responsável: Forge
Origem: Sentinela
Severidade: média
Blocked by: (nenhum; decidido no ADR-0008)
Referências: ticket 25; ADR-0004; **ADR-0008**; contrato 1.2 (§2, §1.3, §4.2, §4.7, §7); ticket 46 (Pixel, muda junto);
`backend/app/core/seguranca.py:63-95`; `routers/auth.py:41-46`; `routers/professores.py:92-96`

## Problema
`PUT /auth/me/senha` e `PUT /professores/{id}/senha` trocam o hash, mas o JWT já emitido continua valendo até
expirar (padrão 8 h). Cenário: o professor percebe que alguém usou a conta dele (ou o admin redefine a senha de uma
conta comprometida) e quem tem o token roubado continua reservando/cancelando em nome dele pelo resto do dia.
Desativar a conta resolve (o `ativo` é lido do banco), mas troca de senha não; e reativar a conta revive tokens antigos.

## Decisão (Atlas, ADR-0008)
Contador `professores.token_versao` copiado para a claim `ver` do JWT; incrementar revoga todas as sessões da conta.
Escolhido em vez de `senha_alterada_em` porque `iat` tem resolução de segundos (token emitido no mesmo segundo da
troca fica ambíguo) e porque o contador também cobre papel e desativação.

## O que fazer
1. Migration `0002_token_versao`: `ALTER TABLE professores ADD COLUMN token_versao integer NOT NULL DEFAULT 0`
   (com `downgrade`). Campo no model `Professor`; **não** expor em `Usuario`.
2. `criar_token`: claim `ver = professor.token_versao`.
3. Validação (`_id_do_token` / `usuario_opcional`): exigir `ver` (`options={"require": ["sub", "exp", "ver"]}`) e
   comparar com `professor.token_versao` depois de carregar o professor; diferente → mesmo tratamento de token
   inválido (visitante em rota pública, `401 NAO_AUTENTICADO` em rota protegida). Nenhuma consulta extra.
4. Incremento em um único ponto do domínio (ex.: `revogar_sessoes(professor)` → `token_versao += 1`), na mesma
   transação da mudança, chamado em:
   - `PUT /auth/me/senha`: depois de trocar o hash, incrementa, faz commit/refresh e emite token novo;
     responde **`200`** com o mesmo schema do login (`access_token`, `token_type`, `expira_em`, `usuario`).
   - `PUT /professores/{id}/senha`: incrementa; continua `204`.
   - `PUT /professores/{id}`: incrementa só se `papel` mudou ou se `ativo` passou de `true` para `false`.
5. Não incrementam: login, reativação, nome/e-mail, `PUT` sem mudança de papel/ativo, erros (`422`).
6. Atualizar o `response_model`/status de `PUT /auth/me/senha` no OpenAPI.

## Critérios de aceite
- [ ] Migration `0002` sobe e desce (`alembic upgrade head` / `downgrade -1`) num banco com dados; contas existentes ficam com `token_versao = 0`.
- [ ] Token sem claim `ver` (emitido antes da mudança) → `401 NAO_AUTENTICADO` em `GET /auth/me`; em `GET /reservas` é tratado como visitante (`pode_cancelar = false`).
- [ ] `PUT /auth/me/senha` com senha atual certa → `200` com `access_token` novo; o token novo funciona em `GET /auth/me`; o token usado na requisição e um segundo token da mesma conta (outro login) → `401`.
- [ ] `PUT /auth/me/senha` com `SENHA_ATUAL_INCORRETA` ou `VALIDACAO` → `422` e o token atual continua valendo.
- [ ] `PUT /professores/{id}/senha` pelo admin → `204`; tokens anteriores daquela conta → `401`; login com a nova senha funciona; os tokens de outras contas (inclusive o do admin, quando `{id}` não é ele) seguem valendo.
- [ ] `PUT /professores/{id}` mudando `papel` → tokens anteriores da conta → `401`. Mudando só `nome`/`email` → tokens seguem valendo.
- [ ] `PUT /professores/{id}` com `ativo` `true → false` e depois `false → true` → o token antigo continua `401` após a reativação; login novo funciona.
- [ ] Dois logins da mesma conta convivem (login não incrementa).
- [ ] Testes automatizados (pytest) para todos os itens acima.
