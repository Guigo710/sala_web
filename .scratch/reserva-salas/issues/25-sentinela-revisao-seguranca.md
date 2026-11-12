# 25: Revisão de segurança da v1

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 12, 07
Referências: ADR-0004, ADR-0005; `docs/api-contrato.md` §1.3–§1.5

## Critérios de aceite
- [x] Checklist revisado: segredo JWT do ambiente e validade, bcrypt, RM sempre do token, `exigir_admin` em toda rota admin, CORS restrito, upload (magic bytes, tamanho, path traversal), SQL injection (sem SQL concatenado), erros 500 sem stack trace, `.env` fora do git, XSS no frontend (sem `dangerouslySetInnerHTML`).
- [x] Achados registrados como tickets novos `Responsável: Forge|Pixel`, `Origem: Sentinela`, com severidade.

## Comments

**Sentinela (12/11/2026):** revisão feita; achados em tickets 40–45.

| Item | Resultado |
|---|---|
| Segredo JWT do ambiente | OK (`JWT_SECRET` obrigatório, ≥ 16). **Corrigido**: o valor de exemplo do `.env.example` agora impede a API de subir (`app/core/config.py`) — cobre o item 3 do ticket 36. |
| Validade/algoritmo do JWT | OK: HS256 fixo, `exp`/`sub` exigidos, 480 min; `alg=none`, HS512, segredo errado e adulterado → 401 (testado). |
| Hash de senha | OK: bcrypt, tempo constante para RM inexistente. Corte em 72 bytes (limite do bcrypt) aceito. |
| Tokens após troca de senha | **Achado**: continuam válidos até expirar → ticket 41 (média). |
| RM sempre do token | OK (professor com `professor_id` → 403; testado). |
| `exigir_admin` em toda rota admin | OK: matriz §5 testada rota a rota. |
| CORS | OK: só `CORS_ORIGENS`, sem credentials. Erros 413/500 sem CORS já estão no ticket 30 (Atlas). |
| Upload | OK: magic bytes, limite em blocos, nome UUID, `caminho_absoluto` impede escape. **Achado**: corpo sem `Content-Length` (chunked) e JSON gigante são lidos inteiros antes da autenticação → ticket 40 (média). Poliglota servido sem `nosniff` → ticket 44 (baixa). |
| SQL injection | OK: só ORM/parametrizado; `ILIKE` escapado (testado). |
| Erros 500 | OK: envelope genérico, sem stack trace (testado). |
| `.env` fora do git | OK (`.gitignore`; nenhum `.env` no histórico). **Corrigido**: seed não cria admin com a `ADMIN_SENHA` de exemplo. **Achado**: Postgres publicado em `0.0.0.0` com senha de exemplo → ticket 43 (média). |
| XSS no frontend | OK: sem `dangerouslySetInnerHTML`/`innerHTML`/`eval`; redirect pós-login vem de `location.state`. Mock fora do build (conferido no `dist`). |
| Rate limit de login | Funciona (testado); o problema do IP compartilhado já está no ticket 31 (Atlas). |
| Frontend em produção | **Achado**: imagem roda o dev server do Vite → ticket 42 (média). |
| Dependências | **Achado**: `npm audit` (react-router open redirect; vitest/tinypool só dev) → ticket 45 (baixa). |
| Cabeçalhos de segurança | **Achado**: sem `nosniff`/`X-Frame-Options` → ticket 44 (baixa). |
