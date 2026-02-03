"""init schema

Revision ID: 0001_init_schema
Revises: 
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op

revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE user_role AS ENUM ('admin', 'journalist');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE platform_type AS ENUM ('whatsapp', 'telegram');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE run_status AS ENUM ('running', 'success', 'failed', 'stopped');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE notification_status AS ENUM ('queued', 'sent', 'failed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE device_platform AS ENUM ('android', 'ios', 'web');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role user_role NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            platform platform_type NOT NULL,
            identifier TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            schedule_interval_minutes SMALLINT NOT NULL DEFAULT 10 CHECK (schedule_interval_minutes BETWEEN 1 AND 1440),
            config JSONB,
            last_run_at TIMESTAMPTZ,
            next_run_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (platform, identifier)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scraper_runs (
            id BIGSERIAL PRIMARY KEY,
            source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            status run_status NOT NULL DEFAULT 'running',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at TIMESTAMPTZ,
            items_fetched INTEGER NOT NULL DEFAULT 0 CHECK (items_fetched >= 0),
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_archive (
            id BIGSERIAL PRIMARY KEY,
            source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
            source_name TEXT NOT NULL,
            platform platform_type NOT NULL,
            source_message_id TEXT,
            content TEXT NOT NULL,
            clean_content TEXT,
            content_hash CHAR(64),
            timestamp TIMESTAMPTZ NOT NULL,
            importance_score SMALLINT CHECK (importance_score BETWEEN 1 AND 10),
            category TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            id BIGSERIAL PRIMARY KEY,
            config_key TEXT NOT NULL UNIQUE,
            config_value TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_devices (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            device_token TEXT NOT NULL UNIQUE,
            platform device_platform NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_seen_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            device_id BIGINT REFERENCES user_devices(id) ON DELETE SET NULL,
            news_id BIGINT REFERENCES news_archive(id) ON DELETE SET NULL,
            status notification_status NOT NULL DEFAULT 'queued',
            provider_message_id TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            sent_at TIMESTAMPTZ
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_sources_platform_active ON sources (platform, is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sources_next_run ON sources (next_run_at);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_scraper_runs_source_id ON scraper_runs (source_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_scraper_runs_status ON scraper_runs (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_scraper_runs_started_at ON scraper_runs (started_at);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_timestamp ON news_archive (timestamp);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_importance ON news_archive (importance_score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_time_importance ON news_archive (timestamp, importance_score);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_platform_category ON news_archive (platform, category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_content_hash ON news_archive (content_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_source_id ON news_archive (source_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_news_archive_source_message ON news_archive (platform, source_message_id);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_user_devices_user_id ON user_devices (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_devices_active ON user_devices (is_active);")

    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_created_at ON notification_log (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_user_id ON notification_log (user_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_log;")
    op.execute("DROP TABLE IF EXISTS user_devices;")
    op.execute("DROP TABLE IF EXISTS system_config;")
    op.execute("DROP TABLE IF EXISTS chat_history;")
    op.execute("DROP TABLE IF EXISTS news_archive;")
    op.execute("DROP TABLE IF EXISTS scraper_runs;")
    op.execute("DROP TABLE IF EXISTS sources;")
    op.execute("DROP TABLE IF EXISTS users;")

    op.execute("DROP TYPE IF EXISTS device_platform;")
    op.execute("DROP TYPE IF EXISTS notification_status;")
    op.execute("DROP TYPE IF EXISTS run_status;")
    op.execute("DROP TYPE IF EXISTS platform_type;")
    op.execute("DROP TYPE IF EXISTS user_role;")
