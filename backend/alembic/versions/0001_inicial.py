"""Esquema inicial: btree_gist + todas as tabelas (contrato §2.1, ADR-0002/0003).

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# DDL copiado do contrato (docs/api-contrato.md §2.1). Nomes de constraints iguais.
DDL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE professores (
    id             serial PRIMARY KEY,
    rm             varchar(20)  NOT NULL UNIQUE,
    nome           varchar(120) NOT NULL,
    email          varchar(160),
    senha_hash     varchar(255) NOT NULL,
    papel          varchar(20)  NOT NULL DEFAULT 'professor'
                   CHECK (papel IN ('professor', 'admin')),
    ativo          boolean      NOT NULL DEFAULT true,
    criado_em      timestamptz  NOT NULL DEFAULT now(),
    atualizado_em  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE salas (
    id             serial PRIMARY KEY,
    nome           varchar(80)  NOT NULL UNIQUE,
    tipo           varchar(30)  NOT NULL
                   CHECK (tipo IN ('sala','lab_informatica','lab_ciencias','lab_outro','auditorio','outro')),
    descricao      text,
    capacidade     integer      NOT NULL CHECK (capacidade > 0),
    localizacao    varchar(120),
    ativo          boolean      NOT NULL DEFAULT true,
    criado_em      timestamptz  NOT NULL DEFAULT now(),
    atualizado_em  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE fotos_sala (
    id         serial PRIMARY KEY,
    sala_id    integer      NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    arquivo    varchar(255) NOT NULL UNIQUE,
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
    especificacao   varchar(255),
    PRIMARY KEY (sala_id, equipamento_id)
);

CREATE TABLE softwares (
    id         serial PRIMARY KEY,
    nome       varchar(80) NOT NULL,
    versao     varchar(40),
    categoria  varchar(60),
    CONSTRAINT uq_softwares_nome_versao UNIQUE NULLS NOT DISTINCT (nome, versao)
);

CREATE TABLE sala_softwares (
    sala_id      integer NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    software_id  integer NOT NULL REFERENCES softwares(id) ON DELETE CASCADE,
    PRIMARY KEY (sala_id, software_id)
);

CREATE TABLE horarios_aula (
    id           serial PRIMARY KEY,
    turno        varchar(10) NOT NULL CHECK (turno IN ('manha','tarde','noite')),
    ordem        smallint    NOT NULL CHECK (ordem > 0),
    inicio       time        NOT NULL,
    fim          time        NOT NULL,
    dias_semana  smallint[]  NOT NULL,
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
    nome         varchar(20) NOT NULL UNIQUE,
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
    inicio                time     NOT NULL,
    fim                   time     NOT NULL,
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
    CONSTRAINT ex_reservas_sem_sobreposicao
        EXCLUDE USING gist (sala_id WITH =, periodo WITH &&) WHERE (status = 'ativa')
);
CREATE INDEX ix_reservas_data            ON reservas (data);
CREATE INDEX ix_reservas_professor_data  ON reservas (professor_id, data);
CREATE INDEX ix_reservas_grupo           ON reservas (grupo_recorrencia_id);
"""

TABELAS = [
    "reservas",
    "grupos_recorrencia",
    "semestres",
    "horarios_aula",
    "sala_softwares",
    "softwares",
    "sala_equipamentos",
    "equipamentos",
    "fotos_sala",
    "salas",
    "professores",
]


def upgrade() -> None:
    op.execute(DDL)


def downgrade() -> None:
    for tabela in TABELAS:
        op.execute(f"DROP TABLE IF EXISTS {tabela}")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
