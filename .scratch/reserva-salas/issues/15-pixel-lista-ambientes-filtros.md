# 15: Lista de ambientes com filtros e disponibilidade

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Blocked by: 13
Referências: `docs/api-contrato.md` §3.6, §4.3, §4.5, §4.6, §4.8

## Critérios de aceite
- [ ] Cartões com capa, nome, tipo (rótulo de `/salas/tipos`), capacidade, localização e ícones/lista de equipamentos.
- [ ] Filtros: tipo (múltiplo), capacidade mínima, equipamento(s), software(s), busca; refletidos na URL.
- [ ] Filtro "livre em": data + seleção de aulas seguidas (de `GET /horarios?dia_semana=`), enviando `data` e `horario_ids`.
- [ ] Erros 422 do filtro de disponibilidade aparecem como mensagem, não quebram a página.
- [ ] Estado vazio e carregando.
