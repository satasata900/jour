"""Add summary lock flag.

Revision ID: 0017_summary_lock
Revises: 0016_post_casual_prompt
Create Date: 2026-02-03
"""

from alembic import op

revision = "0017_summary_lock"
down_revision = "0016_post_casual_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE summaries
        ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE summaries DROP COLUMN IF EXISTS is_locked;")
