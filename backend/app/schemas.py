from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, conint


class Platform(str, Enum):
    whatsapp = "whatsapp"
    telegram = "telegram"
    rss = "rss"


class SummaryPeriod(str, Enum):
    interval = "interval"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class UserRole(str, Enum):
    admin = "admin"
    journalist = "journalist"


class AgentType(str, Enum):
    router = "router"
    monitor = "monitor"
    editor = "editor"
    search = "search"
    general = "general"
    custom = "custom"


class SearchProvider(str, Enum):
    searxng = "searxng"
    disabled = "disabled"


class LLMProvider(str, Enum):
    gemini = "gemini"
    openrouter = "openrouter"


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1)
    platform: Platform
    identifier: str = Field(..., min_length=1)
    is_active: bool = True
    schedule_interval_minutes: conint(ge=1, le=1440) = 10
    config: dict[str, Any] | None = None
    labels: list[str] = Field(default_factory=list)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: Platform
    identifier: str
    is_active: bool
    schedule_interval_minutes: int
    config: dict[str, Any] | None
    labels: list[str]
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    is_active: bool | None = None
    schedule_interval_minutes: conint(ge=1, le=1440) | None = None
    config: dict[str, Any] | None = None
    labels: list[str] | None = None


class NewsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None
    source_name: str
    platform: Platform
    source_message_id: str | None
    author_name: str | None
    content: str
    clean_content: str | None
    timestamp: datetime
    importance_score: int | None
    category: str | None
    created_at: datetime


class NewsCreate(BaseModel):
    source_id: int | None = None
    source_identifier: str | None = None
    source_name: str | None = None
    platform: Platform
    source_message_id: str | None = None
    author_name: str | None = None
    content: str = Field(..., min_length=1)
    clean_content: str | None = None
    content_hash: str | None = Field(None, min_length=64, max_length=64)
    timestamp: datetime
    importance_score: conint(ge=1, le=10) | None = None
    category: str | None = None


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_type: SummaryPeriod
    period_start: datetime
    period_end: datetime
    content: str
    created_at: datetime
    is_locked: bool | None = None


class SummaryUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class ChatHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    message: str
    response: str
    created_at: datetime


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None = None
    role: UserRole
    created_at: datetime
    is_active: bool | None = None
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    display_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3)
    display_name: str | None = Field(None, min_length=2)
    is_active: bool | None = None


class UserPasswordReset(BaseModel):
    password: str = Field(..., min_length=6)


class UserAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None = None
    role: UserRole
    created_at: datetime
    is_active: bool
    last_login_at: datetime | None = None
    session_count: int = 0
    message_count: int = 0
    last_session_at: datetime | None = None


class UserStatsRead(BaseModel):
    total_users: int
    active_users: int
    total_sessions: int
    total_messages: int


class UserListRead(BaseModel):
    items: list[UserAdminRead]
    total: int


class RegistrationStatusRead(BaseModel):
    enabled: bool


class RegistrationUpdate(BaseModel):
    enabled: bool


class TelegramPreferencesUpdate(BaseModel):
    daily_enabled: bool | None = None
    weekly_enabled: bool | None = None
    monthly_enabled: bool | None = None


class TelegramPreferencesRead(BaseModel):
    linked: bool
    chat_id: int | None = None
    username: str | None = None
    bot_username: str | None = None
    link_url: str | None = None
    daily_enabled: bool
    weekly_enabled: bool
    monthly_enabled: bool


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    user: UserRead


class AgentProfileBase(BaseModel):
    key: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str | None = None
    agent_type: AgentType
    system_prompt: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    is_active: bool = True
    is_system: bool = False


class AgentProfileCreate(AgentProfileBase):
    pass


class AgentProfileUpdate(BaseModel):
    key: str | None = Field(None, min_length=1)
    name: str | None = Field(None, min_length=1)
    description: str | None = None
    agent_type: AgentType | None = None
    system_prompt: str | None = Field(None, min_length=1)
    user_prompt: str | None = Field(None, min_length=1)
    is_active: bool | None = None
    is_system: bool | None = None


