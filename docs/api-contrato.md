# Contrato da API: sala_web v1

Responsável: Atlas. **Forge implementa e Pixel consome exatamente este documento.**
Mudanças no contrato só via ticket `Responsável: Atlas`. Regras de negócio detalhadas: `.scratch/reserva-salas/spec.md`.
Versão: **1.2** (2026-11-12). O que mudou desde a 1.0 está no §7 (Histórico).

Sumário
1. Convenções gerais
2. Modelo de dados (PostgreSQL 16)
3. Objetos JSON
4. Rotas
   - 4.1 Saúde e estáticos · 4.2 Auth · 4.3 Salas · 4.4 Fotos · 4.5 Equipamentos · 4.6 Softwares
   - 4.7 Professores · 4.8 Horários de aula · 4.9 Semestres · 4.10 Reservas
5. Matriz de permissões
6. Catálogo de códigos de erro
7. Histórico de mudanças

---

## 1. Convenções gerais

### 1.1 Base, formato e nomes
- Base URL: `http://localhost:8000` (frontend usa `VITE_API_URL`). **Sem prefixo** de versão; rotas **sem barra final** (`/salas`, nunca `/salas/`).
- Corpo e respostas em JSON UTF-8 (`Content-Type: application/json`), exceto upload de foto (`multipart/form-data`).
- Nomes de campos em `snake_case` e em português.
- IDs são inteiros (`integer`, `serial` no banco).
- Listas são devolvidas como **array JSON puro**, sem paginação na v1.
- Campos opcionais ausentes na resposta aparecem como `null` (nunca omitidos).

### 1.2 Datas e horas
- Fuso de referência: `America/Sao_Paulo` (variável `TZ`). "Agora" = hora local do servidor nesse fuso.
- Data: `"YYYY-MM-DD"` (ex.: `"2026-09-15"`).
- Hora: `"HH:MM"` 24h, sem segundos (ex.: `"07:30"`). O backend aceita `"HH:MM:SS"` na entrada, **descarta os segundos** ao gravar e sempre responde `"HH:MM"`.
- Data-hora (`criado_em`, `expira_em`, ...): ISO 8601 com fuso, ex.: `"2026-09-01T10:15:00-03:00"`.
- Dia da semana: inteiro ISO, **1 = segunda … 6 = sábado, 7 = domingo** (Python `date.isoweekday()`).
  Atenção Pixel: FullCalendar usa 0 = domingo; converter com `iso % 7`.

### 1.3 Autenticação
- Header `Authorization: Bearer <token>`.
- Três níveis de acesso, usados em todo o documento:
  - **público**: não exige token. Se um token válido vier, ele é usado (ex.: `pode_cancelar`); token inválido numa rota pública é **ignorado** (tratado como visitante).
  - **professor**: exige token válido de conta ativa com papel `professor` **ou** `admin`.
  - **admin**: exige token válido de conta ativa com papel `admin`.
- Sem token / token inválido / expirado / revogado (`ver` diferente de `token_versao`, ADR-0008) / conta inativa em rota protegida → `401 NAO_AUTENTICADO`.
- Token válido sem papel suficiente → `403 SEM_PERMISSAO`.

### 1.4 Envelope de erro (todas as respostas 4xx)
```json
{
  "detail": "Mensagem em português, pronta para mostrar ao usuário.",
  "codigo": "CODIGO_DE_ERRO"
}
```
Campos extras, só quando indicados:
- `erros` (apenas `codigo = VALIDACAO`, status 422): lista de `{ "campo": "body.capacidade", "mensagem": "deve ser maior que 0" }`.
  O backend substitui o handler padrão de `RequestValidationError` do FastAPI para produzir esse formato.
- `conflitos` (apenas `codigo = CONFLITO_RESERVA`, status 409): lista de objetos `Conflito` (§3.12).

Erros 500 seguem o mesmo envelope com `codigo = ERRO_INTERNO` e mensagem genérica (sem stack trace).

Erros gerados pelo próprio framework (rota/método inexistente, corpo multipart malformado, ...) também usam o
envelope, com os códigos genéricos do §6 (`NAO_ENCONTRADO`, `METODO_NAO_PERMITIDO`, `REQUISICAO_INVALIDA`,
`ERRO_HTTP`). **Pixel:** trate qualquer `codigo` que não conheça mostrando o `detail`; não dependa de a lista
do §6 ser fechada.

### 1.5 CORS
Origens permitidas em `CORS_ORIGENS` (separadas por vírgula; padrão `http://localhost:5173`). Métodos `GET, POST, PUT, PATCH, DELETE`; headers `Authorization, Content-Type`.
**Toda** resposta, inclusive as de erro (`4xx`, `413` recusado antes de ler o corpo, `500`), leva os cabeçalhos
CORS quando a origem é permitida. Sem eles o navegador esconde o envelope e o frontend só vê "sem conexão".

### 1.6 Semântica de `PUT`
- `PUT` **substitui** o recurso inteiro (campos editáveis). Campo opcional omitido é gravado como `null`.
- Campos que no `POST` têm valor padrão (ex.: `ativo`) são **obrigatórios no `PUT`**: omitir `ativo` num `PUT`
  é `422 VALIDACAO` (evita reativar sem querer um ambiente ou aula desativados).
- Não há `PATCH` parcial na v1 (exceto a legenda de foto, §4.4). Para ativar/desativar, o cliente lê o recurso
  (`GET /salas/{id}`, ou o item já listado) e envia o `PUT` completo com `ativo` trocado.

### 1.7 Relógio ("agora")
- "Agora" é sempre o relógio do **servidor** no fuso `TZ` (§1.2). Os campos `passou` (disponibilidade) e
  `pode_cancelar` (reserva) são calculados no servidor e são a referência.
- O cliente pode usar o próprio relógio só para **dicas de interface** (desabilitar um dia passado no calendário,
  estimar quantas ocorrências serão canceladas). A decisão final é do servidor (`DATA_PASSADA`,
  `RESERVA_JA_INICIADA`, contagem devolvida em `POST /reservas/grupos/{id}/cancelar`).

### 1.8 Limites de texto em credenciais
| Campo | Limite | Fora do limite |
|---|---|---|
| `rm` no login | 1–50 caracteres | `422 VALIDACAO` |
| `senha` no login, `senha_atual` | 1–128 caracteres | `422 VALIDACAO` |
| `senha` (criação de conta), `nova_senha` | 8–128 caracteres | `422 VALIDACAO` |
| `rm` na criação de conta | regex `^[A-Za-z0-9]{3,20}$` | `422 VALIDACAO` |

O bcrypt só considera os primeiros 72 bytes da senha (ADR-0004); senhas maiores são aceitas, mas o excedente não conta.

---

## 2. Modelo de dados (PostgreSQL 16)

Migrations com Alembic. A primeira migration cria a extensão:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

Migrations existentes: `0001_inicial` (tudo do §2.1, exceto o abaixo) e `0002_token_versao` (contrato 1.2):

