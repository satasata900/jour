"""add summaries table

Revision ID: 0004_add_summaries
Revises: 0003_add_source_labels
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op

revision = "0004_add_summaries"
down_revision = "0003_add_source_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE summary_period AS ENUM ('daily', 'weekly', 'monthly');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries (
            id BIGSERIAL PRIMARY KEY,
            period_type summary_period NOT NULL,
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (period_type, period_start, period_end)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_summaries_period_type_start ON summaries (period_type, period_start);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS summaries;")
    op.execute("DROP TYPE IF EXISTS summary_period;")
