"""add labels to sources

Revision ID: 0003_add_source_labels
Revises: 0002_add_author_name
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op

revision = "0003_add_source_labels"
down_revision = "0002_add_author_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS labels TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE sources DROP COLUMN IF EXISTS labels;")
