# 51: Container do backend roda como root

Status: ready-for-agent
Responsável: Forge
Origem: Sentinela
Severidade: baixa
Blocked by: (nenhum)
Referências: ADR-0001; ADR-0005; `backend/Dockerfile`; `docker-compose.yml` (volume `uploads`)

## Problema
A imagem do backend não define `USER`. Conferido na rodada 3 (imagem construída e ligada ao `db` do Compose):
`docker exec <backend> id` → `uid=0(root)`. O processo que recebe uploads e grava em `/app/uploads` roda como
root: qualquer falha futura de leitura/escrita de arquivo (ex.: path traversal) atinge o container inteiro.

## O que fazer
- No `Dockerfile`: criar um usuário sem privilégios (ex.: `useradd --system --uid 10001 app`),
  `chown` de `/app/uploads` para ele **antes** do `USER app` (o volume nomeado novo herda o dono da pasta da imagem).
- Volumes `uploads` já existentes criados como root: documentar no README o `chown` único
  (`docker compose run --rm -u root backend chown -R app /app/uploads`).

## Critérios de aceite
- [ ] `docker compose exec backend id` → uid diferente de 0.
- [ ] Upload de foto pelo Compose continua funcionando (volume novo e volume antigo depois do `chown`).
- [ ] Migrations e seed continuam rodando no `CMD`.
