# frontend

Interface React + Vite. Responsável: **Pixel**. Consome `../docs/api-contrato.md` (não inventar rotas;
se faltar algo, ticket `Responsável: Atlas`). Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Pixel`).

Stack: React 18, Vite 6, react-router 7 (modo biblioteca, pacote `react-router`), FullCalendar 6 (somente `@fullcalendar/react`, `daygrid`, `timegrid`,
`interaction`), ESLint 9, Vitest 5 + Testing Library.

## Estrutura

```
frontend/
├── Dockerfile                # multi-stage: node:22-alpine (npm ci + vite build) → nginx:1.28-alpine
├── nginx.conf                # serve dist/, fallback de SPA para index.html, 404 para arquivo inexistente
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
