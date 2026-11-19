# frontend

Interface React + Vite. Responsável: **Pixel**. Consome `../docs/api-contrato.md` (não inventar rotas;
se faltar algo, ticket `Responsável: Atlas`). Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Pixel`).

Stack: React 18, Vite 6, react-router 7 (modo biblioteca, pacote `react-router`), FullCalendar 6 (somente `@fullcalendar/react`, `daygrid`, `timegrid`,
`interaction`), ESLint 9, Vitest 5 + Testing Library.

## Estrutura

```
frontend/
├── Dockerfile                # multi-stage: node:22-alpine (npm ci + vite build) → nginx:1.28-alpine
├── nginx.conf                # template: serve dist/, fallback de SPA, 404 para arquivo inexistente, CSP (ticket 52)
├── vercel.json               # publicação no Vercel: fallback de SPA, cabeçalhos de segurança, cache de /assets (ticket 65)
├── vite-plugins/csp-vercel.js # só no build do Vercel (VERCEL=1): <meta> CSP com a origem de VITE_API_URL (ticket 65)
├── package.json              # scripts: dev, dev:mock, build, lint, test
├── vite.config.js            # dev server em localhost:5173, preview em 0.0.0.0:5173 + config do Vitest
├── eslint.config.js
├── index.html
└── src/
    ├── main.jsx              # providers; liga o mock só em dev com VITE_USE_MOCK=true
    ├── App.jsx               # rotas
    ├── api/                  # conectores: cliente.js (VITE_API_URL, Bearer, ErroApi, 401) + 1 arquivo por recurso
    │   └── mock/             # API simulada em memória (só desenvolvimento, fora do build)
    ├── auth/                 # AuthContext, RotaProtegida, RotaAdmin, sessão em localStorage
    ├── components/           # Layout, Cabecalho, CartaoSala, Galeria, ModalReserva, PreviaRecorrencia,
    │                         # SeletorAulas, DisponibilidadeDia, DialogoCancelar, Modal, avisos...
    ├── hooks/                # useCarregar, useTipos
    ├── pages/                # Login, Agenda, Salas, SalaDetalhe, MinhasReservas, MinhaConta, admin/*
    ├── utils/                # datas (dia ISO ↔ FullCalendar), aulas seguidas, formatação, validação de fotos
    └── styles/global.css
