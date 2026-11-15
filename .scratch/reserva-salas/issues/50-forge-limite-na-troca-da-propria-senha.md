# 50: Sem limite de tentativas na senha atual de `PUT /auth/me/senha`

Status: ready-for-agent
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
- [ ] 5 `senha_atual` erradas seguidas → a 6ª tentativa (mesmo certa) → `429 MUITAS_TENTATIVAS`.
- [ ] Outra conta não é afetada; o limite vence depois da janela.
- [ ] Teste pytest com relógio falso (como em `tests/test_limite_login.py`).
