"""add agent profiles

Revision ID: 0005_add_agent_profiles
Revises: 0004_add_summaries
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op

revision = "0005_add_agent_profiles"
down_revision = "0004_add_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_profiles (
            id BIGSERIAL PRIMARY KEY,
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            agent_type TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            user_prompt TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (key)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_profiles_type_active ON agent_profiles (agent_type, is_active);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_profiles;")
