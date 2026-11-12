# 46: Usar o token novo devolvido pela troca de senha (contrato 1.2)

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Prioridade: alta (muda junto com o ticket 41: sem isto, quem troca a senha é deslogado na próxima requisição)
Blocked by: (nenhum; pode ser feito em paralelo ao 41 contra o mock)
Referências: ADR-0008; `docs/api-contrato.md` §4.2, §4.7 e §7 (1.2); ticket 41 (Forge); ticket 14;
`frontend/src/api/auth.js`, `frontend/src/auth/AuthContext.jsx`, `frontend/src/api/mock/servidor.js`

## O que muda no contrato
- `PUT /auth/me/senha` passa de `204` para **`200`** com o mesmo corpo do `POST /auth/login`
  (`access_token`, `token_type`, `expira_em`, `usuario`). O token antigo deixa de valer na hora.
- Troca/redefinição de senha, mudança de papel e desativação derrubam **todas** as sessões da conta afetada
  (`401 NAO_AUTENTICADO` na próxima requisição; o tratamento atual de 401 já leva ao login com aviso).
- `PUT /professores/{id}/senha` com o `{id}` do próprio admin logado derruba a sessão dele.

## O que fazer
1. `api/auth.js`: `trocarSenha` devolve o corpo da resposta.
2. `AuthContext`: depois de trocar a senha, gravar a sessão nova (`salvarSessao` + `definirToken` + `usuario`),
   reaproveitando o mesmo caminho do login. Mensagem de sucesso pode avisar "As outras sessões foram encerradas."
3. Admin de cadastros (redefinir senha): se o professor for o próprio usuário logado, confirmar antes
   ("Sua sessão será encerrada; para manter a sessão use Trocar minha senha") e, após o `204`, limpar a sessão e
   ir para `/login` com aviso "Senha redefinida. Entre novamente." (ou oferecer o link para a tela de troca da própria senha).
4. Mock (`api/mock/servidor.js`): `PUT /auth/me/senha` responde `200` com token novo e invalida o anterior;
   redefinição pelo admin, mudança de papel e desativação invalidam os tokens da conta (contador por conta,
   como no backend).

## Critérios de aceite
- [ ] Trocar a própria senha mantém o usuário logado; o `localStorage` guarda o token novo; a navegação seguinte não dá 401.
- [ ] Com o mock: depois da troca, o token antigo recebe `401`.
- [ ] Admin redefinindo a própria senha pela tela de cadastros é avisado e acaba na tela de login com a mensagem.
- [ ] Vitest: troca de senha grava o token novo; redefinição da própria senha pelo admin limpa a sessão.
