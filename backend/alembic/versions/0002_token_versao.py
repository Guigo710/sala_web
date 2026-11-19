"""Versão do token por conta: revogação de sessões (ADR-0008, contrato 1.2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE professores ADD COLUMN token_versao integer NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE professores DROP COLUMN token_versao")
