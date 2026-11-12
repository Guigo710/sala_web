# 43: Postgres publicado em todas as interfaces com a senha de exemplo

Status: ready-for-agent
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
- [ ] `docker compose up` → `ss -ltn` mostra a 5432 só em `127.0.0.1`.
- [ ] Backend no Compose continua conectando ao `db`.