```sql
ALTER TABLE professores ADD COLUMN token_versao integer NOT NULL DEFAULT 0;
```

Todas as tabelas têm PK `id serial` (exceto as de associação). `criado_em`/`atualizado_em` são `timestamptz NOT NULL DEFAULT now()`; `atualizado_em` é atualizado pelo ORM (`onupdate`).

### 2.1 DDL de referência

```sql
-- Contas (professores e admins na mesma tabela)
CREATE TABLE professores (
    id             serial PRIMARY KEY,
    rm             varchar(20)  NOT NULL UNIQUE,          -- regex ^[A-Za-z0-9]{3,20}$
    nome           varchar(120) NOT NULL,
    email          varchar(160),
    senha_hash     varchar(255) NOT NULL,                 -- bcrypt
    papel          varchar(20)  NOT NULL DEFAULT 'professor'
                   CHECK (papel IN ('professor', 'admin')),
    ativo          boolean      NOT NULL DEFAULT true,
    token_versao   integer      NOT NULL DEFAULT 0,       -- ADR-0008; migration 0002; nunca exposto no JSON
    criado_em      timestamptz  NOT NULL DEFAULT now(),
    atualizado_em  timestamptz  NOT NULL DEFAULT now()
);

-- Ambientes (salas e laboratórios)
CREATE TABLE salas (
    id             serial PRIMARY KEY,
    nome           varchar(80)  NOT NULL UNIQUE,
    tipo           varchar(30)  NOT NULL
                   CHECK (tipo IN ('sala','lab_informatica','lab_ciencias','lab_outro','auditorio','outro')),
    descricao      text,
    capacidade     integer      NOT NULL CHECK (capacidade > 0),
    localizacao    varchar(120),                          -- ex.: "Bloco A, 2º andar"
    ativo          boolean      NOT NULL DEFAULT true,
    criado_em      timestamptz  NOT NULL DEFAULT now(),
    atualizado_em  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE fotos_sala (
    id         serial PRIMARY KEY,
    sala_id    integer      NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    arquivo    varchar(255) NOT NULL UNIQUE,              -- caminho relativo a UPLOAD_DIR: "salas/3/<uuid>.jpg"
    legenda    varchar(200),
    ordem      integer      NOT NULL DEFAULT 0,
    criado_em  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_fotos_sala_sala_ordem ON fotos_sala (sala_id, ordem);

CREATE TABLE equipamentos (
    id         serial PRIMARY KEY,
    nome       varchar(80) NOT NULL UNIQUE,
    descricao  text
);

CREATE TABLE sala_equipamentos (
    sala_id         integer NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    equipamento_id  integer NOT NULL REFERENCES equipamentos(id) ON DELETE CASCADE,
    quantidade      integer NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    especificacao   varchar(255),                         -- ex.: "i5 10ª geração, 16 GB RAM, SSD 256 GB"
    PRIMARY KEY (sala_id, equipamento_id)
);

CREATE TABLE softwares (
    id         serial PRIMARY KEY,
    nome       varchar(80) NOT NULL,
    versao     varchar(40),
    categoria  varchar(60),                               -- texto livre: "IDE", "Banco de dados", ...
    CONSTRAINT uq_softwares_nome_versao UNIQUE NULLS NOT DISTINCT (nome, versao)
);

CREATE TABLE sala_softwares (
    sala_id      integer NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    software_id  integer NOT NULL REFERENCES softwares(id) ON DELETE CASCADE,
    PRIMARY KEY (sala_id, software_id)
);

-- Grade de aulas (slots)
CREATE TABLE horarios_aula (
    id           serial PRIMARY KEY,
    turno        varchar(10) NOT NULL CHECK (turno IN ('manha','tarde','noite')),
    ordem        smallint    NOT NULL CHECK (ordem > 0),   -- 1ª, 2ª, ... aula do turno
    inicio       time        NOT NULL,
    fim          time        NOT NULL,
    dias_semana  smallint[]  NOT NULL,                     -- ISO 1..7
    ativo        boolean     NOT NULL DEFAULT true,
    CONSTRAINT ck_horarios_fim_maior CHECK (fim > inicio),
    CONSTRAINT ck_horarios_dias CHECK (
        cardinality(dias_semana) > 0
        AND dias_semana <@ ARRAY[1,2,3,4,5,6,7]::smallint[]
    ),
    CONSTRAINT uq_horarios_turno_ordem UNIQUE (turno, ordem)
);

CREATE TABLE semestres (
    id           serial PRIMARY KEY,
    nome         varchar(20) NOT NULL UNIQUE,              -- ex.: "2026-2"
    data_inicio  date        NOT NULL,
    data_fim     date        NOT NULL,
    CONSTRAINT ck_semestres_datas CHECK (data_fim > data_inicio),
    CONSTRAINT ex_semestres_sem_sobreposicao
        EXCLUDE USING gist (daterange(data_inicio, data_fim, '[]') WITH &&)
);

CREATE TABLE grupos_recorrencia (
    id             serial PRIMARY KEY,
    sala_id        integer  NOT NULL REFERENCES salas(id) ON DELETE RESTRICT,
    professor_id   integer  NOT NULL REFERENCES professores(id) ON DELETE RESTRICT,
    semestre_id    integer  NOT NULL REFERENCES semestres(id) ON DELETE RESTRICT,
    dia_semana     smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    inicio         time     NOT NULL,
    fim            time     NOT NULL,
    criado_por_id  integer  NOT NULL REFERENCES professores(id) ON DELETE RESTRICT,
    criado_em      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reservas (
    id                    serial PRIMARY KEY,
    sala_id               integer  NOT NULL REFERENCES salas(id) ON DELETE RESTRICT,
    professor_id          integer  NOT NULL REFERENCES professores(id) ON DELETE RESTRICT,
    data                  date     NOT NULL,
    inicio                time     NOT NULL,              -- snapshot do início da 1ª aula
    fim                   time     NOT NULL,              -- snapshot do fim da última aula
    periodo               tsrange  GENERATED ALWAYS AS (tsrange(data + inicio, data + fim, '[)')) STORED,
    horario_inicio_id     integer  NOT NULL REFERENCES horarios_aula(id) ON DELETE RESTRICT,
    horario_fim_id        integer  NOT NULL REFERENCES horarios_aula(id) ON DELETE RESTRICT,
    quantidade_aulas      smallint NOT NULL CHECK (quantidade_aulas > 0),
    status                varchar(12) NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa','cancelada')),
    observacao            varchar(200),
    grupo_recorrencia_id  integer  REFERENCES grupos_recorrencia(id) ON DELETE RESTRICT,
    criado_por_id         integer  NOT NULL REFERENCES professores(id) ON DELETE RESTRICT,
    criado_em             timestamptz NOT NULL DEFAULT now(),
    cancelada_em          timestamptz,
    cancelada_por_id      integer  REFERENCES professores(id) ON DELETE RESTRICT,
    motivo_cancelamento   varchar(200),

    CONSTRAINT ck_reservas_fim_maior CHECK (fim > inicio),
    CONSTRAINT ck_reservas_cancelamento CHECK (
        (status = 'ativa'     AND cancelada_em IS NULL AND cancelada_por_id IS NULL)
     OR (status = 'cancelada' AND cancelada_em IS NOT NULL AND cancelada_por_id IS NOT NULL)
    ),
    -- Garantia anti-conflito (ADR-0003): nunca duas reservas ATIVAS sobrepostas na mesma sala.
    CONSTRAINT ex_reservas_sem_sobreposicao
        EXCLUDE USING gist (sala_id WITH =, periodo WITH &&) WHERE (status = 'ativa')
);
CREATE INDEX ix_reservas_data            ON reservas (data);
CREATE INDEX ix_reservas_professor_data  ON reservas (professor_id, data);
CREATE INDEX ix_reservas_grupo           ON reservas (grupo_recorrencia_id);
```

