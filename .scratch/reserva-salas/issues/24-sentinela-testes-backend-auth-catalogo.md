# 24: Testes backend: auth, permissões por rota, filtros e upload

Status: ready-for-agent
Responsável: Sentinela
Origem: Atlas
Blocked by: 03, 06, 07, 09
Referências: `docs/api-contrato.md` §1.3, §4.2–§4.9, §5

## Critérios de aceite
- [ ] Teste parametrizado da matriz §5: cada rota de escrita com visitante (401), professor (403 quando admin), admin (ok).
- [ ] Login: sucesso, senha errada, inativo, token expirado/adulterado, rate limit 429.
- [ ] Respostas públicas sem `rm`/`senha_hash`.
- [ ] Filtros de `GET /salas` (tipo, capacidade, equipamento E, software E, disponibilidade).
- [ ] Upload: tipo falso (415), grande (413), nome malicioso (`../../x.jpg`) não escapa de `UPLOAD_DIR`.
