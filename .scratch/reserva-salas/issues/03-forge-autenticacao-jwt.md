# 03: Autenticação JWT (login, me, troca de senha, dependências de papel)

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Blocked by: 02
Referências: `docs/api-contrato.md` §1.3, §4.2; ADR-0004

## O que fazer
`POST /auth/login`, `GET /auth/me`, `PUT /auth/me/senha`; hash bcrypt; JWT HS256; dependências
`usuario_opcional`, `usuario_atual`, `exigir_admin` (recarregando o professor do banco a cada requisição);
rate limit de login em memória (5 falhas/IP/5 min → 429 por 5 min).

## Critérios de aceite
- [ ] Login correto → `200` com `access_token`, `token_type`, `expira_em`, `usuario`.
- [ ] RM inexistente, senha errada e conta inativa → `401 CREDENCIAIS_INVALIDAS` com a mesma mensagem.
- [ ] Token expirado/adulterado em rota protegida → `401 NAO_AUTENTICADO`; em rota pública, ignorado.
- [ ] Conta desativada após o login perde acesso no próximo request (`401`).
- [ ] Professor em rota admin → `403 SEM_PERMISSAO`.
- [ ] 6ª falha seguida do mesmo IP → `429 MUITAS_TENTATIVAS`.
- [ ] `PUT /auth/me/senha` com senha atual errada → `422 SENHA_ATUAL_INCORRETA`; certa → `204` e a nova senha funciona.
