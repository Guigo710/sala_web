# 63: Pool de conexões e fuso adequados ao Neon (SSL, banco que suspende)

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: alta
Blocked by: (nenhum)
Referências: ADR-0009 ("Conexão com o Neon"); `backend/app/core/db.py`; `backend/alembic/env.py`;
`backend/app/core/config.py`

## Contexto
No Neon: conexão só com SSL (`sslmode=require` na URL); o banco suspende após alguns minutos sem uso e derruba as
conexões ociosas; acordar leva de centenas de ms a poucos segundos. Usaremos a **conexão direta** (não a do pooler
PgBouncer). Hoje o `db.py` usa só `pool_pre_ping=True` e define o fuso pelo parâmetro de inicialização
`options=-c timezone=...`, que nem todo intermediário aceita (PgBouncer, por exemplo, recusa `options`).

## O que fazer
1. Engine com valores por variável de ambiente (padrões entre parênteses):
   - `DB_POOL_TAMANHO` (5) → `pool_size`; `DB_POOL_EXTRA` (5) → `max_overflow`;
   - `DB_POOL_RECICLAR_S` (240) → `pool_recycle` (menor que os ~5 min de suspensão do Neon);
   - `pool_pre_ping=True` (manter); `pool_timeout=30`;
   - `connect_args`: `connect_timeout` = `DB_CONEXAO_TIMEOUT_S` (10), `application_name="sala_web"`.
2. **Fuso**: trocar `options=-c timezone=...` por `SET TIME ZONE` num listener `@event.listens_for(engine, "connect")`
   (com o valor de `TZ` passado como parâmetro/literal seguro). O comportamento visto pela API não muda
   (timestamptz volta em `America/Sao_Paulo`).
3. `alembic/env.py`: mesma URL; conferir que roda com `sslmode=require` (sem pool persistente: `NullPool` está bom).
4. Não logar a `DATABASE_URL` (tem senha). Se a conexão falhar ao iniciar, a mensagem pode citar só o host.
5. `.env.example`: as novas variáveis comentadas, com os padrões, e um exemplo comentado de URL do Neon:
   `# DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.

## Critérios de aceite
- [ ] Testes de fuso/horários existentes verdes (o `SET TIME ZONE` substitui o `options` sem mudar respostas).
- [ ] Contra um Postgres local com SSL ligado (ex.: `postgres:16` com `-c ssl=on` e certificado autoassinado),
      `DATABASE_URL=...?sslmode=require` → `alembic upgrade head`, seed e `/saude` funcionam.
- [ ] Simulação de banco "suspenso": com a API no ar, reiniciar o container do Postgres; a próxima requisição
      responde normalmente (pre-ping reconecta), sem `500`.
- [ ] Banco fora do ar: `/saude` responde `503` em no máximo ~`DB_CONEXAO_TIMEOUT_S` + 1 s (não fica pendurado).
- [ ] Nenhum log contém a senha do banco.
