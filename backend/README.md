# backend

API REST em FastAPI. Responsável: **Forge**. Contrato: `../docs/api-contrato.md` (implementar exatamente).
Decisões: `../docs/adr/`. Tickets: `../.scratch/reserva-salas/issues/` (`Responsável: Forge`).

Stack: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2 (+ pydantic-settings), Alembic, psycopg 3, bcrypt, PyJWT,
Pillow (redução das fotos).

## Estrutura esperada

```
backend/
├── Dockerfile
├── requirements.in           # dependências diretas de produção (faixas)
├── requirements.txt          # produção, versões exatas (gerado do .in; é o que a imagem instala)
├── requirements-dev.txt      # -r requirements.txt + pytest/httpx (testes, CI)
├── alembic.ini
├── alembic/
│   └── versions/             # 0001 esquema inicial (btree_gist), 0002 token_versao, 0003 fotos no banco
├── app/
│   ├── main.py               # cria o app, CORS (origens no log), middlewares, handlers de erro, /saude, routers
│   ├── core/
│   │   ├── config.py         # Settings via variáveis de ambiente
│   │   ├── db.py             # engine (pool para o Neon, SET TIME ZONE), SessionLocal, get_db
│   │   ├── seguranca.py      # hash de senha, JWT, dependências usuario_atual/exigir_admin
│   │   ├── erros.py          # ErroApi(status, codigo, detail) + handlers (envelope §1.4)
│   │   └── middlewares.py    # CORS por fora; 500 ERRO_INTERNO; limite de corpo (413); cabeçalhos de segurança
│   ├── models/               # professor.py, sala.py, foto.py, equipamento.py, software.py,
│   │                         # horario_aula.py, semestre.py, reserva.py
│   ├── schemas/              # Pydantic: entrada/saída por recurso
│   ├── routers/              # auth.py, salas.py, fotos.py, uploads.py (GET /uploads/... lido do banco),
│   │                         # equipamentos.py, softwares.py, professores.py, horarios.py, semestres.py, reservas.py
│   ├── services/             # regras de negócio (reservas.py, recorrencia.py, fotos.py, imagens.py, ...)
│   ├── seed.py               # python -m app.seed (idempotente)
│   └── importar_fotos.py     # python -m app.importar_fotos (fotos antigas do disco → banco; idempotente)
└── tests/                    # pytest (Sentinela), contra Postgres real
```

## Rodar

- Docker: na raiz, `cp .env.example .env && docker compose up --build` → http://localhost:8000/docs
- Local: `docker compose up db` (porta publicada só em `127.0.0.1`), depois em `backend/`:
  `pip install -r requirements-dev.txt`, `alembic upgrade head`, `python -m app.seed`, `uvicorn app.main:app --reload`.
- Ao subir, o container roda, nesta ordem: `alembic upgrade head` → `python -m app.seed` →
  `python -m app.importar_fotos` → `uvicorn` em `${PORT:-8000}` com **um único worker** (ver "Publicação").

### Mudanças da rodada 5 para quem já roda localmente

- **Pillow** é dependência nova: `pip install -r requirements-dev.txt` de novo (no Docker, `docker compose up --build`).
- As fotos passam a ficar **no banco** (migration `0003`). Na primeira subida, as fotos antigas do volume
  `uploads` são copiadas para o banco sozinhas (ver "Fotos antigas"). Nada é apagado.
- O serviço `uploads-permissoes` saiu do Compose. Se o Compose avisar de container órfão, rode uma vez
  `docker compose up -d --remove-orphans` (remove só o container parado, não dados).
- O volume `uploads` fica montado **só leitura** no backend.
- `CORS_ORIGENS` agora é validado: `*` ou um endereço com caminho impedem a API de subir (barra final é ignorada).
- `GET /salas/` (com barra no fim) passa a responder `404` em vez de redirecionar.
- Variáveis novas, todas opcionais localmente: `LOGIN_MAX_FALHAS_IP` e `DB_POOL_*`/`DB_CONEXAO_TIMEOUT_S`
  (veja [`.env.example`](../.env.example)).

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
- `JWT_SECRET` é obrigatório (mínimo 32 caracteres) e não pode ser o valor de exemplo do `.env.example`; a API
  não sobe sem um segredo próprio. Se a `DATABASE_URL` usar a senha de exemplo, a API sobe, mas registra um aviso.
- **Tokens (ADR-0008)**: o JWT leva a claim `ver` = `professores.token_versao`. Trocar/redefinir a senha, mudar o
  papel ou desativar a conta incrementa a versão e derruba todas as sessões dela; `PUT /auth/me/senha` devolve um
  token novo. Tokens sem `ver` (anteriores à migration `0002`) são recusados: todos entram de novo uma vez.
