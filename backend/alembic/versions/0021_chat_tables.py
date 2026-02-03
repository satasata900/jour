"""Add chat history and session tables.

Revision ID: 0021_chat_tables
Revises: 0020_post_official_expand
Create Date: 2026-02-04
"""

from alembic import op

revision = "0021_chat_tables"
down_revision = "0020_post_official_expand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history (created_at);"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions (user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions (updated_at);"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages (session_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages (created_at);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages;")
    op.execute("DROP TABLE IF EXISTS chat_sessions;")
    op.execute("DROP TABLE IF EXISTS chat_history;")
