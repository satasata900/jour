"""Add user admin fields.

Revision ID: 0018_user_admin_fields
Revises: 0017_summary_lock
Create Date: 2026-02-03
"""

from alembic import op

revision = "0018_user_admin_fields"
down_revision = "0017_summary_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        DROP COLUMN IF EXISTS last_login_at,
        DROP COLUMN IF EXISTS is_active;
        """
    )
