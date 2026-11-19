# 07: Fotos: upload, listagem, legenda, reordenação e remoção

Status: resolved
Responsável: Forge
Origem: Atlas
Blocked by: 06
Referências: `docs/api-contrato.md` §4.4; ADR-0005

## Critérios de aceite
- [ ] Upload `multipart` (`arquivo`, `legenda`) só admin; salva em `UPLOAD_DIR/salas/{id}/{uuid}.{ext}`; nome original ignorado.
- [ ] Tipo verificado pelos magic bytes (JPEG/PNG/WebP); um `.jpg` que é texto → `415 TIPO_ARQUIVO_INVALIDO`.
- [ ] Acima de `UPLOAD_MAX_MB` → `413 ARQUIVO_GRANDE`, sem deixar arquivo parcial no disco.
- [ ] `url` devolvida abre a imagem via `GET /uploads/...`.
- [ ] `PUT /salas/{id}/fotos/ordem` exige exatamente os ids da sala → senão `422 ORDEM_FOTOS_INVALIDA`.
- [ ] `DELETE` remove registro e arquivo; foto de outra sala → `404`.

## Comments

- **Forge (2026-11-12):** `routers/fotos.py`, `services/arquivos.py`. Verificado: upload PNG/JPEG, texto .jpg → 415, > 5 MB → 413 sem arquivo no disco, nome original ignorado, `/uploads/...` serve, reordenação 422, exclusão apaga arquivo. Middleware recusa cedo por `Content-Length`.
