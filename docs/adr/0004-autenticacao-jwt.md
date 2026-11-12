# ADR-0004: Autenticação por RM + senha com JWT Bearer, papéis professor/admin

Status: aceito · Data: 2026-11-12 · Autor: Atlas

## Contexto
O README original sugeria o professor "informar o RM" no formulário, o que permite reservar em nome
de qualquer um. `decisoes.md` exige login com RM + senha, JWT, senhas com hash, papéis professor/admin,
contas criadas só pelo admin e RM sempre vindo do token.

## Decisão
- Uma tabela `professores` para todas as contas, com `papel` (`professor` | `admin`) e `ativo`.
- `POST /auth/login` com JSON `{rm, senha}` (não o form OAuth2) → `access_token` JWT HS256 com `sub`
  (id), `papel`, `iat`, `exp`. Segredo `JWT_SECRET` e validade `JWT_EXPIRA_MINUTOS` (padrão 480) vêm do ambiente.
- Sem refresh token: expirou, faz login de novo. Token guardado pelo frontend em `localStorage`.
- Senhas com bcrypt (`passlib[bcrypt]` ou `bcrypt` direto). Mínimo 8 caracteres.
- Dependências FastAPI: `usuario_opcional` (rotas públicas), `usuario_atual` (professor) e `exigir_admin`.
  A cada requisição o professor é recarregado do banco: conta desativada perde acesso imediatamente e
  papel vale do banco, não do token.
- Dono da reserva = usuário do token. Só admin pode informar `professor_id`.
- Login com limite simples em memória: 5 falhas por IP em 5 minutos → `429` por 5 minutos.
- Admin inicial criado pelo seed a partir de `ADMIN_RM`, `ADMIN_SENHA`, `ADMIN_NOME`.

## Consequências
- Sem autocadastro nem recuperação por e-mail: o admin redefine senhas.
- `localStorage` é vulnerável a XSS; aceitável na v1 (React escapa por padrão, sem `dangerouslySetInnerHTML`).
  Revisado por Sentinela.
- Rate limit em memória zera ao reiniciar e não funciona com vários processos; suficiente para a v1.