```

## Rotas da interface

| Rota | Acesso | Tela |
|---|---|---|
| `/agenda` | público | FullCalendar mês/semana/dia, filtro por ambiente (`?sala=`) |
| `/ambientes` | público | Lista com filtros na URL (tipo, capacidade, equipamento, software, busca, livre em data + aulas) |
| `/ambientes/:id` | público | Galeria, equipamentos, softwares, disponibilidade do dia, botão Reservar |
| `/login` | público | RM + senha |
| `/minhas-reservas` | professor | Futuras/Passadas, cancelar uma ou a recorrência |
| `/minha-conta` | professor | Dados e troca de senha |
| `/admin/*` | admin | ambientes (+ equipamentos, softwares e fotos do ambiente), equipamentos, softwares, professores, horários, semestres |

## Rodar

- **Docker** (na raiz): `cp .env.example .env && docker compose up --build` → http://localhost:5173.
  A imagem faz o build de produção (`npm run build`) e o serve com nginx; **não** roda o dev server do Vite
  (ticket 42). Rotas como `/agenda` e `/admin/ambientes` abrem direto pela URL (fallback para `index.html`);
  caminhos de arquivo inexistentes (ex.: `/src/main.jsx`) dão 404.
  - As variáveis `VITE_*` valem **no build** (o Vite as grava no JavaScript): o Compose as passa como build args.
    Mudou `VITE_API_URL` ou `VITE_UPLOAD_MAX_MB` no `.env`? Rode `docker compose up --build` de novo; só reiniciar
    o contêiner não basta.
  - CSP (ticket 52): o Dockerfile passa o `nginx.conf` pelo `envsubst` e troca `${API_ORIGIN}` pela origem do
    `VITE_API_URL` (`connect-src`/`img-src`, cobre as fotos de `/uploads`); URL fora de `http(s)://host[:porta][/caminho]`
    derruba o build. Sem `'unsafe-inline'`: o `<style>` que o FullCalendar injeta usa o nonce de
    `<meta name="csp-nonce">` do `index.html`, que o nginx troca a cada resposta (`$request_id`). O
    `e2e/csp.spec.js` confere tudo contra a imagem (`E2E_EXIGIR_CSP=1`); no `vite preview`, sem CSP, ele é pulado.
  - Sem hot reload no Docker: para desenvolver, use o modo local abaixo (pode deixar `db` e `backend` no Docker).
- **Local** (desenvolvimento): em `frontend/`, `npm install && npm run dev` → http://localhost:5173, com hot reload.
  `VITE_API_URL` padrão `http://localhost:8000`. O dev server é só para a sua máquina de desenvolvimento.
- **Build local**: `npm run build && npm run preview` serve `dist/` em http://localhost:5173 (é o que o CI e o E2E usam).
- **Sem backend**: `npm run dev:mock` (ou `VITE_USE_MOCK=true npm run dev`). Sobe uma API simulada em memória
  (reinicia a cada recarga da página). Contas: `admin` / `admin1234` e `123456` / `senha1234`.
  O mock só existe em desenvolvimento: `npm run build` não o inclui. Segue o contrato 1.2: a troca de senha
  devolve token novo e a redefinição de senha, a mudança de papel e a desativação derrubam as sessões da conta.

### Variáveis

| Variável | Padrão | Uso |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base da API (sem barra final). |
| `VITE_UPLOAD_MAX_MB` | `5` (no Compose: `UPLOAD_MAX_MB`) | Limite da foto conferido no navegador antes do upload; deve acompanhar o `UPLOAD_MAX_MB` do backend, que continua sendo a referência (`413`). |
| `VITE_USE_MOCK` | (vazio) | `true` liga a API simulada, só no `npm run dev`. |

## Publicação no Vercel (ADR-0009, ticket 65)

Passo a passo para o dono: [`../docs/publicacao.md`](../docs/publicacao.md) (seção 4). No projeto do Vercel:
Root Directory `frontend`, Framework **Vite**, Build Command `npm run build`, Output Directory `dist` e a variável
`VITE_API_URL` = endereço da API no Render (`https://...onrender.com`, sem barra no fim). Mudou `VITE_API_URL`?
**Redeploy**: o valor entra no build.

- **`vercel.json`** (lido pelo Vercel na pasta `frontend`):
  - `rewrites`: caminhos **sem extensão** (`/agenda`, `/ambientes/3`, `/admin/ambientes`) → `/index.html` (rotas do
    React Router). Arquivo inexistente com extensão (`/src/main.jsx`, `/assets/nao-existe.js`, `/.env`) → 404, como
    no nginx. No Vercel, arquivo que existe em `dist/` tem prioridade sobre o `rewrite`.
  - `headers`: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` e uma CSP fixa com
    `img-src`/`connect-src 'self' https:` e `frame-ancestors 'none'`; `/assets/*` com cache de 1 ano (`immutable`;
    os nomes têm hash). O `index.html` fica com o cache padrão do Vercel (revalidado).
- **Por que a CSP é diferente do nginx**: o Vercel serve arquivos estáticos e não gera um nonce por resposta. Por
  decisão do ADR-0009, **só no Vercel** `style-src` tem `'unsafe-inline'` (o `<style>` que o FullCalendar injeta);
  `script-src 'self'` continua estrito, sem `'unsafe-inline'` nem `'unsafe-eval'`. Nonce fixo ou hash foram
  rejeitados (ADR-0009); com nonce ou hash presentes o navegador ignoraria o `'unsafe-inline'`.
- **Origem da API na CSP**: a URL do Render não cabe no `vercel.json` (só existe depois de criado o serviço). O
  plugin `vite-plugins/csp-vercel.js` age só quando `VERCEL` está definido (o Vercel define `VERCEL=1` no build):
  calcula a origem de `VITE_API_URL` (mesma regra do Dockerfile; fora de `http(s)://host[:porta][/caminho]`, ou
  vazia, **o build falha** com mensagem clara), grava como primeiro elemento do `<head>` uma
  `<meta http-equiv="Content-Security-Policy">` com `img-src`/`connect-src 'self' <origem da API>` e tira a
  `<meta name="csp-nonce">`. O navegador aplica cabeçalho e meta juntos: vale o que as duas permitem.
- Fora do Vercel (`npm run build`, Dockerfile, Compose) o `index.html` sai igual ao de antes, com o nonce do nginx.
- Conferir localmente: `VERCEL=1 VITE_API_URL=https://api.exemplo.com npm run build` e olhar `dist/index.html`
  (o CI faz o mesmo e valida o `vercel.json`).
- Prévias do Vercel (outros branches) não falam com a API sem acrescentar a URL delas em `CORS_ORIGENS` (ADR-0009).

## API dormindo (Render Free, ticket 66)

A API publicada dorme após 15 minutos sem tráfego e leva cerca de 1 minuto para acordar.

- Ao abrir o site, `main.jsx` dispara `GET /saude` sem esperar a resposta (`acordarApi`, em `src/api/saude.js`).
- Requisição à API sem resposta depois de 4 s (ou sendo repetida) mostra o aviso "O servidor está acordando..."
  (`AvisoServidor`, `role="status"`); ele some quando não há mais requisição lenta (`src/api/lentidao.js`).
- `GET` que falha por rede ou com `502`/`503`/`504` é repetido sozinho (esperas de 1, 2, 4, 8 e 15 s, até ~90 s no
  total). `POST`, `PUT`, `PATCH`, `DELETE` e o upload **nunca** são repetidos (duplicariam a ação): a mensagem de
  erro pede para tentar de novo em instantes. Não há tempo-limite curto nas requisições.
- No Compose/local a API responde rápido e o aviso não aparece.

## Fotos (contrato 1.4, ADR-0010, ticket 67)

`Foto.url` continua `/uploads/salas/{sala_id}/{uuid}.jpg` (agora servida do banco). Foto que não carrega (ex.: `404`
de uma foto antiga cujo arquivo se perdeu na importação) vira um bloco "Foto indisponível" (`FotoApi`), sem laço de
erro e mantendo o `alt`; no admin, o bloco diz que a foto pode ser removida. O admin informa que as fotos são
reduzidas para até 1600 px, salvas em JPEG e sem localização (GPS). O mock (`npm run dev:mock`) tem uma foto assim
na sala 8.

## Sessão e troca de senha (contrato 1.2, ADR-0008)

- "Minha conta → Trocar senha" (`PUT /auth/me/senha`) recebe um token novo e o grava no lugar do antigo: o usuário
  continua logado; as outras sessões da conta caem.
- Admin redefinindo a **própria** senha em Administração → Professores: a tela avisa antes, e depois do `204` a sessão
  é encerrada e o login mostra "Senha redefinida. Entre novamente.".
- Qualquer `401` em rota protegida (token revogado ou vencido) leva ao login com aviso.

## Verificar

```
npm run lint
npm test
npm run build
npm audit --omit=dev   # deve ficar sem alertas (ticket 45)
```

## E2E (Playwright, contra o sistema real)

Com a API (migrations + seed) e o frontend no ar, em `frontend/`:

```
npx playwright test          # ou: npm run e2e
```

Variáveis (todas opcionais): `E2E_BASE_URL` (padrão `http://localhost:5173`), `E2E_API_URL` (`http://localhost:8000`),
`E2E_ADMIN_RM` / `E2E_ADMIN_SENHA` (admin do seed; caem em `ADMIN_RM` / `ADMIN_SENHA`), `E2E_SCREENSHOTS`
(pasta das capturas do fluxo; padrão `test-results/telas`). Os testes ficam em `e2e/` e criam um ambiente e
professores com nomes únicos, então podem rodar várias vezes no mesmo banco. No CI (`.github/workflows/ci.yml`)
rodam contra o build de produção (`vite preview`). Primeira vez fora do CI: `npx playwright install chromium`.
