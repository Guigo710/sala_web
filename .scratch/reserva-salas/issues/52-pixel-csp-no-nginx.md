# 52: Content-Security-Policy no nginx do frontend

Status: ready-for-agent
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
