# backend

API REST em FastAPI. Responsável: **Forge**. Contrato: `../docs/api-contrato.md` (implementar exatamente).
Decisões: `../docs/adr/`. Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Forge`).

Stack: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2 (+ pydantic-settings), Alembic, psycopg 3, bcrypt, PyJWT.

## Estrutura esperada

```
backend/
├── Dockerfile
├── requirements.in           # dependências diretas de produção (faixas)
├── requirements.txt          # produção, versões exatas (gerado do .in; é o que a imagem instala)
├── requirements-dev.txt      # -r requirements.txt + pytest/httpx (testes, CI)
├── alembic.ini
├── alembic/
│   └── versions/             # 0001 cria btree_gist + todas as tabelas
├── app/
│   ├── main.py               # cria o app, CORS, handlers de erro, StaticFiles /uploads, routers
│   ├── core/
│   │   ├── config.py         # Settings via variáveis de ambiente
│   │   ├── db.py             # engine, SessionLocal, get_db
│   │   ├── seguranca.py      # hash de senha, JWT, dependências usuario_atual/exigir_admin
│   │   ├── erros.py          # ErroApi(status, codigo, detail) + handlers (envelope §1.4)
│   │   └── middlewares.py    # CORS por fora; 500 ERRO_INTERNO; limite de corpo (413); cabeçalhos de segurança
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
- Local: `docker compose up db` (porta publicada só em `127.0.0.1`), depois em `backend/`:
  `pip install -r requirements-dev.txt`, `alembic upgrade head`, `python -m app.seed`, `uvicorn app.main:app --reload`.

### Dependências

`requirements.txt` fixa as versões exatas testadas (inclusive as transitivas, como o Starlette), para que todo
`docker compose build` gere o mesmo ambiente (ADR-0001). A imagem instala só ele; ferramentas de teste ficam em
`requirements-dev.txt`. Para atualizar: edite `requirements.in`, instale num venv limpo, rode a suíte e regenere
o `requirements.txt` com as versões instaladas (ou `pip-compile requirements.in`).

## Testes (fumaça)

Contra Postgres real, num banco separado: `DATABASE_URL_TESTE` ou, se ausente, o banco de `DATABASE_URL`
com sufixo `_teste` (crie antes: `createdb sala_web_teste`). O esquema é recriado com Alembic a cada execução.

```
cd backend && pip install -r requirements-dev.txt && pytest
```

A suíte completa é do Sentinela; os testes de fumaça e os dos tickets do Forge também ficam em `tests/`.

## Notas de implementação

- **Seed (ADR-0006)** roda a cada start do container e nunca atualiza nem apaga linhas:
  - admin inicial: criado a partir de `ADMIN_RM`/`ADMIN_SENHA`/`ADMIN_NOME` se esse RM não existir; uma conta
    existente nunca é alterada. Se o admin com `ADMIN_RM` for excluído, o próximo start o recria (recuperação de
    acesso; para impedir, retire `ADMIN_RM`/`ADMIN_SENHA` do `.env`);
  - equipamentos, softwares, ambientes, grade de aulas e **semestres** só recebem os dados de partida se a
    tabela estiver **vazia**. Semestres de partida: os dois do ano corrente e os dois do seguinte; depois disso
    o admin cadastra os novos (excluir um semestre de partida não o faz voltar);
  - consequência: se o admin esvaziar uma tabela inteira, o próximo start recoloca os dados de partida dela.
- `JWT_SECRET` é obrigatório (mínimo 16 caracteres) e não pode ser o valor de exemplo do `.env.example`; a API
  não sobe sem um segredo próprio. Se a `DATABASE_URL` usar a senha de exemplo, a API sobe, mas registra um aviso.
- **Tokens (ADR-0008)**: o JWT leva a claim `ver` = `professores.token_versao`. Trocar/redefinir a senha, mudar o
  papel ou desativar a conta incrementa a versão e derruba todas as sessões dela; `PUT /auth/me/senha` devolve um
  token novo. Tokens sem `ver` (anteriores à migration `0002`) são recusados: todos entram de novo uma vez.
- **Limite de login (ADR-0007)**, em memória por processo: 5 falhas do par (IP, RM) bloqueiam o par por 5 min;
  20 falhas do IP (qualquer RM) bloqueiam o IP por 5 min. O IP é o da conexão (`request.client.host`); o código
  **não** lê `X-Forwarded-For`. Com proxy reverso na frente, defina `FORWARDED_ALLOW_IPS` com o IP do proxy
  (veja [`.env.example`](../.env.example)); o uvicorn então usa o IP real do cliente. Nunca use `*`.
- **Middlewares** (`app/core/middlewares.py`): o CORS é o mais externo, então toda resposta, inclusive `413` e
  `500`, leva os cabeçalhos CORS (contrato §1.5). Corpo máximo: 1 MB nas rotas comuns (`413 CORPO_GRANDE`) e
  `UPLOAD_MAX_MB` + folga no upload de foto (`413 ARQUIVO_GRANDE`), com ou sem `Content-Length`. Todas as
  respostas levam `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy: no-referrer`;
  os arquivos de `/uploads` também `Content-Disposition: inline`, `Cache-Control` e uma CSP com `sandbox`.
- Horários: datas/horas locais em `TZ` (padrão `America/Sao_Paulo`); a sessão do Postgres usa o mesmo fuso.