- **Limite de login (ADR-0007)**, em memória por processo: 5 falhas do par (IP, RM) bloqueiam o par por 5 min;
  `LOGIN_MAX_FALHAS_IP` falhas do IP (qualquer RM; padrão 20) bloqueiam o IP por 5 min. `LOGIN_MAX_FALHAS_IP=0`
  desliga só o teto por IP (usado no Render, onde todos chegam com o IP do balanceador; ADR-0009). O IP é o da conexão (`request.client.host`); o código
  **não** lê `X-Forwarded-For`. Com proxy reverso na frente, defina `FORWARDED_ALLOW_IPS` com o IP do proxy
  (veja [`.env.example`](../.env.example)); o uvicorn então usa o IP real do cliente. Nunca use `*`.
- **Limite na troca da própria senha (ticket 50)**, mesmo mecanismo: 5 `senha_atual` erradas da mesma conta em
  5 min bloqueiam `PUT /auth/me/senha` daquela conta por 5 min (`429 MUITAS_TENTATIVAS`, mesmo envelope do login,
  mesmo com a senha certa). A chave é o id do professor (vale para qualquer token da conta); acerto zera.
- **Container sem root (ticket 51)**: a imagem roda como `app` (uid/gid `10001`); o código em `/app` é de root.
  Desde a rodada 5 o processo não grava nada em disco (fotos no banco, ADR-0010).
  *Histórico*: até a rodada 4 o serviço `uploads-permissoes` do Compose fazia `chown` do volume `uploads` para o
  uid 10001; ele saiu, porque o volume agora é só leitura e só serve para a importação.
- **Middlewares** (`app/core/middlewares.py`): o CORS é o mais externo, então toda resposta, inclusive `413` e
  `500`, leva os cabeçalhos CORS (contrato §1.5). Corpo máximo: 1 MB nas rotas comuns (`413 CORPO_GRANDE`) e
  `UPLOAD_MAX_MB` + folga no upload de foto (`413 ARQUIVO_GRANDE`), com ou sem `Content-Length`. Todas as
  respostas levam `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy: no-referrer`;
  as fotos de `/uploads` também `Content-Disposition: inline`, `Cache-Control` e uma CSP com `sandbox`.
- **CORS** (`CORS_ORIGENS`, contrato §1.5): origens exatas `http(s)://host[:porta]`, separadas por vírgula. Espaços,
  barra final e porta padrão são tirados; `*` e endereços com caminho fazem a API **não subir**, com mensagem. As
  origens aceitas aparecem no log ao iniciar (`CORS liberado para: ...`). `redirect_slashes` está desligado:
  rota com barra final responde `404` (atrás do proxy do Render, o redirecionamento iria para `http://`).
- Horários: datas/horas locais em `TZ` (padrão `America/Sao_Paulo`); cada conexão nova do pool recebe
  `SET TIME ZONE` com esse fuso (não usamos o parâmetro `options`, que poolers recusam).
- **Pool de conexões** (`app/core/db.py`, ticket 63): `pool_pre_ping`, `pool_recycle` = `DB_POOL_RECICLAR_S` (240 s,
  menor que a suspensão do Neon), `pool_size`/`max_overflow` = `DB_POOL_TAMANHO`/`DB_POOL_EXTRA` (5/5),
  `pool_timeout` 30 s, `connect_timeout` = `DB_CONEXAO_TIMEOUT_S` (10 s), `application_name=sala_web`. SSL vem da
  própria URL (`?sslmode=require`). Banco fora do ar: `/saude` responde `503` em ~`DB_CONEXAO_TIMEOUT_S`; o log cita
  só o host, nunca a URL (que tem a senha).

## Fotos (ADR-0010)

- O upload (`POST /salas/{id}/fotos`) confere a assinatura (JPEG/PNG/WebP) e o limite `UPLOAD_MAX_MB`, e então
  **reduz** com Pillow (`app/services/imagens.py`, função pura `reduzir`): recusa mais de 40 megapixels antes de
  decodificar (`413`), imagem ilegível vira `415`, aplica a orientação do EXIF, lado maior ≤ 1600 px (nunca amplia),
  RGB sobre fundo branco, JPEG qualidade 80 progressivo (70 se passar de 600 KB), sem metadados (fica só o perfil
  ICC RGB).
