# frontend

Interface React + Vite. Responsável: **Pixel**. Consome `../docs/api-contrato.md` (não inventar rotas;
se faltar algo, ticket `Responsável: Atlas`). Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Pixel`).

Stack: React 18, Vite 6, react-router 6, FullCalendar 6 (somente `@fullcalendar/react`, `daygrid`, `timegrid`,
`interaction`), ESLint 9, Vitest + Testing Library.

## Estrutura

```
frontend/
├── Dockerfile                # node:22-slim, npm ci, vite --host 0.0.0.0 --port 5173
├── package.json              # scripts: dev, dev:mock, build, lint, test
├── vite.config.js            # dev server 0.0.0.0:5173 + config do Vitest
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
    ├── utils/                # datas (dia ISO ↔ FullCalendar), aulas seguidas, formatação
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

- Docker: na raiz, `docker compose up --build` → http://localhost:5173 (o Compose passa `VITE_API_URL`).
- Local: em `frontend/`, `npm install && npm run dev` (com `VITE_API_URL=http://localhost:8000`; padrão é esse).
- Sem backend: `npm run dev:mock` (ou `VITE_USE_MOCK=true npm run dev`). Sobe uma API simulada em memória
  (reinicia a cada recarga da página). Contas: `admin` / `admin1234` e `123456` / `senha1234`.
  O mock só existe em desenvolvimento: `npm run build` não o inclui.

## Verificar

```
npm run lint
npm test
npm run build
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
