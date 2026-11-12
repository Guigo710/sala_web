# 21: Admin: ambientes, fotos, equipamentos e softwares do ambiente

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §4.3, §4.4

## Critérios de aceite
- [ ] Lista (inclui inativas), criar, editar, ativar/desativar e excluir ambiente (`409 SALA_COM_RESERVAS` sugere desativar).
- [ ] Editor de equipamentos do ambiente (quantidade, especificação) e de softwares (`PUT` substitui a lista).
- [ ] Upload de várias fotos (uma requisição por arquivo, com progresso), legenda editável, reordenar (arrastar ou setas → `PUT .../fotos/ordem`), remover com confirmação.
- [ ] Erros `413`/`415` exibidos por arquivo.
