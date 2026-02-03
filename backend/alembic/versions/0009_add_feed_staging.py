"""Add news_feed_staging table for temporary message storage.

Revision ID: 0009_add_feed_staging
Revises: 0008_add_post_agents
Create Date: 2026-01-31
"""

from alembic import op

revision = "0009_add_feed_staging"
down_revision = "0008_add_post_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_feed_staging (
            id BIGSERIAL PRIMARY KEY,
            source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
            source_name TEXT NOT NULL,
            platform platform_type NOT NULL,
            source_message_id TEXT,
            author_name TEXT,
            content TEXT NOT NULL,
            clean_content TEXT,
            content_hash VARCHAR(64),
            timestamp TIMESTAMPTZ NOT NULL,
            importance_score SMALLINT,
            category TEXT,
            is_news_related BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_timestamp ON news_feed_staging (timestamp);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_source ON news_feed_staging (source_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_hash ON news_feed_staging (content_hash);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS news_feed_staging;")
