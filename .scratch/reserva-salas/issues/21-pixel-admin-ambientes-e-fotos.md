# 21: Admin: ambientes, fotos, equipamentos e softwares do ambiente

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.3, §4.4

## Critérios de aceite
- [x] Lista (inclui inativas), criar, editar, ativar/desativar e excluir ambiente (`409 SALA_COM_RESERVAS` sugere desativar).
- [x] Editor de equipamentos do ambiente (quantidade, especificação) e de softwares (`PUT` substitui a lista).
- [x] Upload de várias fotos (uma requisição por arquivo, com progresso), legenda editável, reordenar (arrastar ou setas → `PUT .../fotos/ordem`), remover com confirmação.
- [x] Erros `413`/`415` exibidos por arquivo.

## Comments

**Pixel (2026-11-12):** `/admin/ambientes`: lista com inativas, criar, editar, ativar/desativar (PUT completo a partir do detalhe), excluir (409 SALA_COM_RESERVAS oferece "Desativar"). Edição: dados, equipamentos (qtd + especificação, PUT da lista), softwares (PUT da lista), fotos (upload múltiplo, 1 requisição por arquivo com barra de progresso via XHR, erros 413/415 por arquivo, legenda editável, reordenar por setas → `PUT .../fotos/ordem`, remover com confirmação).
