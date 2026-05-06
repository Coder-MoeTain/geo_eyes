"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06
"""

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "migrations" / "001_initial.sql"
    op.execute(sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Destructive rollback intentionally omitted for safety.
    pass
