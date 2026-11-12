# backend

API REST em FastAPI. Responsável: **Forge**. Contrato: `../docs/api-contrato.md` (implementar exatamente).
Decisões: `../docs/adr/`. Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Forge`).

Stack: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2 (+ pydantic-settings), Alembic, psycopg 3, bcrypt, PyJWT.

## Estrutura esperada

```
backend/
├── Dockerfile
├── requirements.txt          # (ou pyproject.toml)
├── alembic.ini
├── alembic/
│   └── versions/             # 0001 cria btree_gist + todas as tabelas
├── app/
│   ├── main.py               # cria o app, CORS, handlers de erro, StaticFiles /uploads, routers
│   ├── core/
│   │   ├── config.py         # Settings via variáveis de ambiente
│   │   ├── db.py             # engine, SessionLocal, get_db
│   │   ├── seguranca.py      # hash de senha, JWT, dependências usuario_atual/exigir_admin
│   │   └── erros.py          # ErroApi(status, codigo, detail) + handlers (envelope §1.4)
│   ├── models/               # professor.py, sala.py, foto.py, equipamento.py, software.py,
│   │                         # horario_aula.py, semestre.py, reserva.py
│   ├── schemas/              # Pydantic: entrada/saída por recurso
│   ├── routers/              # auth.py, salas.py, fotos.py, equipamentos.py, softwares.py,
│   │                         # professores.py, horarios.py, semestres.py, reservas.py
│   ├── services/             # regras de negócio (reservas.py, recorrencia.py, fotos.py, ...)
│   └── seed.py               # python -m app.seed (idempotente)
└── tests/                    # pytest (Sentinela), contra Postgres real
```

## Rodar

- Docker: na raiz, `cp .env.example .env && docker compose up --build` → http://localhost:8000/docs
- Local: `docker compose up db`, depois em `backend/`: `pip install -r requirements.txt`,
  `alembic upgrade head`, `python -m app.seed`, `uvicorn app.main:app --reload`.

## Testes (fumaça)

Contra Postgres real, num banco separado: `DATABASE_URL_TESTE` ou, se ausente, o banco de `DATABASE_URL`
com sufixo `_teste` (crie antes: `createdb sala_web_teste`). O esquema é recriado com Alembic a cada execução.

```
cd backend && pytest
```

A suíte completa é do Sentinela; `tests/` traz só testes de fumaça dos fluxos principais e de `validar_bloco`.

## Notas de implementação

- O seed roda a cada start do container. Admin: criado se `ADMIN_RM` não existir. Equipamentos, softwares,
  ambientes e grade: só são inseridos **se a tabela estiver vazia** (não desfaz edições do admin).
  Semestres do ano corrente e do seguinte: por nome, se não existir e não se sobrepuser a outro.
- `JWT_SECRET` é obrigatório (mínimo 16 caracteres); a API não sobe sem ele.
- Horários: datas/horas locais em `TZ` (padrão `America/Sao_Paulo`); a sessão do Postgres usa o mesmo fuso.

