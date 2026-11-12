# 44: Cabeçalhos de segurança na API e nos arquivos de /uploads

Status: ready-for-agent
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
- [ ] `GET /uploads/salas/{id}/{arquivo}.jpg` traz `X-Content-Type-Options: nosniff`.
- [ ] `GET /salas` traz `X-Content-Type-Options: nosniff` e `X-Frame-Options: DENY`.
- [ ] Teste automatizado.
