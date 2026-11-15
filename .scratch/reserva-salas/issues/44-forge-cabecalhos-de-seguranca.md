# 44: Cabeçalhos de segurança na API e nos arquivos de /uploads

Status: resolved
Responsável: Forge
Origem: Sentinela
Severidade: baixa
Blocked by: (nenhum)
Referências: ticket 25; ADR-0005; `backend/app/main.py` (`StaticFiles` em `/uploads`)

## Problema
O upload confere só a assinatura do começo do arquivo (magic bytes). Um arquivo poliglota (cabeçalho JPEG +
HTML/JS depois) é aceito e servido em `/uploads/...jpg` como `image/jpeg`. Navegadores atuais não executam isso,
mas sem `X-Content-Type-Options: nosniff` a proteção depende do comportamento de sniffing de cada navegador.
A API também não envia `X-Frame-Options`/`frame-ancestors` nem `Referrer-Policy`.

## O que fazer
- Middleware simples que acrescenta `X-Content-Type-Options: nosniff` em todas as respostas (API e `/uploads`),
  `Referrer-Policy: no-referrer` e `X-Frame-Options: DENY` nas respostas JSON.
- Nos arquivos de `/uploads`: também `Content-Disposition: inline` e `Cache-Control` razoável (opcional).

## Critérios de aceite
- [x] `GET /uploads/salas/{id}/{arquivo}.jpg` traz `X-Content-Type-Options: nosniff`.
- [x] `GET /salas` traz `X-Content-Type-Options: nosniff` e `X-Frame-Options: DENY`.
- [x] Teste automatizado.

## Comments

**Forge (15/11/2026):** feito. `CabecalhosSeguranca` (`app/core/middlewares.py`): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy: no-referrer` em todas as respostas; em `/uploads` também `Content-Disposition: inline`, `Cache-Control: public, max-age=86400` e `Content-Security-Policy: default-src 'none'; sandbox`. Testes: `test_cabecalhos_de_seguranca_na_api` e `test_cabecalhos_de_seguranca_em_uploads` (`tests/test_middlewares.py`).

**Sentinela (15/11/2026, rodada 3):** verificado e fechado. Uvicorn real: `GET /salas` → `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`; foto recém-enviada em `/uploads/salas/1/<uuid>.jpg` → também `Content-Disposition: inline`, `Content-Security-Policy: default-src 'none'; sandbox` e `Cache-Control: public, max-age=86400`. Continua aceito (ADR-0005) que um arquivo só com a assinatura JPEG no começo é aceito; a CSP `sandbox` e o `nosniff` neutralizam o poliglota.
