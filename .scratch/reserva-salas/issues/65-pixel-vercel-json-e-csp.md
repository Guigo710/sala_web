# 65: `vercel.json` (fallback do React Router, cabeçalhos de segurança) e CSP no Vercel

Status: resolved
Responsável: Pixel
Origem: Atlas
Prioridade: alta
Blocked by: (nenhum)
Referências: ADR-0009 (seção "Cabeçalhos e CSP do frontend no Vercel", com a justificativa); ticket 52 (CSP com
nonce no nginx); `frontend/nginx.conf`; `frontend/index.html` (`__CSP_NONCE__`); `frontend/vite.config.js`

## Contexto
No Vercel o frontend é servido como arquivos estáticos: não há nginx, nem `sub_filter`, nem nonce por resposta.
Decisão do Atlas (ADR-0009): **só no Vercel**, `style-src 'self' 'unsafe-inline'`, mantendo `script-src 'self'`
estrito. A origem da API não pode ficar fixa no `vercel.json` (a URL do Render só existe depois de criado o serviço),
então ela entra numa `<meta http-equiv="Content-Security-Policy">` gerada no build do Vercel a partir de `VITE_API_URL`.
O Compose (nginx com nonce) **não muda**.

## O que fazer
1. **`frontend/vercel.json`** (o Root Directory do projeto no Vercel é `frontend`):
   - `rewrites`: caminhos **sem extensão** (rotas do React Router: `/agenda`, `/ambientes/3`, `/admin/ambientes`)
     → `/index.html`. Arquivo inexistente com extensão (`/src/main.jsx`, `/assets/nao-existe.js`, `/.env`) → `404`,
     não o `index.html` (mesma regra do nginx). Lembrete: no Vercel o sistema de arquivos tem prioridade sobre `rewrites`.
   - `headers` em todas as rotas: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
     `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()` e
     `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https:; connect-src 'self' https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`.
   - `/assets/(.*)`: `Cache-Control: public, max-age=31536000, immutable`. `index.html` sem cache longo (padrão do Vercel serve).
   - Nada de `buildCommand`/`outputDirectory` no `vercel.json` (ficam nos campos do painel, como no guia); se preferir
     fixá-los aqui, os valores têm de ser `npm run build` e `dist`, e o Atlas ajusta o guia.
2. **Plugin do Vite só para o build no Vercel** (`process.env.VERCEL` definido; o Vercel define `VERCEL=1` no build):
   - calcula a origem de `VITE_API_URL` (mesma regra do Dockerfile: `http(s)://host[:porta][/caminho]`; fora disso,
     **o build falha** com mensagem clara);
   - insere, como **primeiro** elemento do `<head>`, `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' <ORIGEM_API>; connect-src 'self' <ORIGEM_API>; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'">`
     (`frame-ancestors` não vale em meta; fica no cabeçalho);
   - remove a `<meta name="csp-nonce" content="__CSP_NONCE__">` (sem nonce no Vercel; o FullCalendar funciona com `'unsafe-inline'`).
   - **Não** pôr `'nonce-...'` nem hash em `style-src` no Vercel: com nonce ou hash presente o navegador ignora `'unsafe-inline'`.
   - Fora do Vercel (`npm run build` local, Dockerfile) o `index.html` gerado fica idêntico ao de hoje.
3. `frontend/README.md`: seção "Publicação no Vercel" (o que o `vercel.json` faz, por que a CSP é diferente do nginx,
   apontando para ADR-0009 e `docs/publicacao.md`).
4. CI (job frontend): passo que roda `VERCEL=1 VITE_API_URL=https://api.exemplo.com npm run build` e confere em
   `dist/index.html` a meta com `https://api.exemplo.com`, sem `__CSP_NONCE__`; e que `vercel.json` é JSON válido com a CSP acima.

## Critérios de aceite
- [ ] Build no Vercel (ou `VERCEL=1 npm run build` local): `dist/index.html` com a meta CSP da API e sem o marcador.
- [ ] Build sem `VERCEL`: `dist/index.html` igual ao atual; imagem nginx e o job `imagens` do CI continuam verdes.
- [ ] Na implantação de prévia (ou com `npx vercel dev`/`vercel build` se disponível): `/agenda` abre direto pela URL;
      `/src/main.jsx` → 404; cabeçalhos acima presentes (`curl -I`).
- [ ] Agenda (FullCalendar) com estilos corretos e sem erro de CSP no console; fotos da API aparecem; login funciona
      contra a API publicada (conferido no ticket 68).
- [ ] Nenhum `'unsafe-eval'`, nenhum `'unsafe-inline'` em `script-src`.

## Resolução (Pixel, rodada 5)
- `frontend/vercel.json`: `rewrites` com `source` `/((?!.*\.[A-Za-z0-9]+$).*)` → `/index.html` (só caminhos sem
  extensão; conferido com `path-to-regexp@6.1.0`, o do Vercel); `headers` em `/(.*)` com os 4 cabeçalhos + a CSP do
  ADR-0009; `/assets/(.*)` com `Cache-Control: public, max-age=31536000, immutable`. Sem `buildCommand`/`outputDirectory`.
- `frontend/vite-plugins/csp-vercel.js` (registrado no `vite.config.js`, `apply: 'build'`): só com `VERCEL` definido,
  calcula a origem de `VITE_API_URL` (regex do Dockerfile; vazia ou inválida → build falha com mensagem que aponta
  Settings → Environment Variables), põe a `<meta http-equiv="Content-Security-Policy">` como primeiro elemento do
  `<head>` e remove a `<meta name="csp-nonce">` (e o comentário dela). Sem `VERCEL` o HTML sai idêntico (teste).
- Testes: `vite-plugins/csp-vercel.test.js` (origem, meta, plugin com/sem VERCEL, `vercel.json` válido com a CSP exata,
  fallback só sem extensão). CI (job frontend): build sem VERCEL mantém `__CSP_NONCE__`; build com
  `VERCEL=1 VITE_API_URL=https://api.exemplo.com` confere a meta e o `vercel.json`.
- `e2e/csp.spec.js` reconhece o modo Vercel (`'unsafe-inline'` em `style-src` do cabeçalho) e então confere a meta.
- Validação local: `dist/` do build `VERCEL=1` servido por um servidor estático que aplica as regras do `vercel.json`
  (sistema de arquivos primeiro, depois `rewrites`; `headers` por `source`), API local atrás de HTTPS
  (`https://localhost:8443`, porque o cabeçalho só libera `https:`): `/agenda`, `/ambientes/3`, `/admin/ambientes` → 200;
  `/src/main.jsx`, `/assets/nao-existe.js`, `/.env` → 404; cabeçalhos presentes; Playwright 9/9 E2E + 2 verificações
  extras, sem violação de CSP, FullCalendar com estilos (`.fc-header-toolbar` flex).
- `README.md` do frontend: seção "Publicação no Vercel". Implantação real (prévia/produção) fica para o ticket 68.