Notas para Forge:
- `periodo` é coluna gerada: no SQLAlchemy use `Computed("tsrange(data + inicio, data + fim, '[)')", persisted=True)` e **nunca** escreva nela. A restrição usa `sqlalchemy.dialects.postgresql.ExcludeConstraint`.
- Violação da exclusão chega como `IntegrityError` com SQLSTATE `23P01` e nome `ex_reservas_sem_sobreposicao`: o service converte em `409 CONFLITO_RESERVA` (buscando as reservas conflitantes para preencher `conflitos`).
- Violação de `ex_semestres_sem_sobreposicao` → `409 SEMESTRE_SOBREPOSTO`. Violação de UNIQUE → o `409` de duplicidade da rota.
- `professores.rm` é comparado exatamente como gravado (sem normalizar maiúsculas).

### 2.2 Relacionamentos
```
professores 1─N reservas (professor_id, criado_por_id, cancelada_por_id)
salas       1─N reservas, 1─N fotos_sala, N─N equipamentos (sala_equipamentos), N─N softwares (sala_softwares)
horarios_aula 1─N reservas (horario_inicio_id, horario_fim_id)
semestres   1─N grupos_recorrencia 1─N reservas
```

### 2.3 Enumerações (valores fixos)

| Enum | Valores (valor → rótulo) |
|---|---|
| `tipo` de sala | `sala` → "Sala de aula", `lab_informatica` → "Laboratório de informática", `lab_ciencias` → "Laboratório de ciências", `lab_outro` → "Outro laboratório", `auditorio` → "Auditório", `outro` → "Outro" |
| `papel` | `professor`, `admin` |
| `turno` | `manha` → "Manhã", `tarde` → "Tarde", `noite` → "Noite" (ordem de exibição: manha, tarde, noite) |
| `status` de reserva | `ativa`, `cancelada` |

Os rótulos de `tipo` são servidos por `GET /salas/tipos`; Pixel não deve fixá-los no código.

---

## 3. Objetos JSON

### 3.1 `Usuario` (conta logada ou visão admin de professor)
```json
{
  "id": 7,
  "rm": "123456",
  "nome": "Maria Souza",
  "email": "maria@fatec.sp.gov.br",
  "papel": "professor",
  "ativo": true,
  "criado_em": "2026-08-01T09:00:00-03:00"
}
```

### 3.2 `PessoaResumo` (exposição pública: nunca RM)
```json
{ "id": 7, "nome": "Maria Souza" }
```

### 3.3 `SalaEquipamento`
```json
{ "equipamento_id": 1, "nome": "Computador", "quantidade": 30, "especificacao": "i5, 16 GB RAM, SSD 256 GB" }
```

### 3.4 `Software`
```json
{ "id": 4, "nome": "Visual Studio Code", "versao": "1.95", "categoria": "IDE" }
```

### 3.5 `Foto`
```json
{
  "id": 12,
  "sala_id": 3,
  "url": "/uploads/salas/3/5b0d6f0e-8a1c-4c55-9a3b-1f2e3d4c5b6a.jpg",
  "legenda": "Vista da porta",
  "ordem": 1,
  "criado_em": "2026-08-02T14:00:00-03:00"
}
```
`url` é relativa à base da API; Pixel monta `${VITE_API_URL}${url}`.

### 3.6 `SalaResumo` (listagem)
```json
{
  "id": 3,
  "nome": "Laboratório 03",
  "tipo": "lab_informatica",
  "tipo_rotulo": "Laboratório de informática",
  "capacidade": 30,
  "localizacao": "Bloco B, térreo",
  "ativo": true,
  "foto_capa_url": "/uploads/salas/3/5b0d6f0e-8a1c-4c55-9a3b-1f2e3d4c5b6a.jpg",
  "equipamentos": [
    { "equipamento_id": 1, "nome": "Computador", "quantidade": 30, "especificacao": "i5, 16 GB RAM" },
    { "equipamento_id": 2, "nome": "Projetor", "quantidade": 1, "especificacao": null }
  ]
}
```
`foto_capa_url` = foto de menor `ordem` (desempate por `id`), ou `null`.

### 3.7 `SalaDetalhe`
Todos os campos de `SalaResumo` mais:
```json
{
  "descricao": "Laboratório usado pelas disciplinas de programação.",
  "fotos": [ /* Foto[], ordenadas por ordem, id */ ],
  "softwares": [ /* Software[], ordenados por nome */ ],
  "criado_em": "2026-08-01T09:00:00-03:00",
  "atualizado_em": "2026-08-10T16:30:00-03:00"
}
```
`equipamentos` (já presente no resumo) vem ordenado por nome.

### 3.8 `Equipamento`
```json
{ "id": 1, "nome": "Computador", "descricao": "Desktop para alunos" }
```

### 3.9 `HorarioAula`
```json
{
  "id": 5,
  "turno": "manha",
  "ordem": 3,
  "inicio": "09:30",
  "fim": "10:20",
  "dias_semana": [1, 2, 3, 4, 5, 6],
  "ativo": true
}
```

### 3.10 `Semestre`
```json
{ "id": 2, "nome": "2026-2", "data_inicio": "2026-08-03", "data_fim": "2026-12-19" }
```

### 3.11 `Reserva`
```json
{
  "id": 101,
  "sala": { "id": 3, "nome": "Laboratório 03", "tipo": "lab_informatica" },
  "professor": { "id": 7, "nome": "Maria Souza" },
  "data": "2026-09-15",
  "inicio": "07:30",
  "fim": "09:10",
  "horario_inicio_id": 1,
  "horario_fim_id": 2,
  "quantidade_aulas": 2,
  "status": "ativa",
  "observacao": "Programação I - ADS 1º sem.",
  "grupo_recorrencia_id": null,
  "criado_em": "2026-09-01T10:15:00-03:00",
  "cancelada_em": null,
  "cancelada_por": null,
  "motivo_cancelamento": null,
  "pode_cancelar": true
}
```
- `cancelada_por`: `PessoaResumo` ou `null`.
- `pode_cancelar`: calculado para o usuário do token. `false` para visitante; para professor, `true` só se for o dono, `status = ativa` e `agora < data + inicio`; para admin, `true` sempre que `status = ativa`.
- Para FullCalendar: `start = data + "T" + inicio`, `end = data + "T" + fim`.