class AgentProfileRead(AgentProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class RetentionSettings(BaseModel):
    days: conint(ge=1, le=365)


class RetentionSettingsRead(BaseModel):
    days: int
    min_days: int
    max_days: int
    source: str


class ChatRetentionSettings(BaseModel):
    days: conint(ge=1, le=30)


class ChatRetentionSettingsRead(BaseModel):
    days: int
    min_days: int
    max_days: int
    source: str


class SettingsKeys(BaseModel):
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    tavily_api_key: str | None = None


class SettingsKeysUpdate(BaseModel):
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    tavily_api_key: str | None = None


class SettingsAI(BaseModel):
    gemini_api_version: str
    agent_llm_provider: LLMProvider
    summary_model: str
    agent_llm_model: str
    summary_timezone: str
    summary_run_interval_seconds: int
    summary_max_messages: int
    summary_max_chars: int


class SettingsAIUpdate(BaseModel):
    gemini_api_version: str | None = None
    agent_llm_provider: LLMProvider | None = None
    summary_model: str | None = None
    agent_llm_model: str | None = None
    summary_timezone: str | None = None
    summary_run_interval_seconds: conint(ge=60, le=86400) | None = None
    summary_max_messages: conint(ge=1, le=5000) | None = None
    summary_max_chars: conint(ge=1000, le=500000) | None = None


class SettingsSearch(BaseModel):
    provider: SearchProvider
    searxng_base_url: str
    searxng_timeout_seconds: conint(ge=3, le=60)
    searxng_max_results: conint(ge=1, le=50)
    searxng_language: str
    searxng_safe_search: conint(ge=0, le=2)
    searxng_time_range: str
    searxng_categories: str
    searxng_engines: str


class SettingsSearchUpdate(BaseModel):
    provider: SearchProvider | None = None
    searxng_base_url: str | None = None
    searxng_timeout_seconds: conint(ge=3, le=60) | None = None
    searxng_max_results: conint(ge=1, le=50) | None = None
    searxng_language: str | None = None
    searxng_safe_search: conint(ge=0, le=2) | None = None
    searxng_time_range: str | None = None
    searxng_categories: str | None = None
    searxng_engines: str | None = None


class SettingsTelegram(BaseModel):
    enabled: bool
    api_id: str | None = None
    api_hash: str | None = None
    phone_number: str | None = None
    session_name: str
    log_level: str
    include_private: bool
    log_groups: bool


class SettingsTelegramUpdate(BaseModel):
    enabled: bool | None = None
    api_id: str | None = None
    api_hash: str | None = None
    phone_number: str | None = None
    session_name: str | None = None
    log_level: str | None = None
    include_private: bool | None = None
    log_groups: bool | None = None


class SettingsWhatsApp(BaseModel):
    enabled: bool
    phone_number: str | None = None
    log_level: str


class SettingsWhatsAppUpdate(BaseModel):
    enabled: bool | None = None
    phone_number: str | None = None
    log_level: str | None = None


class SettingsTelegramBot(BaseModel):
    enabled: bool
    token: str | None = None
    username: str | None = None


class SettingsTelegramBotUpdate(BaseModel):
    enabled: bool | None = None
    token: str | None = None
    username: str | None = None


class SettingsRead(BaseModel):
    keys: SettingsKeys
    ai: SettingsAI
    search: SettingsSearch
    retention: RetentionSettingsRead
    chat_retention: ChatRetentionSettingsRead
    telegram: SettingsTelegram
    telegram_bot: SettingsTelegramBot
    whatsapp: SettingsWhatsApp


class SettingsUpdate(BaseModel):
    keys: SettingsKeysUpdate | None = None
    ai: SettingsAIUpdate | None = None
    search: SettingsSearchUpdate | None = None
    retention: RetentionSettings | None = None
    chat_retention: ChatRetentionSettings | None = None
    telegram: SettingsTelegramUpdate | None = None
    telegram_bot: SettingsTelegramBotUpdate | None = None
    whatsapp: SettingsWhatsAppUpdate | None = None


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead]


class ChatMessageCreate(BaseModel):
    role: str
    content: str


class NewChatSession(BaseModel):
    title: str | None = None
