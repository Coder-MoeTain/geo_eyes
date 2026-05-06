"""analytics and partitioning

Revision ID: 0002_analytics_partitioning
Revises: 0001_initial
Create Date: 2026-05-06
"""

from pathlib import Path

from alembic import op

revision = "0002_analytics_partitioning"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "migrations" / "002_analytics_and_partitioning.sql"
    op.execute(sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_mirror_detection_partitioned ON detections;")
    op.execute("DROP FUNCTION IF EXISTS mirror_detection_into_partitioned();")
    op.execute("DROP FUNCTION IF EXISTS ensure_detection_partition(timestamp);")
    op.execute("DROP TABLE IF EXISTS detections_partitioned CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS airport_activity_summary;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS detection_statistics;")
