"""Add display name for users.

Revision ID: 0019_user_display_name
Revises: 0018_user_admin_fields
Create Date: 2026-02-03
"""

from alembic import op

revision = "0019_user_display_name"
down_revision = "0018_user_admin_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS display_name TEXT;
        """
    )
    op.execute(
        """
        UPDATE users
        SET display_name = COALESCE(
            NULLIF(display_name, ''),
            NULLIF(split_part(username, '@', 1), ''),
            username
        )
        WHERE display_name IS NULL OR display_name = '';
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS display_name;")
