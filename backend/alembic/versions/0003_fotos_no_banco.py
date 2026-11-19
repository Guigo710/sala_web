"""Fotos guardadas no banco, já reduzidas (ADR-0010, contrato 1.4).

Linhas antigas ficam com `conteudo` nulo até `python -m app.importar_fotos` trazer o arquivo do disco.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE fotos_sala ADD COLUMN conteudo bytea")
    op.execute("ALTER TABLE fotos_sala ADD COLUMN tipo_mime varchar(30)")
    op.execute("ALTER TABLE fotos_sala ADD COLUMN tamanho integer")
    # JPEG não comprime: guarda fora da linha (TOAST) sem tentar comprimir.
    op.execute("ALTER TABLE fotos_sala ALTER COLUMN conteudo SET STORAGE EXTERNAL")


def downgrade() -> None:
    # Volta ao esquema 0002. As fotos que só existem no banco (enviadas depois desta migration) perdem o
    # conteúdo; as antigas continuam no disco (a importação nunca apaga arquivos).
    op.execute("ALTER TABLE fotos_sala DROP COLUMN tamanho")
    op.execute("ALTER TABLE fotos_sala DROP COLUMN tipo_mime")
    op.execute("ALTER TABLE fotos_sala DROP COLUMN conteudo")
