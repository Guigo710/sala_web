# sala_web

Sistema web para gerenciamento, consulta e reserva de salas e laboratórios escolares. Veja `README.md`.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Time de agentes

Definidos em `.claude/agents/`. Decisões do projeto em `.scratch/reserva-salas/decisoes.md` (fonte da verdade).

| Agente | Papel |
|---|---|
| **Atlas** | Engenharia de software e arquitetura: spec, contrato da API (`docs/api-contrato.md`), ADRs, tickets, revisão. Emite ordens de melhoria para Forge. |
| **Pixel** | Frontend: React + Vite, FullCalendar, conectores com a API (`frontend/`). |
| **Forge** | Backend: FastAPI, SQLAlchemy, PostgreSQL (`backend/`). Executa as ordens de Atlas. |
| **Sentinela** | Segurança e testes: pytest, Vitest, Playwright, revisão de segurança, CI. |

Tickets em `.scratch/reserva-salas/issues/`, com linha `Responsável:` indicando o agente.
