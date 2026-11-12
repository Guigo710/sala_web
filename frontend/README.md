# frontend

Interface React + Vite. Responsável: **Pixel**. Consome `../docs/api-contrato.md` (não inventar rotas;
se faltar algo, ticket `Responsável: Atlas`). Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Pixel`).

Stack: React 18, Vite, react-router, FullCalendar (somente `@fullcalendar/react`, `daygrid`, `timegrid`,
`interaction`), ESLint, Vitest + Testing Library.

## Estrutura esperada

```
frontend/
├── Dockerfile                # node:20, npm ci, vite --host 0.0.0.0 --port 5173
├── package.json              # scripts: dev, build, lint, test
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx               # rotas
    ├── api/                  # conectores: cliente.js (base VITE_API_URL, Bearer, erros) + 1 arquivo por recurso
    ├── auth/                 # AuthContext, RotaProtegida, RotaAdmin
    ├── components/           # Layout, Cabecalho, CartaoSala, Galeria, ModalReserva, PreviaRecorrencia, ...
    ├── pages/                # Login, Agenda, Salas, SalaDetalhe, MinhasReservas, admin/*
    ├── utils/                # datas (dia da semana ISO ↔ FullCalendar), formatação
    └── styles/
```

## Rodar

- Docker: na raiz, `docker compose up --build` → http://localhost:5173
- Local: em `frontend/`, `npm install && npm run dev` (com `VITE_API_URL=http://localhost:8000`).
