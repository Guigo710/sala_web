# 51: Container do backend roda como root

Status: resolved
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
- [x] `docker compose exec backend id` → uid diferente de 0.
- [x] Upload de foto pelo Compose continua funcionando (volume novo e volume antigo depois do `chown`).
- [x] Migrations e seed continuam rodando no `CMD`.

## Resolução (Forge, rodada 4)
- `backend/Dockerfile`: grupo/usuário de sistema `app` com uid/gid fixos `10001`, `chown app:app /app/uploads`
  e `USER 10001:10001` antes do `CMD` (o código em `/app` continua de root, só leitura para `app`).
- `docker-compose.yml`: serviço `uploads-permissoes` (imagem `python:3.12-slim`, a mesma base, como root) monta o
  volume `uploads` e faz `find /app/uploads ! -user 10001 -exec chown 10001:10001 {} +`; o backend depende dele
  com `service_completed_successfully`. Assim volumes antigos criados por root são corrigidos sem passo manual
  (o `chown` manual ficou documentado no `backend/README.md` como alternativa). Volumes e projeto não renomeados.
- Conferido com a imagem construída, num projeto Compose de teste: `docker compose exec backend id` →
  `uid=10001(app)`; migrations + seed rodaram no `CMD`; volume antigo (pasta e foto criadas por root) passou a
  10001 e o upload deu `201`; com volume novo, upload `201` e `GET /uploads/...` `200`.
