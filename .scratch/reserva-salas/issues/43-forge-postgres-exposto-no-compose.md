# 43: Postgres publicado em todas as interfaces com a senha de exemplo

Status: resolved
Responsável: Forge
Origem: Sentinela
Severidade: média
Blocked by: (nenhum)
Referências: ticket 25; ADR-0001; `docker-compose.yml` (serviço `db`); `.env.example`

## Problema
O serviço `db` publica `"${DB_PORTA_HOST:-5432}:5432"`, ou seja, em `0.0.0.0` da máquina da escola. Quem copia o
`.env.example` sem editar sobe o banco com `POSTGRES_PASSWORD=troque-esta-senha`, e qualquer máquina da rede entra
como superusuário no banco (lê hashes, apaga reservas, cria admin). O backend não precisa da porta publicada
(usa a rede interna do Compose).

## O que fazer
- Publicar só em loopback: `"127.0.0.1:${DB_PORTA_HOST:-5432}:5432"` (continua servindo para rodar o backend fora
  do Docker na mesma máquina).
- Opcional: o backend recusar subir se a `DATABASE_URL` tiver a senha de exemplo, como já faz com o `JWT_SECRET`
  (`app/core/config.py`, ticket 25) e o seed com a `ADMIN_SENHA` de exemplo.
- Comentar no `.env.example` que a porta só é publicada no localhost.

## Critérios de aceite
- [x] `docker compose up` → `ss -ltn` mostra a 5432 só em `127.0.0.1`.
- [x] Backend no Compose continua conectando ao `db`.

## Comments

**Forge (15/11/2026):** feito. `docker-compose.yml` (serviço `db`): `"127.0.0.1:${DB_PORTA_HOST:-5432}:5432"`; comentário no `.env.example`. Opcional também feito: o backend avisa no log quando a `DATABASE_URL` usa a senha de exemplo (aviso, não recusa, para não travar quem já tem o volume criado). Verificado com `docker compose up -d db`: porta publicada como `127.0.0.1:55432->5432/tcp`; um container na rede `sala_web_default` conecta em `db:5432`. O backend em container não foi subido (o build não baixa pacotes neste ambiente); a `DATABASE_URL` dele continua com host `db`.

**Sentinela (15/11/2026, rodada 3):** verificado e fechado. `docker compose up -d db` (projeto isolado, `.env` com senha própria) → `127.0.0.1:55433->5432/tcp`. Segundo critério, que faltava: construí a imagem do backend e a rodei na rede do Compose com `DATABASE_URL` em `db:5432` → migrations, seed e `GET /saude` → `{"status":"ok"}`. Na mesma verificação: a imagem roda como root (ticket 51) e o `backend/.dockerignore` não excluía `.env` (o config lê `backend/.env`, que iria para a imagem no `COPY . .`); corrigido direto (`.env`, `.env.*`, `.ruff_cache`).
