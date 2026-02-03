from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


user_role_enum = ENUM("admin", "journalist", name="user_role", create_type=False)
platform_enum = ENUM(
    "whatsapp", "telegram", "rss", name="platform_type", create_type=False
)
summary_period_enum = ENUM(
    "interval", "daily", "weekly", "monthly", name="summary_period", create_type=False
)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(Text, nullable=False, unique=True)
    display_name = Column(Text)
    password_hash = Column(Text, nullable=False)
    role = Column(user_role_enum, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    last_login_at = Column(DateTime(timezone=True))
    telegram_chat_id = Column(BigInteger, unique=True)
    telegram_username = Column(Text)
    telegram_link_token = Column(String(64), unique=True)
    telegram_linked_at = Column(DateTime(timezone=True))
    telegram_daily_enabled = Column(Boolean, nullable=False, server_default=text("false"))
    telegram_weekly_enabled = Column(Boolean, nullable=False, server_default=text("false"))
    telegram_monthly_enabled = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan", order_by="desc(ChatSession.updated_at)"
    )

    # Deprecated single-message history
    chat_history = relationship(
        "ChatHistory", back_populates="user", cascade="all, delete-orphan"
    )


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="chat_history")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True)
    session_id = Column(BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # user, model, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("platform", "identifier", name="uq_sources_platform_identifier"),
    )

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    platform = Column(platform_enum, nullable=False)
    identifier = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    schedule_interval_minutes = Column(
        SmallInteger, nullable=False, server_default=text("10")
    )
    config = Column(JSONB)
    labels = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::text[]"),
    )
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    news_items = relationship("NewsArchive", back_populates="source")


class NewsArchive(Base):
    __tablename__ = "news_archive"

    id = Column(BigInteger, primary_key=True)
    source_id = Column(BigInteger, ForeignKey("sources.id", ondelete="SET NULL"))
    source_name = Column(Text, nullable=False)
    platform = Column(platform_enum, nullable=False)
    source_message_id = Column(Text)
    author_name = Column(Text)
    content = Column(Text, nullable=False)
    clean_content = Column(Text)
    content_hash = Column(String(64))
    timestamp = Column(DateTime(timezone=True), nullable=False)
    importance_score = Column(SmallInteger)
    category = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source = relationship("Source", back_populates="news_items")


class NewsFeedStaging(Base):
    """Temporary staging table for incoming messages.
    
    Messages stay here until interval summary succeeds, then move to NewsArchive.
    This prevents excessive API usage by processing messages in batches.
    """
    __tablename__ = "news_feed_staging"

    id = Column(BigInteger, primary_key=True)
    source_id = Column(BigInteger, ForeignKey("sources.id", ondelete="SET NULL"))
    source_name = Column(Text, nullable=False)
    platform = Column(platform_enum, nullable=False)
    source_message_id = Column(Text)
    author_name = Column(Text)
    content = Column(Text, nullable=False)
    clean_content = Column(Text)
    content_hash = Column(String(64))
    timestamp = Column(DateTime(timezone=True), nullable=False)
    importance_score = Column(SmallInteger)
    category = Column(Text)
    is_news_related = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source = relationship("Source")


class Summary(Base):
    __tablename__ = "summaries"
    __table_args__ = (
        UniqueConstraint(
            "period_type",
            "period_start",
            "period_end",
            name="uq_summaries_period",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    period_type = Column(summary_period_enum, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    content = Column(Text, nullable=False)
    is_locked = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SummaryArchive(Base):
    __tablename__ = "summary_archive"
    __table_args__ = (
        UniqueConstraint(
            "period_type",
            "period_start",
            "period_end",
            name="uq_summary_archive_period",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    period_type = Column(summary_period_enum, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(BigInteger, primary_key=True)
    config_key = Column(Text, nullable=False, unique=True)
    config_value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    __table_args__ = (UniqueConstraint("key", name="uq_agent_profiles_key"),)

    id = Column(BigInteger, primary_key=True)
    key = Column(String(64), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    agent_type = Column(String(32), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    is_system = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
