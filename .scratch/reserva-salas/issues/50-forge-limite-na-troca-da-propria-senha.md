# 50: Sem limite de tentativas na senha atual de `PUT /auth/me/senha`

Status: resolved
Responsável: Forge
Origem: Sentinela
Severidade: baixa
Blocked by: (nenhum)
Referências: ADR-0007 (limite de login); ADR-0008 (revogação); `backend/app/services/auth.py` (`trocar_senha`);
`backend/app/core/seguranca.py` (`LimiteLogin`)

## Problema
O limite de tentativas (ADR-0007) só vale para `POST /auth/login`. Em `PUT /auth/me/senha` a `senha_atual` pode ser
chutada sem limite por quem tem o token. Medido contra o uvicorn real (rodada 3):

```
30 chutes de senha_atual com o token de um professor → 30 × 422 SENHA_ATUAL_INCORRETA em 9,4 s (nenhum 429)
chute certo logo depois                              → 200, token novo; todos os outros tokens da conta → 401
```

Cenário: alguém pega o token de um professor (computador do laboratório com a sessão aberta, `localStorage`).
Hoje esse acesso termina quando o token expira (8 h). Com chutes ilimitados da senha atual, o atacante pode
acertá-la, trocar a senha e ficar com a conta de vez, derrubando a sessão do dono (ADR-0008). Só faz sentido com
senhas fracas, mas não há nada que freie o ataque.

## O que fazer
- Contar as falhas de `SENHA_ATUAL_INCORRETA` por conta (ex.: reaproveitar `_Contador` com chave
  `("troca", professor.id)`, 5 falhas em 5 min).
- Ao estourar: `429 MUITAS_TENTATIVAS` antes de conferir a senha. Opcional e mais forte: revogar as sessões da
  conta (`revogar_sessoes`), já que o token em uso provavelmente não é do dono.
- Acerto zera o contador. Atlas registra o `429` em §4.2 do contrato.

## Critérios de aceite
- [x] 5 `senha_atual` erradas seguidas → a 6ª tentativa (mesmo certa) → `429 MUITAS_TENTATIVAS`.
- [x] Outra conta não é afetada; o limite vence depois da janela.
- [x] Teste pytest com relógio falso (como em `tests/test_limite_login.py`).

## Resolução (Forge, rodada 4)
- `app/core/seguranca.py`: `LimiteTrocaSenha` (reaproveita `_Contador` do ADR-0007, chave `("troca", professor.id)`,
  `MAX_FALHAS_TROCA = 5`, janela e bloqueio de 5 min, relógio trocável) e a instância `limite_troca_senha`.
- `app/services/auth.py` (`trocar_senha`): bloqueado → `429 MUITAS_TENTATIVAS` antes de conferir a senha, com o mesmo
  envelope (`{"detail", "codigo"}`) do login; `SENHA_ATUAL_INCORRETA` registra falha; acerto zera.
- Não revoga as sessões ao estourar (opção "mais forte" fica para decisão do Atlas, ticket 53).
- Testes: `tests/test_limite_troca_senha.py` (10, relógio falso); `conftest.py` limpa o contador entre testes.
- Conferido também contra o container: 5 × `422`, depois `429` mesmo com a senha certa.
- Contrato §4.2 ainda não lista o `429` desta rota: ticket 53 (Atlas).
