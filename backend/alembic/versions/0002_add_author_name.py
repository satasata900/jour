"""add author_name to news_archive

Revision ID: 0002_add_author_name
Revises: 0001_init_schema
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op

revision = "0002_add_author_name"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE news_archive ADD COLUMN IF NOT EXISTS author_name TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE news_archive DROP COLUMN IF EXISTS author_name;")