### 3.12 `Conflito`
```json
{
  "data": "2026-09-22",
  "inicio": "07:30",
  "fim": "08:20",
  "reserva_id": 88,
  "sala_id": 3,
  "professor": { "id": 9, "nome": "João Lima" }
}
```

### 3.13 `GrupoRecorrencia`
```json
{
  "id": 14,
  "sala": { "id": 3, "nome": "Laboratório 03", "tipo": "lab_informatica" },
  "professor": { "id": 7, "nome": "Maria Souza" },
  "semestre": { "id": 2, "nome": "2026-2", "data_inicio": "2026-08-03", "data_fim": "2026-12-19" },
  "dia_semana": 2,
  "inicio": "07:30",
  "fim": "09:10",
  "criado_em": "2026-09-01T10:20:00-03:00",
  "total_ocorrencias": 15,
  "ocorrencias_ativas": 14
}
```

---

## 4. Rotas

Legenda de acesso: **público**, **professor** (professor ou admin), **admin**. Ver §1.3.
Erros comuns a toda rota protegida (`401 NAO_AUTENTICADO`, `403 SEM_PERMISSAO`) e a toda rota com corpo/parâmetros (`422 VALIDACAO`) não são repetidos em cada tabela.
`404 NAO_ENCONTRADO` vale para todo `{id}` inexistente.

### 4.1 Saúde e estáticos

| Método | Rota | Acesso | Resposta |
|---|---|---|---|
| GET | `/saude` | público | `200 {"status": "ok"}` (faz `SELECT 1` no banco; se falhar, `503 {"status": "erro"}`) |
| GET | `/uploads/{caminho}` | público | arquivo estático de `UPLOAD_DIR` (StaticFiles). |

### 4.2 Auth

