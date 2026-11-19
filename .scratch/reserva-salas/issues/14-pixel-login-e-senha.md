# 14: Tela de login e troca de senha

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.2

## Critérios de aceite
- [x] Formulário RM + senha; erros `CREDENCIAIS_INVALIDAS` e `MUITAS_TENTATIVAS` mostram `detail`.
- [x] Após login, volta à página que pediu login (ou Agenda).
- [x] Tela "Minha conta" troca a senha (`PUT /auth/me/senha`), mostrando `SENHA_ATUAL_INCORRETA`.
- [x] Campos com `label`, navegáveis por teclado.

## Comments

**Pixel (2026-11-12):** `/login` (RM + senha, mostra `detail` de CREDENCIAIS_INVALIDAS/MUITAS_TENTATIVAS, volta à página de origem ou /agenda). `/minha-conta` com troca de senha (`PUT /auth/me/senha`), validação local de 8 caracteres e confirmação.
