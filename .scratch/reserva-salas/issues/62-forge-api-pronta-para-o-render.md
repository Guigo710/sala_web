# 62: API pronta para o Render (porta `PORT`, CORS de produção, teto de login por IP configurável)

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: alta
Blocked by: (nenhum)
Referências: ADR-0009 (seções "Porta e processo", "CORS", "Limites de tentativas em memória"); ADR-0007 adendo 2;
contrato 1.4 §1.5, §4.2; `backend/Dockerfile`; `backend/app/core/config.py` (`cors_origens`);
`backend/app/core/seguranca.py` (`MAX_FALHAS_IP`, `LimiteLogin`); `backend/app/main.py`

## Contexto
O Render define a variável `PORT` (hoje 10000) e espera a aplicação nela. A API fica atrás do balanceador do Render:
todos os clientes chegam com o mesmo `request.client.host`, o que transformaria o teto de 20 falhas por IP num
bloqueio de login global. O dono vai digitar `CORS_ORIGENS` à mão no painel; uma barra a mais no fim faria o CORS
falhar sem nenhuma pista.

## O que fazer
1. **Porta**: `CMD` do `Dockerfile` com `--port ${PORT:-8000}` (forma `sh -c`, que já é a usada). Continua **um
   único worker** (não acrescentar `--workers`; comentário citando ADR-0009: os limites em memória dependem disso).
   O Compose continua publicando `8000:8000` sem definir `PORT`.
2. **`LOGIN_MAX_FALHAS_IP`** em `Config` (inteiro ≥ 0, padrão 20). `0` desliga só o teto por IP; a contagem por par
   (IP, RM) continua com 5. `LimiteLogin` passa a receber o valor da config.
3. **`CORS_ORIGENS`**:
   - tirar espaços e barra(s) final(is) de cada item; ignorar itens vazios;
   - item que não seja `http(s)://host[:porta]` (sem caminho) → a API **não sobe**, com mensagem clara
     ("CORS_ORIGENS: 'xxx' não é uma origem; use algo como https://sala-web.vercel.app");
   - `*` → não sobe, com mensagem dizendo para listar as origens;
   - `INFO` no log ao iniciar: "CORS liberado para: https://..., ..." (o dono confere no painel de logs do Render).
4. **Barra final nas rotas**: confirmar que uma requisição com barra no fim (`/salas/`) não gera redirecionamento
   para `http://` (atrás do proxy o esquema visto é `http`). Se gerar, desligar `redirect_slashes` (o contrato já diz
   que as rotas não têm barra final; a resposta passa a ser `404`).
5. Não mexer em `FORWARDED_ALLOW_IPS` (continua nunca `*`; ADR-0007 item 1).

## Critérios de aceite
- [ ] `docker run -e PORT=10000 ...` → API responde em 10000; sem `PORT` → 8000; `docker compose up` igual a antes.
- [ ] `LOGIN_MAX_FALHAS_IP=0`: 30 falhas de RMs diferentes do mesmo IP não geram `429`; 5 falhas do mesmo RM geram.
      Sem a variável: comportamento do ADR-0007 (teto 20) inalterado (testes atuais verdes).
- [ ] `CORS_ORIGENS="https://a.vercel.app/ , http://localhost:5173"` → preflight de `https://a.vercel.app` aceito;
      `CORS_ORIGENS="*"` e `CORS_ORIGENS="https://a.vercel.app/agenda"` → processo termina com a mensagem.
- [ ] Log de inicialização mostra as origens aceitas.
- [ ] `GET /salas/` não responde `307` com `Location: http://...`.
- [ ] `.env.example` documenta `LOGIN_MAX_FALHAS_IP` (comentário: "no Render use 0; ADR-0009").
