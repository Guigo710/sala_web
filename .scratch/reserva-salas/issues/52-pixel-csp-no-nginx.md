# 52: Content-Security-Policy no nginx do frontend

Status: done
Responsável: Pixel
Origem: Sentinela
Severidade: baixa
Blocked by: (nenhum)
Referências: ticket 42; ADR-0004 (token em `localStorage`); `frontend/nginx.conf`

## Problema
O `nginx.conf` já manda `nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy` (conferido na rodada 3 com o
`dist/` real), mas não manda `Content-Security-Policy`. Como o token fica em `localStorage` (ADR-0004), uma
falha de XSS levaria o token; uma CSP restritiva é a segunda barreira.

## O que fazer
- `add_header Content-Security-Policy "..." always;` no `server`, por exemplo:
  `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: <API>;
  connect-src 'self' <API>; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'`.
  O FullCalendar injeta `<style>`, por isso `'unsafe-inline'` só em `style-src`.
- `<API>` vem do `VITE_API_URL` do build: gerar o trecho no Dockerfile (ex.: `envsubst` num template do
  `nginx.conf`) ou documentar a troca.
- Opcional: `Permissions-Policy: camera=(), microphone=(), geolocation=()`.

## Critérios de aceite
- [ ] `curl -I :5173/agenda` traz a CSP.
- [ ] `npx playwright test` verde contra o Compose (fotos de `/uploads` aparecem, sem erro de CSP no console).
- [ ] O job `imagens` do CI confere o cabeçalho.

## Resolução (Pixel, rodada 4)
- `frontend/nginx.conf` virou template: o Dockerfile (estágio nginx) tira a origem do `VITE_API_URL` (só aceita
  `http(s)://host[:porta][/caminho]`, senão o build falha), roda `envsubst '${API_ORIGIN}'` e `nginx -t`.
- CSP final (com a API padrão):
  `default-src 'self'; script-src 'self'; style-src 'self' 'nonce-<request_id>'; img-src 'self' http://localhost:8000;
  connect-src 'self' http://localhost:8000; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self';
  frame-ancestors 'none'`, mais `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- Sem `'unsafe-inline'`: o FullCalendar 6 lê o nonce de `<meta name="csp-nonce">` (`index.html`, marcador
  `__CSP_NONCE__` trocado pelo `sub_filter` com `$request_id` a cada resposta). `index.html` sem ETag/Last-Modified
  (sem 304 com nonce velho). `font-src data:` só pela fonte de ícones embutida do FullCalendar (fcicons).
- `e2e/csp.spec.js` (login, agenda, detalhe com foto de `/uploads`, admin) e job `imagens` do CI conferem a CSP e o nonce.
- Critérios: `curl -I /agenda` traz a CSP; `npx playwright test` 9/9 contra a imagem nginx + API real; CI atualizado.
