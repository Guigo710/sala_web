# 40: Limite de tamanho do corpo para todas as rotas (inclusive upload sem Content-Length)

Status: resolved
Responsável: Forge
Origem: Sentinela
Severidade: média
Blocked by: (nenhum)
Referências: ticket 25 (revisão de segurança); ticket 29 (ponto 14); ADR-0005; `backend/app/main.py:34-51`

## Problema
O middleware `limitar_upload` só olha o `Content-Length`. Uma requisição com `Transfer-Encoding: chunked`
(sem `Content-Length`) passa direto, e o FastAPI lê e faz o parse do multipart **antes** de resolver as
dependências de autenticação. Medido contra a API real (uvicorn, sem token):

```
POST /salas/1/fotos  chunked 400 MB, sem token  → 401 em 1,4 s (o corpo inteiro foi lido e gravado em arquivo temporário)
POST /salas/1/fotos  Content-Length 30 MB       → 413 (barrado cedo, ok)
POST /auth/login     JSON de 50 MB               → 422 em 0,5 s (corpo inteiro lido para a memória)
```

Qualquer pessoa na rede consegue encher o disco temporário/memória do servidor e ocupar workers, sem login.
Não há limite de corpo para nenhuma rota além do upload.

## O que fazer
- Middleware ASGI (puro, não `@app.middleware("http")`) que conta os bytes recebidos em `receive` e corta com
  `413` quando passar do limite: `UPLOAD_MAX_MB` + folga nas rotas de foto; um limite pequeno (ex.: 1 MB) nas demais.
  Vale com ou sem `Content-Length`.
- Manter a recusa antecipada pelo `Content-Length` (já existe).
- Registrar o middleware de forma que a resposta saia com CORS (ver ticket 30).

## Critérios de aceite
- [x] Upload chunked acima do limite → `413 ARQUIVO_GRANDE` sem ler o corpo todo (teste com gerador de 50 MB).
- [x] `POST /auth/login` com corpo de 5 MB → `413` (código a definir com o Atlas, ex.: `CORPO_GRANDE`) antes do parse.
- [x] Testes de upload do Sentinela (`tests/test_catalogo_upload.py`) continuam passando.

## Comments

**Forge (15/11/2026):** feito. `LimiteCorpo` (ASGI puro, `app/core/middlewares.py`): recusa pelo `Content-Length` e conta os bytes de `receive` (chunked), parando a leitura ao passar do limite. Foto: `UPLOAD_MAX_MB` + 512 KB → `413 ARQUIVO_GRANDE`; demais rotas: 1 MB → `413 CORPO_GRANDE` (registro no contrato pedido no ticket 47, Atlas). Fica por dentro do CORS. Testes em `tests/test_middlewares.py` (gerador de 50 MB, a aplicação lê só os primeiros blocos; login com 5 MB → 413 antes do parse; corpo no limite passa); `test_catalogo_upload.py` segue verde. Conferido com uvicorn real: login chunked de 2 MB → `413 CORPO_GRANDE`.
