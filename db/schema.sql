DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'journalist');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE platform_type AS ENUM ('whatsapp', 'telegram', 'rss');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE summary_period AS ENUM ('interval', 'daily', 'weekly', 'monthly');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE run_status AS ENUM ('running', 'success', 'failed', 'stopped');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE notification_status AS ENUM ('queued', 'sent', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE device_platform AS ENUM ('android', 'ios', 'web');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role user_role NOT NULL,
    telegram_chat_id BIGINT UNIQUE,
    telegram_username TEXT,
    telegram_link_token VARCHAR(64) UNIQUE,
    telegram_linked_at TIMESTAMPTZ,
    telegram_daily_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_weekly_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_monthly_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    platform platform_type NOT NULL,
    identifier TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    schedule_interval_minutes SMALLINT NOT NULL DEFAULT 10 CHECK (schedule_interval_minutes BETWEEN 1 AND 1440),
    config JSONB,
    labels TEXT[] NOT NULL DEFAULT '{}',
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, identifier)
);

CREATE INDEX IF NOT EXISTS idx_sources_platform_active ON sources (platform, is_active);
CREATE INDEX IF NOT EXISTS idx_sources_next_run ON sources (next_run_at);

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

CREATE INDEX IF NOT EXISTS idx_scraper_runs_source_id ON scraper_runs (source_id);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_status ON scraper_runs (status);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_started_at ON scraper_runs (started_at);

CREATE TABLE IF NOT EXISTS news_archive (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
    source_name TEXT NOT NULL,
    platform platform_type NOT NULL,
    source_message_id TEXT,
    author_name TEXT,
    content TEXT NOT NULL,
    clean_content TEXT,
    content_hash CHAR(64),
    timestamp TIMESTAMPTZ NOT NULL,
    importance_score SMALLINT CHECK (importance_score BETWEEN 1 AND 10),
    category TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_news_archive_timestamp ON news_archive (timestamp);
CREATE INDEX IF NOT EXISTS idx_news_archive_importance ON news_archive (importance_score);
CREATE INDEX IF NOT EXISTS idx_news_archive_time_importance ON news_archive (timestamp, importance_score);
CREATE INDEX IF NOT EXISTS idx_news_archive_platform_category ON news_archive (platform, category);
CREATE INDEX IF NOT EXISTS idx_news_archive_content_hash ON news_archive (content_hash);
CREATE INDEX IF NOT EXISTS idx_news_archive_source_id ON news_archive (source_id);
CREATE INDEX IF NOT EXISTS idx_news_archive_source_message ON news_archive (platform, source_message_id);

CREATE TABLE IF NOT EXISTS summaries (
    id BIGSERIAL PRIMARY KEY,
    period_type summary_period NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (period_type, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_summaries_period_type_start ON summaries (period_type, period_start);

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

CREATE INDEX IF NOT EXISTS idx_agent_profiles_type_active ON agent_profiles (agent_type, is_active);

CREATE TABLE IF NOT EXISTS chat_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history (created_at);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history (user_id);

CREATE TABLE IF NOT EXISTS system_config (
    id BIGSERIAL PRIMARY KEY,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_devices (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL UNIQUE,
    platform device_platform NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_devices_user_id ON user_devices (user_id);
CREATE INDEX IF NOT EXISTS idx_user_devices_active ON user_devices (is_active);

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

CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log (status);
CREATE INDEX IF NOT EXISTS idx_notification_log_created_at ON notification_log (created_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_user_id ON notification_log (user_id);
