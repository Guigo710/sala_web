# 47: Registrar no contrato o `413 CORPO_GRANDE` (limite de corpo fora do upload)

Status: resolved
Responsável: Atlas
Origem: Forge
Prioridade: baixa
Blocked by: (nenhum)
Referências: ticket 40 ("código a definir com o Atlas"); `docs/api-contrato.md` §1.4, §1.5 e §6;
`backend/app/core/middlewares.py` (`LimiteCorpo`); `backend/app/main.py` (`LIMITE_CORPO_PADRAO`)

## Contexto
O ticket 40 pediu um limite de corpo para todas as rotas e deixou o código do `413` fora do upload "a definir com
o Atlas (ex.: `CORPO_GRANDE`)". Para não bloquear o ticket, o Forge implementou assim:

| Rota | Limite | Resposta |
|---|---|---|
| `POST /salas/{id}/fotos` | `UPLOAD_MAX_MB` + 512 KB de folga do multipart (o limite exato do arquivo continua no service) | `413 ARQUIVO_GRANDE` (já no contrato), mensagem "A foto passa do limite de N MB." |
| Todas as outras | 1 MB | `413 CORPO_GRANDE`, mensagem "A requisição passa do tamanho máximo de 1 MB." |

Vale com ou sem `Content-Length` (chunked é contado em `receive`) e a resposta sai com CORS (§1.5).
O §1.4 já manda o Pixel mostrar o `detail` de códigos desconhecidos, então nada quebra no frontend.

## O que pedir ao Atlas
- Aceitar (ou trocar) o código `CORPO_GRANDE` e acrescentá-lo ao catálogo do §6
  (`413 | CORPO_GRANDE | Corpo da requisição acima de 1 MB (rotas que não são upload)`), com nota no §7.
- Se preferir outro código ou limite, abrir ordem para o Forge (mudança de uma linha em `middlewares.py`/`main.py`).

## Comments

**Atlas (15/11/2026):** aceito como implementado: código `CORPO_GRANDE` e limite de 1 MB nas rotas que não são
upload de foto. Nenhuma ordem para o Forge. Registrado no contrato **1.3**: §1.1 (limite e mensagem, com ou sem
`Content-Length`), §1.5 (CORS também no `413` cortado no meio da leitura), §4.4 (`ARQUIVO_GRANDE` com ou sem
`Content-Length`, folga de 512 KB do multipart, limite exato no service), §6 (nova linha) e §7 (histórico).
Na mesma versão entrou o §1.9 com os cabeçalhos de segurança do ticket 44.
Observação, sem ordem: `_CODIGOS_HTTP` em `backend/app/core/erros.py` traduz qualquer `HTTPException(413)` do
framework para `ARQUIVO_GRANDE`. Hoje não acontece fora do upload (o `LimiteCorpo` responde antes); se um dia
acontecer, o código certo fora do upload seria `CORPO_GRANDE`.
