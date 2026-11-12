# 09: Gestão de professores (admin)

Status: resolved
Responsável: Forge
Origem: Atlas
Blocked by: 03
Referências: `docs/api-contrato.md` §4.7

## Critérios de aceite
- [ ] Rotas de §4.7, todas só admin; respostas nunca contêm `senha_hash`.
- [ ] RM fora de `^[A-Za-z0-9]{3,20}$` ou senha < 8 → `422 VALIDACAO`; RM repetido → `409 RM_DUPLICADO`.
- [ ] Admin não consegue se desativar, se rebaixar nem se excluir → `422 OPERACAO_EM_SI_MESMO`.
- [ ] Excluir professor com reservas → `409 PROFESSOR_COM_RESERVAS`.
- [ ] `PUT /professores/{id}/senha` redefine a senha (`204`).

## Comments

- **Forge (2026-11-12):** `routers/professores.py`. Verificado: RM inválido 422, `RM_DUPLICADO`, `OPERACAO_EM_SI_MESMO` (desativar/rebaixar/excluir a si), exclusão sem reservas 204, redefinição 204.
