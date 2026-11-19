# ADR-0008: Revogação de tokens por versão na conta (`token_versao`)

Status: aceito · Data: 2026-11-12 · Autor: Atlas · Origem: ticket 41 (Sentinela) · Complementa o ADR-0004

## Contexto
O ADR-0004 emite JWT sem estado (8 h) e relê o professor do banco a cada requisição, o que já resolve conta
desativada e papel (vale o do banco). Mas trocar ou redefinir a senha não invalida tokens já emitidos: quem roubou
um token continua agindo em nome do professor até o token expirar. Reativar uma conta também "ressuscita" os
tokens antigos dela, ainda não vencidos.

Opções consideradas:
1. **`senha_alterada_em` (timestamptz)** comparada com `iat`. `iat` tem resolução de segundos: um token emitido no
   mesmo segundo da troca fica ambíguo (o novo token devolvido pela troca pode ser recusado, ou um antigo aceito).
   Também só cobre senha, não papel/desativação.
2. **Lista de tokens revogados (`jti`)**: exige tabela nova, limpeza e consulta extra. Demais para a v1.
3. **Contador inteiro na conta, copiado para uma claim**: comparação exata, um único `UPDATE` revoga tudo, e o
   professor já é lido do banco em toda requisição (custo zero de consulta).

## Decisão
- Coluna `professores.token_versao integer NOT NULL DEFAULT 0` (migration nova `0002`).
- O JWT ganha a claim **`ver`** (inteiro) = `token_versao` no momento da emissão. Na validação, `ver` é
  obrigatória; token sem `ver` ou com `ver != professor.token_versao` é inválido (→ visitante nas rotas públicas,
  `401 NAO_AUTENTICADO` nas protegidas, como qualquer token inválido).
- Incrementar a versão (`token_versao = token_versao + 1`, na mesma transação da mudança) derruba **todas** as
  sessões da conta. Incrementa quando:

| Evento | Rota | Incrementa? | Sessão de quem fez a ação |
|---|---|---|---|
| Troca da própria senha | `PUT /auth/me/senha` | sim | recebe **token novo** na resposta (`200`, mesmo corpo do login); as outras sessões caem |
| Redefinição pelo admin | `PUT /professores/{id}/senha` | sim | `204`; se o admin redefinir a **própria** senha por esta rota, a sessão dele também cai (deve entrar de novo) |
| Mudança de `papel` | `PUT /professores/{id}` com `papel` diferente do atual | sim | não se aplica (admin não pode mudar o próprio papel: `OPERACAO_EM_SI_MESMO`) |
| Desativação | `PUT /professores/{id}` com `ativo` de `true` para `false` | sim | não se aplica (admin não pode se desativar) |
| Reativação, nome, e-mail, `PUT` sem mudança de papel/ativo | `PUT /professores/{id}` | não | |
| Login | `POST /auth/login` | não (logins em vários dispositivos convivem) | |

- Papel continua valendo do banco (ADR-0004); incrementar na mudança de papel serve para encerrar sessões cujo
  frontend guardou o papel antigo (menus de admin) e obrigar um login limpo.
- Desativar já bloqueava pelo `ativo`; incrementar garante que reativar a conta não revive tokens antigos.

## Consequências
- Na implantação, os tokens emitidos antes (sem `ver`) passam a ser recusados: todos entram de novo uma vez. Aceito.
- `PUT /auth/me/senha` muda de `204` para `200` com o mesmo corpo do `POST /auth/login` (contrato 1.2): Forge e Pixel mudam juntos.
- Não há "sair de todos os dispositivos" isolado nem logout no servidor; trocar a senha cumpre esse papel na v1.
- Segue sem refresh token; nada muda no `localStorage`.
- Implementação: ticket 41 (Forge) e ticket 46 (Pixel). Revisão: Sentinela.
