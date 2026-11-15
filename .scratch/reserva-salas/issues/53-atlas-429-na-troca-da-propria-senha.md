# 53: Registrar no contrato o `429 MUITAS_TENTATIVAS` de `PUT /auth/me/senha`

Status: ready-for-agent
Responsável: Atlas
Origem: Forge
Prioridade: baixa
Blocked by: (nenhum)
Referências: ticket 50; ADR-0007; `docs/api-contrato.md` §4.2 (`PUT /auth/me/senha`);
`backend/app/core/seguranca.py` (`LimiteTrocaSenha`); `backend/app/services/auth.py` (`trocar_senha`)

## Contexto
O ticket 50 pediu limite de tentativas da `senha_atual` e "Atlas registra o `429` em §4.2 do contrato". O Forge
implementou assim (sem editar o contrato):

- 5 `SENHA_ATUAL_INCORRETA` da mesma conta (chave = id do professor, vale para qualquer token da conta) em 5 min
  bloqueiam a troca por 5 min;
- bloqueado → `429 MUITAS_TENTATIVAS` antes de conferir a senha (mesmo com a senha certa), mesmo envelope do login:
  `{"detail": "Muitas tentativas de troca de senha. Aguarde 5 minutos e tente novamente.", "codigo": "MUITAS_TENTATIVAS"}`;
- troca certa zera o contador; em memória, por processo, como o ADR-0007; independente do limite do login.

## O que fazer
- Em §4.2, `PUT /auth/me/senha`: acrescentar `429 MUITAS_TENTATIVAS` aos erros, com a regra acima.
- Decidir se o ADR-0007 ganha um adendo (ou se basta a referência ao ticket 50).
- Decidir a opção "mais forte" do ticket 50: revogar as sessões da conta ao estourar o limite. Não implementada,
  porque derruba também a sessão do dono e mudaria o comportamento documentado; se aprovada, abrir ticket ao Forge.
