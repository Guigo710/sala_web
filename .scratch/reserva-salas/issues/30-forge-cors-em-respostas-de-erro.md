# 30: Cabeçalhos CORS nas respostas 413 antecipadas e 500

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: alta
Blocked by: (nenhum)
Referências: `docs/api-contrato.md` §1.4, §1.5; ticket 29 (ponto 14)

## Problema
Duas respostas de erro saem **sem** `Access-Control-Allow-Origin`. O navegador então esconde o envelope, e o
frontend mostra "Não foi possível conectar ao servidor" (`SEM_CONEXAO`, `frontend/src/api/cliente.js:149` e `:187`)
em vez da mensagem da API.

1. **413 antecipado do upload.** `backend/app/main.py:39-51` registra `limitar_upload` com `@app.middleware("http")`
   **depois** do `CORSMiddleware` (`main.py:27-32`). No Starlette, o último middleware adicionado fica por fora,
   então a resposta `413` desse middleware não passa pelo CORS.
2. **500.** O handler de `Exception` (`backend/app/core/erros.py:167-173`) é executado pelo `ServerErrorMiddleware`,
   que fica sempre por fora de todos os middlewares do usuário, inclusive o CORS.

Reproduzido com `TestClient` e `Origin: http://localhost:5173`: o `413` (Content-Length de 50 MB) e o `500`
(banco fora do ar) voltam sem o cabeçalho; o `405` volta com ele.

## O que fazer
- Deixar o `CORSMiddleware` como o middleware mais externo: adicioná-lo **por último**, depois de `limitar_upload`.
- Fazer erros inesperados virarem o envelope `ERRO_INTERNO` **por dentro** do CORS: um middleware registrado antes
  do CORS que captura `Exception`, registra o log com stack trace e devolve o `500` com o envelope. O handler de
  `erros.py:167` continua como última rede de segurança.
- Não mudar o envelope nem os códigos.

## Critérios de aceite
- [ ] Com `Origin: http://localhost:5173`, estas respostas trazem `access-control-allow-origin: http://localhost:5173`:
  `413` antecipado (Content-Length acima do limite), `413` lido em blocos, `415`, `401`, `403`, `404`, `405`,
  `409`, `422` e `500` (forçado, ex.: monkeypatch de um service que lança `RuntimeError`).
- [ ] Com origem não permitida, nenhuma delas traz o cabeçalho.
- [ ] O `500` continua com `{"detail": "...", "codigo": "ERRO_INTERNO"}`, sem stack trace no corpo e com stack trace no log.
- [ ] Teste automatizado cobrindo pelo menos o `413` antecipado e o `500` (combinar com o Sentinela, ticket 24).

## Comments