- O JPEG vai para `fotos_sala.conteudo` (`bytea`, `STORAGE EXTERNAL`), com `tipo_mime` e `tamanho`. **Nada é gravado
  em disco.** No ORM, `conteudo` é `deferred` com *raiseload*: listas, detalhe, capa e galeria nunca leem os bytes,
  e um acesso acidental levanta erro em vez de fazer uma consulta escondida.
- `GET /uploads/salas/{sala_id}/{uuid}.jpg` (`app/routers/uploads.py`) lê só `conteudo` e `tipo_mime` pelo nome, numa
  sessão curta, e responde com `ETag: "<uuid>"` e `Cache-Control: public, max-age=31536000, immutable`;
  `If-None-Match` igual → `304` sem ler os bytes. Nome inexistente ou foto sem conteúdo → `404` (envelope).
- Excluir foto ou sala só apaga registros.

### Fotos antigas (quem usava o Compose antes da rodada 5)

Até a rodada 4 as fotos ficavam no volume `uploads`. Na primeira subida da versão nova, `python -m app.importar_fotos`
(no `CMD`, depois do seed) copia cada uma para o banco, já reduzida, com um **nome novo** `.jpg`. É idempotente:
só trata fotos com `conteudo` vazio, um commit por foto, nunca apaga arquivos nem linhas e nunca impede a API de subir.

1. **Conferir**: `docker compose logs backend | grep importar_fotos`. Cada foto aparece como
   `Foto N importada: antigo -> novo`; no fim, `Importação de fotos concluída: X importada(s), Y não encontrada(s),
   Z com erro`. Foto cujo arquivo já não existia gera `WARNING` com id e nome e continua respondendo `404` (o site
   mostra um substituto; exclua-a pela tela e envie de novo). Nas subidas seguintes o resumo mostra `0 importada(s)`.
2. **Olhar as fotos na tela** (detalhe de cada ambiente e admin).
3. **Só depois de conferir**, para liberar o espaço do volume antigo:
   - tire a linha `- uploads:/app/uploads:ro` do serviço `backend` e o volume `uploads:` da seção `volumes` do
     seu `docker-compose.yml` (numa rodada futura isso já virá feito);
   - `docker compose up -d` e então `docker volume rm <projeto>_uploads` (o projeto é o nome da pasta, em geral
     `sala_web`: `docker volume ls` mostra o nome exato).
   - **Atenção: `docker volume rm` é irreversível.** As fotos que não foram importadas (as do `WARNING`) se perdem
     de vez. Se quiser guardar uma cópia antes:
     `docker run --rm -v sala_web_uploads:/dados -v "$PWD":/copia alpine tar czf /copia/uploads-antigos.tgz -C /dados .`

## Publicação (Render + Neon)

Passo a passo para o dono do projeto: [`docs/publicacao.md`](../docs/publicacao.md) (ADR-0009). A API usa o mesmo
`Dockerfile`; o Render define `PORT` e o `CMD` escuta nela com **um único worker** (os limites de tentativas ficam em
memória, por processo; não acrescente `--workers`). Health check: `GET /saude`. O `render.yaml` da raiz permite
criar o serviço por Blueprint (opção B do guia) e não contém segredos.

Variáveis de produção (valores **só** no painel do Render → Environment; nunca no repositório):

| Variável | Para que serve | Segredo? |
|---|---|---|
| `DATABASE_URL` | Conexão direta do Neon, `postgresql+psycopg://...?sslmode=require` (sem `-pooler`) | **sim** |
| `JWT_SECRET` | Assinatura dos tokens (≥ 32 caracteres; botão *Generate*) | **sim** |
| `ADMIN_RM` | RM do admin criado pelo seed na primeira subida | não |
| `ADMIN_SENHA` | Senha inicial desse admin; apague depois de entrar e trocar a senha | **sim** |
| `ADMIN_NOME` | Nome do admin inicial (`Administrador`) | não |
| `CORS_ORIGENS` | Endereço do site no Vercel, sem barra no fim | não |
| `LOGIN_MAX_FALHAS_IP` | `0` no Render (todos chegam com o IP do balanceador) | não |
| `TZ` | `America/Sao_Paulo` | não |
| `JWT_EXPIRA_MINUTOS` | Validade do token (opcional, `480`) | não |
| `UPLOAD_MAX_MB` | Tamanho máximo da foto enviada (opcional, `5`) | não |
| `DB_POOL_TAMANHO`, `DB_POOL_EXTRA`, `DB_POOL_RECICLAR_S`, `DB_CONEXAO_TIMEOUT_S` | Pool de conexões (opcionais; os padrões servem) | não |

Não defina `PORT` (o Render define) nem `UPLOAD_DIR` (na nuvem não há fotos antigas; a importação não faz nada).
