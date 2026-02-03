"""add rss platform

Revision ID: 0006_add_rss_platform
Revises: 0005_add_agent_profiles
Create Date: 2026-01-17 00:00:00.000000
"""

from alembic import op

revision = "0006_add_rss_platform"
down_revision = "0005_add_agent_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'platform_type' AND e.enumlabel = 'rss'
            ) THEN
                ALTER TYPE platform_type ADD VALUE 'rss';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Downgrade not supported for ENUM value removal.
    pass
