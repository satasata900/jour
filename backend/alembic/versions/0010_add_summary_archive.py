"""Add summary_archive table.

Revision ID: 0010_add_summary_archive
Revises: 0009_add_feed_staging
Create Date: 2026-02-02
"""

from alembic import op

revision = "0010_add_summary_archive"
down_revision = "0009_add_feed_staging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS summary_archive (
            id BIGSERIAL PRIMARY KEY,
            period_type summary_period NOT NULL,
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_summary_archive_period UNIQUE (period_type, period_start, period_end)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_summary_archive_period_type ON summary_archive (period_type);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_summary_archive_period_end ON summary_archive (period_end);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS summary_archive;")