#### `POST /auth/login` (público)
Corpo JSON (não é form OAuth2):
```json
{ "rm": "123456", "senha": "minhaSenha123" }
```
`200`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expira_em": "2026-09-01T18:15:00-03:00",
  "usuario": { /* Usuario */ }
}
```
Limites dos campos: §1.8.
Erros: `401 CREDENCIAIS_INVALIDAS` (RM inexistente, senha errada **ou conta inativa**: mesma mensagem "RM ou senha inválidos."), `429 MUITAS_TENTATIVAS` (ADR-0007):
- 5 falhas do mesmo **par (IP, RM)** em 5 min bloqueiam esse par por 5 min;
- 20 falhas do mesmo **IP** em 5 min (qualquer RM) bloqueiam o IP por 5 min;
- enquanto bloqueado, responde `429` mesmo com a senha certa; login certo zera as falhas daquele par.
O IP é o da conexão; `X-Forwarded-For` só vale vindo de proxy listado em `FORWARDED_ALLOW_IPS` (uvicorn).

JWT: HS256, segredo `JWT_SECRET`, expiração `JWT_EXPIRA_MINUTOS` (padrão 480). Claims: `sub` (id do professor, string), `papel`, `ver` (inteiro: `token_versao` da conta na emissão), `iat`, `exp`. A cada requisição o backend recarrega o professor do banco (papel e `ativo` valem do banco, não do token).

Revogação (ADR-0008): o token só vale se `ver` for igual ao `token_versao` atual da conta; token sem `ver` é inválido.
O backend incrementa `token_versao`, derrubando **todas** as sessões da conta, quando:
- a própria senha é trocada (`PUT /auth/me/senha`; a sessão atual recebe token novo na resposta);
- o admin redefine a senha (`PUT /professores/{id}/senha`);
- o admin muda o `papel` ou desativa a conta (`PUT /professores/{id}` com `papel` diferente do atual ou `ativo` de `true` para `false`).
Login, reativação e mudança de nome/e-mail não incrementam.

#### `GET /auth/me` (professor)
`200` → `Usuario`.

#### `PUT /auth/me/senha` (professor)
```json
{ "senha_atual": "minhaSenha123", "nova_senha": "novaSenha456" }
```
`200` com o **mesmo corpo do `POST /auth/login`** (`access_token`, `token_type`, `expira_em`, `usuario`): o token novo
substitui o da sessão atual; todos os tokens anteriores da conta, inclusive o usado nesta requisição, deixam de valer (ADR-0008).
(Até a 1.1 era `204`.) Erros: `422 SENHA_ATUAL_INCORRETA`; `422 VALIDACAO` se `nova_senha` fora de 8–128 caracteres (§1.8).
Erro não muda nada: `token_versao` e o token atual seguem valendo.

### 4.3 Salas

#### `GET /salas/tipos` (público)
`200`:
```json
[
  { "valor": "sala", "rotulo": "Sala de aula" },
  { "valor": "lab_informatica", "rotulo": "Laboratório de informática" },
  { "valor": "lab_ciencias", "rotulo": "Laboratório de ciências" },
  { "valor": "lab_outro", "rotulo": "Outro laboratório" },
  { "valor": "auditorio", "rotulo": "Auditório" },
  { "valor": "outro", "rotulo": "Outro" }
]
```

#### `GET /salas` (público)
Query (todas opcionais, combinadas com **E**; listas = parâmetro repetido):

| Parâmetro | Tipo | Efeito |
|---|---|---|
| `tipo` | string, repetível | `?tipo=lab_informatica&tipo=lab_ciencias` → tipo em qualquer um deles |
| `capacidade_min` | int ≥ 1 | `capacidade >= capacidade_min` |
| `equipamento_id` | int, repetível | sala possui **todos** os equipamentos listados |
| `software_id` | int, repetível | sala possui **todos** os softwares listados |
| `busca` | string | `ILIKE '%busca%'` em nome, descrição ou localização |
| `data` | date | junto com `horario_ids`: só salas **livres** nesse bloco |
| `horario_ids` | int, repetível | aulas do bloco (mesmas regras da reserva avulsa: §4.10 RN03) |
| `incluir_inativas` | bool | só tem efeito para admin; para os demais é ignorado (inativas nunca aparecem) |

- `data` sem `horario_ids` (ou o contrário) → `422 VALIDACAO`.
- Aulas inválidas para a data → `422 AULAS_NAO_SEGUIDAS` / `422 AULA_INVALIDA_NO_DIA`. Data passada **não** é erro aqui.
- Ordenação: `nome` ascendente.

`200` → `SalaResumo[]`.

Exemplo: `GET /salas?tipo=lab_informatica&capacidade_min=25&software_id=4&data=2026-09-15&horario_ids=1&horario_ids=2`

#### `GET /salas/{id}` (público)
`200` → `SalaDetalhe`. Sala inativa: `404` para visitante/professor; admin vê.

#### `GET /salas/{id}/disponibilidade?data=YYYY-MM-DD` (público)
Grade do dia para a sala: todas as aulas **ativas válidas no dia da semana de `data`**, ordenadas por turno e ordem.
`200`:
```json
{
  "sala_id": 3,
  "data": "2026-09-15",
  "dia_semana": 2,
  "aulas": [
    { "horario": { /* HorarioAula id 1 */ }, "livre": false, "passou": false,
      "reserva": { "id": 101, "professor": { "id": 7, "nome": "Maria Souza" }, "inicio": "07:30", "fim": "09:10" } },
    { "horario": { /* HorarioAula id 2 */ }, "livre": false, "passou": false,
      "reserva": { "id": 101, "professor": { "id": 7, "nome": "Maria Souza" }, "inicio": "07:30", "fim": "09:10" } },
    { "horario": { /* HorarioAula id 3 */ }, "livre": true, "passou": false, "reserva": null }
  ]
}
```
Cada item tem **sempre** os quatro campos: `horario`, `livre` (nenhuma reserva ativa sobrepõe a aula), `passou` (`agora >= data + horario.inicio`, relógio do servidor, §1.7; vale também para aulas ocupadas) e `reserva` (a reserva ativa que ocupa, ou `null`). Domingo sem aulas → `aulas: []`. Sala inativa → `404` (exceto admin).

#### `POST /salas` (admin)
```json
{
  "nome": "Laboratório 03",
  "tipo": "lab_informatica",
  "descricao": "Laboratório usado pelas disciplinas de programação.",
  "capacidade": 30,
  "localizacao": "Bloco B, térreo",
  "ativo": true
}
```
Obrigatórios: `nome` (1–80), `tipo`, `capacidade` (> 0). Opcionais: `descricao`, `localizacao` (≤ 120), `ativo` (padrão `true`).
`201` → `SalaDetalhe`. Erros: `409 NOME_DUPLICADO`.

#### `PUT /salas/{id}` (admin)
Mesmo corpo do `POST` (substituição completa dos campos básicos; equipamentos, softwares e fotos têm rotas próprias), mas com `ativo` **obrigatório** (§1.6). Ativar/desativar = `PUT` completo com `ativo` trocado.
`200` → `SalaDetalhe`. Erros: `409 NOME_DUPLICADO`.

#### `DELETE /salas/{id}` (admin)
`204`. Apaga fotos (registros e arquivos) e associações. Erros: `409 SALA_COM_RESERVAS` (existe qualquer reserva, de qualquer status: desative com `ativo=false`).

#### `PUT /salas/{id}/equipamentos` (admin)
Substitui **toda** a lista de equipamentos da sala.
```json
[
  { "equipamento_id": 1, "quantidade": 30, "especificacao": "i5, 16 GB RAM" },
  { "equipamento_id": 2, "quantidade": 1, "especificacao": null }
]
```
`quantidade` ≥ 1 (padrão 1). `[]` remove todos. `200` → `SalaDetalhe`.
Erros: `404 NAO_ENCONTRADO` (equipamento inexistente), `422 VALIDACAO` (equipamento repetido).

#### `PUT /salas/{id}/softwares` (admin)
```json
{ "software_ids": [4, 5, 9] }
```
Substitui toda a lista. Ids repetidos são ignorados (a lista é um conjunto; diferente de equipamentos, onde cada item traz quantidade e a repetição é ambígua). `200` → `SalaDetalhe`. Erros: `404 NAO_ENCONTRADO` (software inexistente).

### 4.4 Fotos

Formatos aceitos: JPEG, PNG, WebP, conferidos pelo conteúdo (assinatura), não só pela extensão/`Content-Type`. Tamanho máximo `UPLOAD_MAX_MB` (padrão 5). Arquivo salvo como `UPLOAD_DIR/salas/{sala_id}/{uuid4}.{jpg|png|webp}`.

#### `GET /salas/{id}/fotos` (público)
`200` → `Foto[]` ordenadas por `ordem`, `id`.

#### `POST /salas/{id}/fotos` (admin)
`multipart/form-data`: `arquivo` (file, obrigatório), `legenda` (texto ≤ 200, opcional). Uma foto por requisição (Pixel envia várias em sequência).
`201` → `Foto` com `ordem = (maior ordem da sala) + 1`.
Erros: `413 ARQUIVO_GRANDE`, `415 TIPO_ARQUIVO_INVALIDO`.

#### `PATCH /salas/{id}/fotos/{foto_id}` (admin)
```json
{ "legenda": "Nova legenda" }
```
`legenda` ausente, `null` ou vazia remove a legenda. `200` → `Foto`. Foto de outra sala → `404`.

#### `DELETE /salas/{id}/fotos/{foto_id}` (admin)
`204`. Apaga registro e arquivo.

#### `PUT /salas/{id}/fotos/ordem` (admin)
```json
{ "foto_ids": [14, 12, 13] }
```
Deve conter **exatamente** os ids das fotos da sala, sem repetição; grava `ordem = posição (1..n)`.
`200` → `Foto[]` na nova ordem. Erros: `422 ORDEM_FOTOS_INVALIDA`.

### 4.5 Equipamentos

| Método | Rota | Acesso | Corpo | Resposta | Erros |
|---|---|---|---|---|---|
| GET | `/equipamentos` | público | query `busca` opcional | `200 Equipamento[]` (por nome) | |
| GET | `/equipamentos/{id}` | público | | `200 Equipamento` | |
| POST | `/equipamentos` | admin | `{"nome": "Projetor", "descricao": null}` | `201 Equipamento` | `409 NOME_DUPLICADO` |
| PUT | `/equipamentos/{id}` | admin | idem POST | `200 Equipamento` | `409 NOME_DUPLICADO` |
| DELETE | `/equipamentos/{id}` | admin | | `204` (remove também das salas) | |

`nome` obrigatório, 1–80.

### 4.6 Softwares

| Método | Rota | Acesso | Corpo | Resposta | Erros |
|---|---|---|---|---|---|
| GET | `/softwares` | público | query `busca`, `categoria` opcionais | `200 Software[]` (por nome, versão) | |
| GET | `/softwares/categorias` | público | | `200 ["Banco de dados", "IDE", ...]` (distintas, não nulas, ordenadas) | |
| GET | `/softwares/{id}` | público | | `200 Software` | |
| POST | `/softwares` | admin | `{"nome": "PostgreSQL", "versao": "16", "categoria": "Banco de dados"}` | `201 Software` | `409 NOME_DUPLICADO` (mesmo nome+versão) |
| PUT | `/softwares/{id}` | admin | idem POST | `200 Software` | `409 NOME_DUPLICADO` |
| DELETE | `/softwares/{id}` | admin | | `204` (remove também das salas) | |

`nome` obrigatório (1–80); `versao` (≤ 40) e `categoria` (≤ 60) opcionais.

### 4.7 Professores (admin)

Todas as rotas desta seção: **admin**.

#### `GET /professores`
Query opcional: `busca` (nome ou RM, ILIKE), `papel`, `ativo` (bool). `200` → `Usuario[]` por nome.

#### `GET /professores/{id}`
`200` → `Usuario`.

#### `POST /professores`
```json
{ "rm": "123456", "nome": "Maria Souza", "email": null, "senha": "senhaInicial1", "papel": "professor" }
```
`rm` regex `^[A-Za-z0-9]{3,20}$`; `senha` 8–128 (§1.8); `papel` padrão `professor`; `email` opcional (formato e-mail). Conta nasce `ativo = true`.
`201` → `Usuario`. Erros: `409 RM_DUPLICADO`.

#### `PUT /professores/{id}`
```json
{ "nome": "Maria Souza", "email": "maria@fatec.sp.gov.br", "papel": "admin", "ativo": true }
```
Substituição (§1.6): `nome`, `papel` e `ativo` **obrigatórios**; `email` opcional (omitido ou `null` → grava `null`). Pixel envia sempre os quatro.
RM não é editável. `200` → `Usuario`.
Erros: `422 OPERACAO_EM_SI_MESMO` (admin tentando se desativar ou tirar o próprio papel admin).
Mudar `papel` ou passar `ativo` de `true` para `false` encerra todas as sessões da conta editada (§4.2, ADR-0008).

#### `PUT /professores/{id}/senha`
```json
{ "nova_senha": "outraSenha789" }
```
`204`. (Redefinição pelo admin; não pede senha atual. `nova_senha` 8–128.) Encerra todas as sessões da conta
(§4.2, ADR-0008). Se `{id}` for o próprio admin, a sessão dele também cai e ele precisa entrar de novo; para trocar a
própria senha mantendo a sessão, use `PUT /auth/me/senha`.

#### `DELETE /professores/{id}`
`204`. Erros: `409 PROFESSOR_COM_RESERVAS` (a conta aparece em alguma reserva ou grupo de recorrência, como professor, `criado_por` ou `cancelada_por`, de qualquer status: desative), `422 OPERACAO_EM_SI_MESMO`.

### 4.8 Horários de aula

#### `GET /horarios` (público)
Query opcional: `dia_semana` (1–7: só aulas que valem nesse dia), `turno`, `incluir_inativos` (só admin; ignorado para os demais).
`200` → `HorarioAula[]` ordenados por turno (manha, tarde, noite) e `ordem`.

#### `GET /horarios/{id}` (público)
`200` → `HorarioAula`.

#### `POST /horarios` (admin)
```json
{ "turno": "manha", "ordem": 3, "inicio": "09:30", "fim": "10:20", "dias_semana": [1,2,3,4,5,6], "ativo": true }
```
`201` → `HorarioAula`.
Erros: `409 ORDEM_DUPLICADA` (turno+ordem já existe), `409 HORARIO_SOBREPOSTO` (sobrepõe outra aula ativa que vale em algum dia em comum), `422 VALIDACAO` (`fim <= inicio`, dias fora de 1–7, lista vazia).

#### `PUT /horarios/{id}` (admin)
Mesmo corpo, com `ativo` **obrigatório** (§1.6); mesmas regras. Não altera reservas existentes (elas guardam `inicio`/`fim`). `200` → `HorarioAula`.

#### `DELETE /horarios/{id}` (admin)
`204`. Erros: `409 HORARIO_EM_USO` (a aula é `horario_inicio_id` ou `horario_fim_id` de alguma reserva: use `ativo=false`).
A aula do meio de um bloco de 3+ aulas não é referenciada por FK e **pode** ser excluída; a reserva continua válida
porque guarda `inicio`/`fim` (ADR-0002).

### 4.9 Semestres

| Método | Rota | Acesso | Corpo | Resposta | Erros |
|---|---|---|---|---|---|
| GET | `/semestres` | público | | `200 Semestre[]` (por `data_inicio` desc) | |
| GET | `/semestres/atual` | público | | `200 Semestre` que contém hoje; se nenhum, o próximo que começa depois de hoje | `404 NAO_ENCONTRADO` |
| GET | `/semestres/{id}` | público | | `200 Semestre` | |
| POST | `/semestres` | admin | `{"nome": "2026-2", "data_inicio": "2026-08-03", "data_fim": "2026-12-19"}` | `201 Semestre` | `409 NOME_DUPLICADO`, `409 SEMESTRE_SOBREPOSTO`, `422 VALIDACAO` (fim ≤ início) |
| PUT | `/semestres/{id}` | admin | idem POST | `200 Semestre` | idem POST |
| DELETE | `/semestres/{id}` | admin | | `204` | `409 SEMESTRE_EM_USO` (há grupo de recorrência) |

### 4.10 Reservas

#### Regras comuns de criação
- **RN03 aulas seguidas** (`horario_ids`): lista não vazia, sem repetição (senão `422 VALIDACAO`); todas existentes (`404`), ativas e do **mesmo turno** com `ordem` consecutiva (senão `422 AULAS_NAO_SEGUIDAS`); todas valem no dia da semana da data (senão `422 AULA_INVALIDA_NO_DIA`). A ordem dos ids no array não importa. `inicio` = início da aula de menor ordem; `fim` = fim da de maior ordem.
- Sala inexistente → `404`; inativa → `422 SALA_INATIVA`.
- `data + inicio <= agora` → `422 DATA_PASSADA`.
- `professor_id` no corpo: só admin (reserva em nome do professor; deve existir → `404`, e estar ativo → `422 PROFESSOR_INATIVO`). Professor que envia `professor_id` → `403 SEM_PERMISSAO`. Ausente → dono é o usuário do token. `criado_por_id` é sempre o usuário do token.
- Conflito com reserva ativa (service ou constraint) → `409 CONFLITO_RESERVA` com `conflitos`.
- `observacao` opcional, ≤ 200.

#### `POST /reservas` (professor): reserva avulsa
```json
{ "sala_id": 3, "data": "2026-09-15", "horario_ids": [1, 2], "observacao": "Programação I - ADS 1º sem." }
```
`201` → `Reserva`.
Exemplo de conflito `409`:
```json
{
  "detail": "Sala não disponível neste horário.",
  "codigo": "CONFLITO_RESERVA",
  "conflitos": [
    { "data": "2026-09-15", "inicio": "08:20", "fim": "09:10", "reserva_id": 77, "sala_id": 3,
      "professor": { "id": 9, "nome": "João Lima" } }
  ]
}
```

#### `POST /reservas/recorrentes/previa` (professor): não grava nada
```json
{ "sala_id": 3, "data_inicio": "2026-09-15", "horario_ids": [1, 2] }
```
(`professor_id` opcional, mesmas regras; não afeta o resultado, só é validado.)
Série: `data_inicio`, `+7`, `+14`, … até `semestre.data_fim` inclusive, onde `semestre` contém `data_inicio`.
- As regras comuns (aulas, sala ativa, `DATA_PASSADA`) são avaliadas sobre `data_inicio`, **na prévia e na
  confirmação**. Se a aula de hoje já começou, a série tem de começar na semana seguinte.
- `data_inicio` **não** precisa estar livre: se estiver ocupada, aparece na prévia com `livre: false`, e o cliente
  simplesmente não a envia em `datas`. Por isso, ao montar a recorrência, a interface pode deixar escolher aulas
  ocupadas na primeira data.
`200`:
```json
{
  "sala": { "id": 3, "nome": "Laboratório 03", "tipo": "lab_informatica" },
  "semestre": { "id": 2, "nome": "2026-2", "data_inicio": "2026-08-03", "data_fim": "2026-12-19" },
  "dia_semana": 2,
  "inicio": "07:30",
  "fim": "09:10",
  "horario_ids": [1, 2],
  "ocorrencias": [
    { "data": "2026-09-15", "livre": true,  "conflitos": [] },
    { "data": "2026-09-22", "livre": false, "conflitos": [ /* Conflito[] */ ] },
    { "data": "2026-09-29", "livre": true,  "conflitos": [] }
  ],
  "total": 14,
  "livres": 13,
  "em_conflito": 1
}
```
Erros: regras comuns (exceto conflito, que aparece nas ocorrências), `422 SEM_SEMESTRE` (nenhum semestre contém `data_inicio`).
Validade das aulas no dia da semana é a mesma em todas as datas da série (mesmo dia da semana).

#### `POST /reservas/recorrentes` (professor): confirma
```json
{
  "sala_id": 3,
  "data_inicio": "2026-09-15",
  "horario_ids": [1, 2],
  "datas": ["2026-09-15", "2026-09-29", "2026-10-06"],
  "observacao": "Programação I - ADS 1º sem."
}
```
- `datas`: não vazia, sem repetição; cada uma deve pertencer à série da prévia (senão `422 DATA_FORA_DA_SERIE`). Normalmente Pixel envia as `livres` da prévia, permitindo ao professor desmarcar outras. `datas` não precisa conter `data_inicio`.
- O **dono do grupo** é `grupos_recorrencia.professor_id` (o professor da reserva), não `criado_por_id`: é ele quem vê e cancela o grupo, mesmo quando foi o admin que criou.
- Tudo numa transação: cria 1 `grupos_recorrencia` + 1 `reservas` por data. Se **qualquer** data conflitar → nada é gravado, `409 CONFLITO_RESERVA` com **todos** os conflitos encontrados (o cliente refaz a prévia).

`201`:
```json
{
  "grupo": { /* GrupoRecorrencia */ },
  "reservas": [ /* Reserva[] ordenadas por data */ ]
}
```
Erros: regras comuns, `422 SEM_SEMESTRE`, `422 DATA_FORA_DA_SERIE`, `409 CONFLITO_RESERVA`.

#### `GET /reservas` (público): agenda
Exatamente **um** dos modos de período é obrigatório:
- `mes=YYYY-MM`, ou
- `data=YYYY-MM-DD`, ou
- `de=YYYY-MM-DD&ate=YYYY-MM-DD` (inclusivos, `ate >= de`, no máximo **62 dias contando as duas pontas**, ou seja `ate - de <= 61`; ex.: `de=2026-09-01&ate=2026-11-01` vale, `ate=2026-11-02` não).

Nenhum modo, mais de um, só `de` ou só `ate`, `ate < de`, intervalo acima de 62 dias ou `mes` fora do formato `AAAA-MM` → `422 INTERVALO_INVALIDO`.
`data`, `de` ou `ate` que não são datas válidas → `422 VALIDACAO` (erro de tipo do parâmetro, com `erros`).
A maior visão do FullCalendar (mês, 6 semanas) tem 42 dias, dentro do limite.
Filtros opcionais: `sala_id` (repetível), `professor_id`, `status` = `ativa` (padrão) | `cancelada` | `todas`.
Ordenação: `data`, `inicio`, nome da sala.
`200` → `Reserva[]`. (Nota Pixel: FullCalendar entrega `end` exclusivo; envie `ate = end - 1 dia`.)

#### `GET /reservas/minhas` (professor)
Reservas em que `professor_id` = usuário do token.
Query: `periodo` = `futuras` (padrão: ainda não terminaram, `data + fim > agora`) | `passadas` | `todas`; `status` = `ativa` (padrão) | `cancelada` | `todas`.
Ordenação: `futuras` ascendente; `passadas` e `todas` descendente (data, inicio).
`200` → `Reserva[]`.

#### `GET /reservas/{id}` (público)
`200` → `Reserva`.

#### `GET /reservas/grupos/{grupo_id}` (professor: dono do grupo; admin: qualquer)
`200`:
```json
{ "grupo": { /* GrupoRecorrencia */ }, "reservas": [ /* Reserva[] todas, incl. canceladas, por data */ ] }
```
Professor que não é dono → `403 SEM_PERMISSAO`.

#### `POST /reservas/{id}/cancelar` (professor: só as próprias; admin: qualquer)
Corpo opcional:
```json
{ "motivo": "Aula remanejada" }
```
`200` → `Reserva` atualizada (`status = cancelada`, `cancelada_em`, `cancelada_por`, `motivo_cancelamento`).
Erros: `403 SEM_PERMISSAO` (professor, reserva de outro), `409 RESERVA_JA_CANCELADA`, `422 RESERVA_JA_INICIADA` (professor e `agora >= data + inicio`; admin nunca recebe esse erro).

#### `POST /reservas/grupos/{grupo_id}/cancelar` (professor: dono; admin: qualquer)
Corpo opcional `{ "motivo": "..." }`. Cancela todas as ocorrências do grupo com `status = ativa` e `data + inicio > agora` (vale também para admin). A contagem que o cliente mostra antes de confirmar é estimativa (§1.7); vale a `canceladas` da resposta.
`200`:
```json
{ "grupo_recorrencia_id": 14, "canceladas": 9, "reservas_ids": [120, 121, 122, 123, 124, 125, 126, 127, 128] }
```
Sem nada a cancelar → `200` com `canceladas: 0`. Erros: `403 SEM_PERMISSAO`.

---

## 5. Matriz de permissões

| Rota | Público | Professor | Admin |
|---|:-:|:-:|:-:|
| `GET /saude`, `GET /uploads/*` | ✔ | ✔ | ✔ |
| `POST /auth/login` | ✔ | ✔ | ✔ |
| `GET /auth/me`, `PUT /auth/me/senha` | | ✔ | ✔ |
| `GET /salas*` (tipos, lista, detalhe, disponibilidade, fotos) | ✔ (só ativas) | ✔ (só ativas) | ✔ (+ inativas) |
| `POST/PUT/DELETE /salas*`, fotos, associações | | | ✔ |
| `GET /equipamentos*`, `GET /softwares*`, `GET /horarios*`, `GET /semestres*` | ✔ | ✔ | ✔ |
| `POST/PUT/DELETE` equipamentos, softwares, horários, semestres | | | ✔ |
| `/professores*` | | | ✔ |
| `GET /reservas`, `GET /reservas/{id}` | ✔ | ✔ | ✔ |
| `GET /reservas/minhas` | | ✔ | ✔ |
| `POST /reservas`, `POST /reservas/recorrentes*` | | ✔ (dono = token) | ✔ (pode `professor_id`) |
| `GET /reservas/grupos/{id}` | | ✔ (dono) | ✔ |
| `POST /reservas/{id}/cancelar` | | ✔ (dono, antes do início) | ✔ (sempre) |
| `POST /reservas/grupos/{id}/cancelar` | | ✔ (dono, futuras) | ✔ (futuras) |

---

## 6. Catálogo de códigos de erro

| HTTP | `codigo` | Quando |
|---|---|---|
| 400 | `REQUISICAO_INVALIDA` | Corpo que o framework não consegue ler (ex.: multipart malformado) |
| 401 | `NAO_AUTENTICADO` | Token ausente/inválido/expirado/revogado ou conta inativa em rota protegida |
| 401 | `CREDENCIAIS_INVALIDAS` | Login com RM/senha errados ou conta inativa |
| 403 | `SEM_PERMISSAO` | Papel insuficiente; reserva/grupo de outro professor; professor enviando `professor_id` |
| 404 | `NAO_ENCONTRADO` | Recurso inexistente (ou sala inativa para não-admin); rota inexistente |
| 405 | `METODO_NAO_PERMITIDO` | Rota existe, mas não com esse método |
| 409 | `CONFLITO_RESERVA` | Sobreposição com reserva ativa (traz `conflitos`) |
| 409 | `RESERVA_JA_CANCELADA` | Cancelar reserva já cancelada |
| 409 | `NOME_DUPLICADO` | Nome único repetido (sala, equipamento, software nome+versão, semestre) |
| 409 | `RM_DUPLICADO` | RM já cadastrado |
| 409 | `SALA_COM_RESERVAS` | Excluir sala com reservas |
| 409 | `PROFESSOR_COM_RESERVAS` | Excluir professor com reservas |
| 409 | `ORDEM_DUPLICADA` | Horário com turno+ordem repetidos |
| 409 | `HORARIO_SOBREPOSTO` | Horário sobrepõe outro ativo em dia comum |
| 409 | `HORARIO_EM_USO` | Excluir horário referenciado por reserva |
| 409 | `SEMESTRE_SOBREPOSTO` | Semestres com datas sobrepostas |
| 409 | `SEMESTRE_EM_USO` | Excluir semestre com grupo de recorrência |
| 413 | `ARQUIVO_GRANDE` | Foto acima de `UPLOAD_MAX_MB` |
| 415 | `TIPO_ARQUIVO_INVALIDO` | Foto que não é JPEG/PNG/WebP |
| 422 | `VALIDACAO` | Erro de schema/parâmetro (traz `erros`) |
| 422 | `DATA_PASSADA` | Início da reserva já passou |
| 422 | `AULAS_NAO_SEGUIDAS` | Aulas de turnos diferentes, com buraco na ordem, ou inativas |
| 422 | `AULA_INVALIDA_NO_DIA` | Aula não vale no dia da semana da data |
| 422 | `SALA_INATIVA` | Reserva em sala inativa |
| 422 | `PROFESSOR_INATIVO` | Admin reservando para conta inativa |
| 422 | `SEM_SEMESTRE` | Recorrência sem semestre contendo `data_inicio` |
| 422 | `DATA_FORA_DA_SERIE` | Data enviada não pertence à série semanal |
| 422 | `RESERVA_JA_INICIADA` | Professor cancelando reserva já iniciada |
| 422 | `INTERVALO_INVALIDO` | Período de `GET /reservas` ausente, ambíguo ou > 62 dias |
| 422 | `ORDEM_FOTOS_INVALIDA` | Lista de reordenação não bate com as fotos da sala |
| 422 | `SENHA_ATUAL_INCORRETA` | Troca de senha com senha atual errada |
| 422 | `OPERACAO_EM_SI_MESMO` | Admin desativando, rebaixando ou excluindo a si mesmo |
| 429 | `MUITAS_TENTATIVAS` | Limite de tentativas de login (ADR-0007) |
| 4xx | `ERRO_HTTP` | Outro erro HTTP gerado pelo framework, sem código próprio (reserva; não deve ocorrer no uso normal) |
| 500 | `ERRO_INTERNO` | Erro inesperado |

Respostas `503` só existem em `GET /saude` (corpo `{"status": "erro"}`, fora do envelope).

---

## 7. Histórico de mudanças

### 1.2 (2026-11-12): revogação de tokens (ticket 41, ADR-0008)
Mudanças que **exigem código**:
- Modelo: coluna `professores.token_versao integer NOT NULL DEFAULT 0`, migration `0002_token_versao` (§2). Forge (ticket 41).
- JWT ganha a claim `ver`; token sem `ver` ou com `ver` diferente de `token_versao` → inválido (§1.3, §4.2). Forge (ticket 41).
  Na implantação, todos os tokens antigos caem: cada usuário entra de novo uma vez.
- `token_versao` incrementa na troca/redefinição de senha, na mudança de `papel` e na desativação (§4.2, §4.7). Forge (ticket 41).
- **`PUT /auth/me/senha` passa de `204` para `200`** com o corpo do login (token novo para a sessão atual). Forge (ticket 41) e Pixel (ticket 46), juntos.
- `PUT /professores/{id}/senha` no próprio admin derruba a sessão dele. Pixel trata (ticket 46).

### 1.1 (2026-11-12): triagem do ticket 29 e revisão arquitetural
Mudanças que **exigem código** (ordens 30–37):
- `PUT /salas/{id}` e `PUT /horarios/{id}`: `ativo` passa a ser obrigatório (§1.6). Pixel já envia; Forge ajusta o schema (ticket 32).
- Login: limite por par (IP, RM) mais teto por IP (§4.2, ADR-0007). Forge (ticket 31).
- CORS em todas as respostas de erro (§1.5). Forge (ticket 30).
- Seed: semestres também só com a tabela vazia (ADR-0006). Forge (ticket 34).

Esclarecimentos (o backend já se comporta assim; só passou a estar escrito):
- §1.2 segundos descartados; §1.4 e §6 códigos genéricos `REQUISICAO_INVALIDA`, `METODO_NAO_PERMITIDO`, `ERRO_HTTP`.
- §1.6 semântica de `PUT`; §1.7 relógio do servidor como referência; §1.8 limites de RM/senha.
- §4.3 `passou` sempre presente; `software_ids` repetidos ignorados. §4.4 legenda vazia remove.
- §4.7 `PUT /professores` (obrigatórios) e vínculos que impedem excluir professor.
- §4.8 `HORARIO_EM_USO` só para aulas referenciadas por FK.
- §4.10 `DATA_PASSADA` sobre `data_inicio` na recorrência; `data_inicio` pode estar ocupada; dono do grupo;
  62 dias contando as duas pontas; formatos inválidos de `mes` vs. `data`/`de`/`ate`.
