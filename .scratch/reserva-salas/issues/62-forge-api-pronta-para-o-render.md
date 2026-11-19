# 62: API pronta para o Render (porta `PORT`, CORS de produção, teto de login por IP configurável)

Status: resolved
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
- [x] `docker run -e PORT=10000 ...` → API responde em 10000; sem `PORT` → 8000; `docker compose up` igual a antes.
- [x] `LOGIN_MAX_FALHAS_IP=0`: 30 falhas de RMs diferentes do mesmo IP não geram `429`; 5 falhas do mesmo RM geram.
      Sem a variável: comportamento do ADR-0007 (teto 20) inalterado (testes atuais verdes).
- [x] `CORS_ORIGENS="https://a.vercel.app/ , http://localhost:5173"` → preflight de `https://a.vercel.app` aceito;
      `CORS_ORIGENS="*"` e `CORS_ORIGENS="https://a.vercel.app/agenda"` → processo termina com a mensagem.
- [x] Log de inicialização mostra as origens aceitas.
- [x] `GET /salas/` não responde `307` com `Location: http://...`.
- [x] `.env.example` documenta `LOGIN_MAX_FALHAS_IP` (comentário: "no Render use 0; ADR-0009").

## Resolução (Forge, rodada 5)
- Porta: `CMD` com `--port ${PORT:-8000}` e `exec uvicorn` (sinais chegam ao uvicorn); comentário no `Dockerfile` sobre
  o worker único (ADR-0009). Compose sem `PORT` (continua 8000).
- `LOGIN_MAX_FALHAS_IP` (`Config`, `ge=0`, padrão 20). `LimiteLogin.da_config()` cria o limitador do módulo;
  `max_falhas_ip=0` desliga só o contador por IP (nem guarda entradas); o par (IP, RM) continua com 5.
- `CORS_ORIGENS`: `normalizar_origens` (em `core/config.py`, usado por um validador do `Config`) tira espaços e barras
  finais, ignora vazios e repetidos, põe esquema/host em minúsculas e tira a porta padrão (`:443`/`:80`; o navegador
  nunca as manda no `Origin`). `*` (ou qualquer curinga) e itens que não sejam `http(s)://host[:porta]` impedem a API
  (e o seed) de subir, com a mensagem pedida. `INFO "CORS liberado para: ..."` em `criar_app`.
- Barra final: o FastAPI respondia `307` com `Location: http://testserver/salas`; `redirect_slashes=False` →
  `/salas/` responde `404 NAO_ENCONTRADO`. Nenhuma rota do projeto é declarada com barra final.
- `FORWARDED_ALLOW_IPS` não foi tocado.
- Conferido: o mesmo `sh -c` do `CMD` com `PORT=10000` → API em 10000; `docker run -e PORT=10000` da imagem →
  `Uvicorn running on http://0.0.0.0:10000`; Compose em 8000; log com as origens; preflight de `https://a.vercel.app`
  com `CORS_ORIGENS="https://a.vercel.app/ , http://localhost:5173"` → 200.
- Testes: `backend/tests/test_publicacao_render.py` (padrão/validação da variável, 30 falhas de RMs diferentes sem
  429 e 5 do mesmo RM com 429 pela API, teto 20 inalterado sem a variável, normalização, origens inválidas, processo
  que termina com `*` e com `/agenda`, preflight, log, `/salas/` sem redirecionar, `CMD` do Dockerfile, `.env.example`).
