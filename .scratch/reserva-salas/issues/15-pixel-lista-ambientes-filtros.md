# 15: Lista de ambientes com filtros e disponibilidade

Status: resolved
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.6, §4.3, §4.5, §4.6, §4.8

## Critérios de aceite
- [x] Cartões com capa, nome, tipo (rótulo de `/salas/tipos`), capacidade, localização e ícones/lista de equipamentos.
- [x] Filtros: tipo (múltiplo), capacidade mínima, equipamento(s), software(s), busca; refletidos na URL.
- [x] Filtro "livre em": data + seleção de aulas seguidas (de `GET /horarios?dia_semana=`), enviando `data` e `horario_ids`.
- [x] Erros 422 do filtro de disponibilidade aparecem como mensagem, não quebram a página.
- [x] Estado vazio e carregando.

## Comments

**Pixel (2026-11-12):** `/ambientes`: cartões (capa, nome, rótulo do tipo de `/salas/tipos`, capacidade, localização, equipamentos), filtros refletidos na URL (tipo múltiplo, capacidade mínima, equipamentos, softwares, busca com atraso), "Livre em" data + aulas seguidas de `GET /horarios?dia_semana=` enviando `data` + `horario_ids`. Erros 422 viram alerta; estados vazio/carregando.
