# 14: Tela de login e troca de senha

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.2

## Critérios de aceite
- [ ] Formulário RM + senha; erros `CREDENCIAIS_INVALIDAS` e `MUITAS_TENTATIVAS` mostram `detail`.
- [ ] Após login, volta à página que pediu login (ou Agenda).
- [ ] Tela "Minha conta" troca a senha (`PUT /auth/me/senha`), mostrando `SENHA_ATUAL_INCORRETA`.
- [ ] Campos com `label`, navegáveis por teclado.
