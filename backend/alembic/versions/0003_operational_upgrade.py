"""operational schema upgrade

Revision ID: 0003_operational_upgrade
Revises: 0002_analytics_partitioning
Create Date: 2026-05-06
"""

from pathlib import Path

from alembic import op

revision = "0003_operational_upgrade"
down_revision = "0002_analytics_partitioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "migrations" / "003_operational_upgrade.sql"
    op.execute(sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    pass
