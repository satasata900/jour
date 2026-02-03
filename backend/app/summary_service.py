import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import func, text

from app import models
from app.database import SessionLocal

logger = logging.getLogger("summaries")

DEFAULT_GEMINI_SUMMARY_MODEL = "gemini-2.0-flash"
DEFAULT_OPENROUTER_SUMMARY_MODEL = "openrouter/auto"
DEFAULT_SUMMARY_PROVIDER = "openrouter"
DEFAULT_RUN_INTERVAL_SECONDS = 300
DEFAULT_MAX_MESSAGES = 200
DEFAULT_MAX_INPUT_CHARS = 120000
DEFAULT_CHAT_RETENTION_DAYS = 7
MIN_CHAT_RETENTION_DAYS = 1
MAX_CHAT_RETENTION_DAYS = 30
SUMMARY_ANCHOR_HOUR = 0
SUMMARY_ANCHOR_MINUTE = 0
INTERVAL_MINUTES = 30
WEEKLY_ANCHOR_WEEKDAY = 6
NO_MESSAGES_SUMMARY = "No messages received for this period."
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_TIMEOUT_SECONDS = 60

# OpenRouter fallback chain for summaries: try free models first, then cheap paid
OPENROUTER_FALLBACK_MODELS = [
    # === FREE MODELS (try first) - verified available ===
    "meta-llama/llama-3.3-70b-instruct:free",  # Meta Llama 3.3 70B - very capable
    "google/gemma-3-27b-it:free",              # Google Gemma 3 27B - excellent quality
    "qwen/qwen3-next-80b-a3b-instruct:free",   # Qwen 3 80B - large context
    "deepseek/deepseek-r1-0528:free",          # DeepSeek R1 - good for reasoning
    "nousresearch/hermes-3-llama-3.1-405b:free",  # Hermes 3 405B - powerful
    # === CHEAP PAID MODELS (fallback) ===
    "google/gemini-2.0-flash-001",              # $0.10/M input - fast and cheap
    "deepseek/deepseek-chat",                   # $0.14/M input - very cheap
    "anthropic/claude-3-haiku",                 # $0.25/M input - fast, reliable
]
_BULLET_RE = re.compile(r"^\s*(?:[-•*]|\d+[).\-])\s+\S+")

# Smart filtering patterns for news detection
# Casual chat patterns to filter out (not news-related)
CASUAL_CHAT_PATTERNS = [
    r"^(صباح|مساء)\s+(الخير|النور)",  # Morning/evening greetings
    r"^(السلام\s+عليكم|مرحبا|هلا|هاي|hi|hello)",  # Greetings
    r"^(شكرا|مشكور|الله\s+يعطيك)",  # Thanks
    r"^(ههه|😂|😅|🤣|لول|lol)",  # Laughter
    r"^(تمام|اوكي|ok|okay|👍)",  # Confirmations
    r"^@\w+\s*(تفضل|شوف|خذ)",  # Mentions with informal words
    r"^\s*[👍👎❤️🔥💯😊🙏]+\s*$",  # Emoji-only messages
    r"^(كيفك|شلونك|كيف\s+الحال)",  # How are you
    r"^\s*.{1,15}\s*$",  # Very short messages (less than 15 chars)
]

# News-related keywords that indicate important content
NEWS_KEYWORDS = [
    "عاجل", "خبر", "إعلان", "رسمي", "تصريح", "قرار", "حكومة", "وزارة",
    "رئيس", "وزير", "اتفاق", "مؤتمر", "بيان", "تقرير", "إحصائية",
    "اقتصاد", "سوق", "بورصة", "أسعار", "دولار", "نفط", "طاقة",
    "حرب", "سلام", "أمن", "جيش", "معركة", "هجوم", "دفاع",
    "انتخابات", "تصويت", "برلمان", "مجلس", "قانون", "تشريع",
    "breaking", "news", "official", "announcement", "report",
]

# Compile patterns for performance
_CASUAL_PATTERNS = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in CASUAL_CHAT_PATTERNS]
_NEWS_PATTERN = re.compile("|".join(NEWS_KEYWORDS), re.IGNORECASE | re.UNICODE)





def _normalize_model(model: str) -> str:
    normalized = model.strip()
    if normalized.startswith("models/"):
        return normalized.split("/", 1)[1]
    return normalized


def _get_api_version(value: str | None = None) -> str:
    api_version = (value or os.getenv("GEMINI_API_VERSION", "v1")).strip().lstrip("/")
    return api_version or "v1"


def _get_timezone(name: str | None = None) -> timezone:
    name = name or os.getenv("SUMMARY_TIMEZONE", "UTC")
    if name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown SUMMARY_TIMEZONE=%s; falling back to UTC.", name)
        return timezone.utc


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


def _parse_int_value(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _parse_bool_value(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_config_value(db, key: str, env_key: str, default: str | int) -> str | int:
    try:
        row = db.execute(
            text(
                "SELECT config_value FROM system_config WHERE config_key = :key LIMIT 1"
            ),
            {"key": key},
        ).fetchone()
    except Exception as exc:
        logger.warning("Config lookup failed for %s: %s", key, exc)
        row = None
    if row and row[0] is not None:
        return row[0]
    env_value = os.getenv(env_key)
    if env_value is not None and env_value != "":
        return env_value
    return default


def _get_string_setting(db, key: str, env_key: str, default: str) -> str:
    value = _get_config_value(db, key, env_key, default)
    return str(value) if value is not None else default


def _get_int_setting(
    db, key: str, env_key: str, default: int, min_value: int | None = None, max_value: int | None = None
) -> int:
    value = _parse_int_value(_get_config_value(db, key, env_key, default), default)
    if min_value is not None and value < min_value:
        return min_value
    if max_value is not None and value > max_value:
        return max_value
    return value


def _get_bool_setting(db, key: str, env_key: str, default: bool) -> bool:
    return _parse_bool_value(_get_config_value(db, key, env_key, default), default)


def _get_summary_provider(db) -> str:
    provider = _get_string_setting(
        db, "agent_llm_provider", "AGENT_LLM_PROVIDER", DEFAULT_SUMMARY_PROVIDER
    ).strip().lower()
    if provider not in {"openrouter", "gemini"}:
        return DEFAULT_SUMMARY_PROVIDER
    return provider


def _get_summary_model(db, provider: str) -> str:
    default = (
        DEFAULT_OPENROUTER_SUMMARY_MODEL
        if provider == "openrouter"
        else DEFAULT_GEMINI_SUMMARY_MODEL
    )
    model = _get_string_setting(db, "summary_model", "SUMMARY_MODEL", default).strip()
    if not model:
        model = default
    if provider == "openrouter":
        if model.startswith("gemini") or model.startswith("models/"):
            return default
        return model
    if "/" in model and not model.startswith("models/"):
        return default
    return _normalize_model(model)


def _get_openrouter_base_url() -> str:
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip()
    if not base_url:
        return DEFAULT_OPENROUTER_BASE_URL
    return base_url.rstrip("/")



def _get_chat_retention_days(db) -> int:
    value = _get_int_setting(
        db,
        "chat_retention_days",
        "CHAT_RETENTION_DAYS",
        DEFAULT_CHAT_RETENTION_DAYS,
        MIN_CHAT_RETENTION_DAYS,
        MAX_CHAT_RETENTION_DAYS,
    )
    if value < MIN_CHAT_RETENTION_DAYS:
        return MIN_CHAT_RETENTION_DAYS
    if value > MAX_CHAT_RETENTION_DAYS:
        return MAX_CHAT_RETENTION_DAYS
    return value


def _get_summary_interval_seconds() -> int:
    try:
        with SessionLocal() as db:
            return _get_int_setting(
                db,
                "summary_run_interval_seconds",
                "SUMMARY_RUN_INTERVAL_SECONDS",
                DEFAULT_RUN_INTERVAL_SECONDS,
                60,
                86400,
            )
    except Exception as exc:
        logger.warning("Summary interval lookup failed: %s", exc)
        return _parse_int_env("SUMMARY_RUN_INTERVAL_SECONDS", DEFAULT_RUN_INTERVAL_SECONDS)


def _cleanup_period_messages(db, start_utc: datetime, end_utc: datetime) -> int:
    result = db.execute(
        text(
            """
            DELETE FROM news_archive
            WHERE timestamp >= :start_utc
              AND timestamp < :end_utc
            """
        ),
        {"start_utc": start_utc, "end_utc": end_utc},
    )
    db.commit()
    return result.rowcount or 0


def _cleanup_interval_summaries(db, start_utc: datetime, end_utc: datetime) -> int:
    result = db.execute(
        text(
            """
            DELETE FROM summaries
            WHERE period_type = 'interval'
              AND period_start >= :start_utc
              AND period_end <= :end_utc
            """
        ),
        {"start_utc": start_utc, "end_utc": end_utc},
    )
    db.commit()
    return result.rowcount or 0


def _cleanup_interval_summaries_before(db, cutoff_utc: datetime) -> int:
    result = db.execute(
        text(
            """
            DELETE FROM summaries
            WHERE period_type = 'interval'
              AND period_end <= :cutoff_utc
            """
        ),
        {"cutoff_utc": cutoff_utc},
    )
    db.commit()
    return result.rowcount or 0


def _move_staging_to_archive(db, start_utc: datetime, end_utc: datetime) -> int:
    """
    Move messages from staging to archive after successful interval summary.
    Only moves news-related messages (is_news_related = true).
    """
    result = db.execute(
        text(
            """
            INSERT INTO news_archive (
                source_id, source_name, platform, source_message_id,
                author_name, content, clean_content, content_hash,
                timestamp, importance_score, category, created_at
            )
            SELECT 
                source_id, source_name, platform, source_message_id,
                author_name, content, clean_content, content_hash,
                timestamp, importance_score, category, created_at
            FROM news_feed_staging
            WHERE timestamp >= :start_utc
              AND timestamp < :end_utc
              AND is_news_related = true
            ON CONFLICT DO NOTHING
            """
        ),
        {"start_utc": start_utc, "end_utc": end_utc},
    )
    moved = result.rowcount or 0
    
    # Delete from staging after successful move
    db.execute(
        text(
            """
            DELETE FROM news_feed_staging
            WHERE timestamp >= :start_utc
              AND timestamp < :end_utc
            """
        ),
        {"start_utc": start_utc, "end_utc": end_utc},
    )
    db.commit()
    return moved


def _get_staging_messages(db, start_utc: datetime, end_utc: datetime, limit: int = 500):
    """Get messages from staging table for summarization."""
    return (
        db.query(models.NewsFeedStaging)
        .filter(
            models.NewsFeedStaging.timestamp >= start_utc,
            models.NewsFeedStaging.timestamp < end_utc,
        )
        .order_by(models.NewsFeedStaging.timestamp.asc())
        .limit(limit)
        .all()
    )


def _mark_staging_importance(db, start_utc: datetime, end_utc: datetime) -> int:
    """Mark messages in staging with importance scores and news-related flag."""
    messages = _get_staging_messages(db, start_utc, end_utc, limit=1000)
    updated = 0
    
    for msg in messages:
        content = msg.content or msg.clean_content or ""
        importance = _calculate_importance(content, msg.source_name or "")
        is_news = importance >= 4
        
        msg.importance_score = importance
        msg.is_news_related = is_news
        updated += 1
    
    db.commit()
    return updated


def _cleanup_chat_history(db, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = db.execute(
        text("DELETE FROM chat_history WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    db.commit()
    return result.rowcount or 0


def _cleanup_chat_sessions(db, retention_days: int) -> tuple[int, int]:
    if retention_days <= 0:
        return 0, 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    message_result = db.execute(
        text("DELETE FROM chat_messages WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    session_result = db.execute(
        text(
            """
            DELETE FROM chat_sessions
            WHERE NOT EXISTS (
                SELECT 1 FROM chat_messages m WHERE m.session_id = chat_sessions.id
            )
            """
        )
    )
    db.commit()
    return (message_result.rowcount or 0, session_result.rowcount or 0)


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _is_casual_chat(content: str) -> bool:
    """Check if message is casual chat (not news-related)."""
    if not content:
        return True
    content = content.strip()
    for pattern in _CASUAL_PATTERNS:
        if pattern.search(content):
            return True
    return False


def _is_news_related(content: str) -> bool:
    """Check if message contains news-related keywords."""
    if not content:
        return False
    return bool(_NEWS_PATTERN.search(content))


def _calculate_importance(content: str, source_name: str = "") -> int:
    """Calculate importance score (1-10) for a message."""
    if not content:
        return 0
    
    score = 5  # Base score
    
    # Bonus for news keywords
    if _is_news_related(content):
        score += 2
    
    # Penalty for casual chat
    if _is_casual_chat(content):
        score -= 3
    
    # Bonus for longer content (likely more substantive)
    if len(content) > 200:
        score += 1
    if len(content) > 500:
        score += 1
    
    # Bonus for certain source types (news agencies)
    news_source_keywords = ["أخبار", "نيوز", "news", "وكالة", "agency", "رسمي"]
    if any(kw in source_name.lower() for kw in news_source_keywords):
        score += 1
    
    return max(1, min(10, score))


def _filter_news_messages(
    messages: list, min_importance: int = 4
) -> tuple[list, list]:
    """
    Filter messages into news-related and casual chat.
    Returns (news_messages, filtered_out_messages).
    """
    news = []
    filtered = []
    
    for msg in messages:
        content = getattr(msg, 'content', '') or getattr(msg, 'clean_content', '') or ''
        source_name = getattr(msg, 'source_name', '') or ''
        
        importance = _calculate_importance(content, source_name)
        
        if importance >= min_importance:
            news.append(msg)
        else:
            filtered.append(msg)
    
    return news, filtered


def _daily_anchor(dt_local: datetime) -> datetime:
    anchor = dt_local.replace(
        hour=SUMMARY_ANCHOR_HOUR,
        minute=SUMMARY_ANCHOR_MINUTE,
        second=0,
        microsecond=0,
    )
    if dt_local < anchor:
        anchor = anchor - timedelta(days=1)
    return anchor


def _weekly_anchor(dt_local: datetime) -> datetime:
    anchor = dt_local.replace(
        hour=SUMMARY_ANCHOR_HOUR,
        minute=SUMMARY_ANCHOR_MINUTE,
        second=0,
        microsecond=0,
    )
    days_since = (anchor.weekday() - WEEKLY_ANCHOR_WEEKDAY) % 7
    anchor = anchor - timedelta(days=days_since)
    if dt_local < anchor:
        anchor = anchor - timedelta(days=7)
    return anchor


def _monthly_anchor(dt_local: datetime, tz: timezone) -> datetime:
    anchor = dt_local.replace(
        day=1,
        hour=SUMMARY_ANCHOR_HOUR,
        minute=SUMMARY_ANCHOR_MINUTE,
        second=0,
        microsecond=0,
    )
    if dt_local < anchor:
        if dt_local.month == 1:
            year = dt_local.year - 1
            month = 12
        else:
            year = dt_local.year
            month = dt_local.month - 1
        anchor = datetime(
            year,
            month,
            1,
            hour=SUMMARY_ANCHOR_HOUR,
            minute=SUMMARY_ANCHOR_MINUTE,
            tzinfo=tz,
        )
    return anchor


def _next_monthly_anchor(dt_local: datetime, tz: timezone) -> datetime:
    year = dt_local.year + (dt_local.month // 12)
    month = (dt_local.month % 12) + 1
    return datetime(
        year,
        month,
        1,
        hour=SUMMARY_ANCHOR_HOUR,
        minute=SUMMARY_ANCHOR_MINUTE,
        tzinfo=tz,
    )


def _interval_end_local(now_local: datetime, anchor_local: datetime) -> datetime:
    delta = now_local - anchor_local
    if delta.total_seconds() <= 0:
        return anchor_local
    intervals = int(delta.total_seconds() // (INTERVAL_MINUTES * 60))
    return anchor_local + timedelta(minutes=intervals * INTERVAL_MINUTES)


# Summary retention policy (in days)
SUMMARY_RETENTION = {
    "interval": 1,   # Half-hourly: keep for 1 day only (used for daily rollup)
    "daily": 14,     # Daily: keep for 2 weeks
    "weekly": 90,    # Weekly: keep for 3 months
    "monthly": None, # Monthly: keep forever
}


def _cleanup_old_summaries(db) -> dict[str, int]:
    """
    Delete old summaries based on retention policy.
    Returns dict with count of deleted summaries per type.
    """
    now_utc = datetime.now(timezone.utc)
    deleted = {"interval": 0, "daily": 0, "weekly": 0}
    
    for period_type, retention_days in SUMMARY_RETENTION.items():
        if retention_days is None:
            continue  # Keep forever
        
        cutoff = now_utc - timedelta(days=retention_days)
        
        count = (
            db.query(models.Summary)
            .filter(
                models.Summary.period_type == period_type,
                models.Summary.period_end < cutoff,
            )
            .delete(synchronize_session=False)
        )
        
        if count > 0:
            db.commit()
            deleted[period_type] = count
    
    return deleted


def _archive_summaries_before(db, period_type: str, cutoff_utc: datetime) -> int:
    db.execute(
        text(
            """
            INSERT INTO summary_archive (
                period_type,
                period_start,
                period_end,
                content,
                created_at,
                archived_at
            )
            SELECT
                period_type,
                period_start,
                period_end,
                content,
                created_at,
                NOW()
            FROM summaries
            WHERE period_type = :period_type
              AND period_end <= :cutoff_utc
            ON CONFLICT DO NOTHING
            """
        ),
        {"period_type": period_type, "cutoff_utc": cutoff_utc},
    )
    result = db.execute(
        text(
            """
            DELETE FROM summaries
            WHERE period_type = :period_type
              AND period_end <= :cutoff_utc
            """
        ),
        {"period_type": period_type, "cutoff_utc": cutoff_utc},
    )
    db.commit()
    return result.rowcount or 0


def _build_daily_prompt(
    start_local: datetime,
    end_local: datetime,
    lines: list[str],
    message_count: int,
    omitted: int,
) -> str:
    """
    Build prompt for interval (30-min) summaries from raw messages.
    This is the only level that actually summarizes raw content.
    """
    prompt = [
        "أنت محرر أخبار. مهمتك هي استخراج وتلخيص الأخبار المهمة من الرسائل التالية.",
        "",
        "القواعد:",
        f"- لديك {message_count} رسالة للفترة المحددة",
        "- استخرج الأخبار والمعلومات المهمة فقط",
        "- تجاهل المحادثات الجانبية والتحيات والردود العادية",
        "- اكتب كل خبر في نقطة منفصلة (•)",
        "- احتفظ بالتفاصيل المهمة (أسماء، أرقام، تواريخ)",
        "- لا تخترع معلومات، استخدم المحتوى المقدم فقط",
        "- اكتب بالعربية الفصحى",
        "- إذا لم يكن هناك أخبار مهمة، اكتب 'لا توجد أخبار مهمة في هذه الفترة'",
        "",
        f"الفترة: {start_local:%Y-%m-%d %H:%M} إلى {end_local:%Y-%m-%d %H:%M}",
        f"الرسائل: {message_count} إجمالي، {omitted} تم حذفها بسبب الحجم.",
        "",
        "الرسائل:",
        *lines,
    ]
    return "\n".join(prompt).strip()


def _build_rollup_prompt(
    period_label: str,
    start_local: datetime,
    end_local: datetime,
    lines: list[str],
    source_count: int = 0,
) -> str:
    """
    Build a prompt for consolidating multiple reports into one.
    Focus on AGGREGATION and DEDUPLICATION, not summarization.
    """
    if period_label == "daily":
        instructions = [
            "أنت محرر أخبار. مهمتك هي تجميع التقارير الساعية في تقرير يومي واحد.",
            "",
            "القواعد المهمة:",
            f"- لديك {source_count} تقرير ساعي تحتاج لجمعهم",
            "- احتفظ بجميع الأخبار المهمة، لا تحذف شيئاً مهماً",
            "- أزل التكرارات الحرفية فقط (نفس الخبر بنفس الكلمات)",
            "- إذا تكرر خبر بصياغات مختلفة، احتفظ بالصياغة الأفضل",
            "- رتب الأخبار حسب الأهمية (الأهم أولاً)",
            "- استخدم نقاط (•) لكل خبر",
            "- لا تلخص بشكل جائر، احتفظ بالتفاصيل المهمة",
            "- اكتب بالعربية الفصحى",
        ]
    elif period_label == "weekly":
        instructions = [
            "أنت محرر أخبار. مهمتك هي تجميع التقارير اليومية في تقرير أسبوعي واحد.",
            "",
            "القواعد المهمة:",
            f"- لديك {source_count} تقرير يومي تحتاج لجمعهم",
            "- احتفظ بجميع الأخبار والأحداث المهمة",
            "- أزل التكرارات الحرفية فقط",
            "- رتب الأخبار حسب الموضوع أو حسب الأهمية",
            "- يمكنك تجميع الأخبار المتعلقة بنفس الموضوع معاً",
            "- لا تحذف أخباراً مهمة، فقط نظم وأزل المكرر",
            "- اكتب بالعربية الفصحى",
        ]
    else:  # monthly
        instructions = [
            "أنت محرر أخبار. مهمتك هي تجميع التقارير الأسبوعية في تقرير شهري واحد.",
            "",
            "القواعد المهمة:",
            f"- لديك {source_count} تقرير أسبوعي تحتاج لجمعهم",
            "- احتفظ بجميع الأحداث والتطورات المهمة",
            "- أزل التكرارات فقط",
            "- رتب حسب الموضوع أو التسلسل الزمني",
            "- يمكنك إضافة عناوين فرعية للمواضيع المختلفة",
            "- لا تلخص بشكل يفقد التفاصيل المهمة",
            "- اكتب بالعربية الفصحى",
        ]
    
    prompt = [
        *instructions,
        "",
        f"الفترة: {start_local:%Y-%m-%d %H:%M} إلى {end_local:%Y-%m-%d %H:%M}",
        "",
        "التقارير:",
        *lines,
    ]
    return "\n".join(prompt).strip()


def _collect_summary_lines(summaries: list[models.Summary]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for summary in summaries:
        content = (summary.content or "").strip()
        if not content or content == NO_MESSAGES_SUMMARY:
            continue
        for line in content.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            lines.append(cleaned)
    return lines


def _collect_grouped_summary_lines(
    summaries: list[models.Summary],
    tz: timezone,
    labeler,
) -> list[str]:
    lines: list[str] = []
    for summary in summaries:
        content = (summary.content or "").strip()
        if not content or content == NO_MESSAGES_SUMMARY:
            continue
        group_lines: list[str] = []
        seen: set[str] = set()
        for line in content.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            group_lines.append(cleaned)
        if not group_lines:
            continue
        lines.append(labeler(summary, tz))
        lines.extend(group_lines)
    return lines


def _upsert_summary(
    db,
    period_type: str,
    start_utc: datetime,
    end_utc: datetime,
    content: str,
) -> tuple[models.Summary | None, bool]:
    existing = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == period_type,
            models.Summary.period_start == start_utc,
            models.Summary.period_end == end_utc,
        )
        .first()
    )
    if existing:
        if getattr(existing, "is_locked", False):
            return existing, False
        if existing.content != content:
            existing.content = content
            db.commit()
            return existing, True
        return existing, False

    summary = models.Summary(
        period_type=period_type,
        period_start=start_utc,
        period_end=end_utc,
        content=content,
    )
    db.add(summary)
    db.commit()
    return summary, True


def _aggregate_period_summaries(
    db,
    period_type: str,
    source_type: str,
    start_utc: datetime,
    end_utc: datetime,
) -> tuple[models.Summary | None, bool]:
    summaries = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == source_type,
            models.Summary.period_start >= start_utc,
            models.Summary.period_start < end_utc,
        )
        .order_by(models.Summary.period_start.asc())
        .all()
    )
    if not summaries:
        return None, False
    lines = _collect_summary_lines(summaries)
    content = "\n".join(lines).strip() if lines else NO_MESSAGES_SUMMARY
    return _upsert_summary(db, period_type, start_utc, end_utc, content)


def _aggregate_period_summaries_grouped(
    db,
    period_type: str,
    source_type: str,
    start_utc: datetime,
    end_utc: datetime,
    tz: timezone,
    labeler,
) -> tuple[models.Summary | None, bool]:
    summaries = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == source_type,
            models.Summary.period_start >= start_utc,
            models.Summary.period_start < end_utc,
        )
        .order_by(models.Summary.period_start.asc())
        .all()
    )
    if not summaries:
        return None, False
    lines = _collect_grouped_summary_lines(summaries, tz, labeler)
    content = "\n".join(lines).strip() if lines else NO_MESSAGES_SUMMARY
    return _upsert_summary(db, period_type, start_utc, end_utc, content)



def _call_gemini(
    api_key: str, model: str, prompt: str, api_version: str | None = None
) -> str | None:
    api_version = _get_api_version(api_version)
    model = _normalize_model(model)
    url = (
        f"https://generativelanguage.googleapis.com/{api_version}/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "topP": 0.8, "maxOutputTokens": 1024},
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        candidates = parsed.get("candidates") or []
        if not candidates:
            logger.error("Gemini response missing candidates.")
            return None
        parts = candidates[0].get("content", {}).get("parts") or []
        if not parts:
            logger.error("Gemini response missing content parts.")
            return None
        text = parts[0].get("text")
        if not text:
            logger.error("Gemini response missing text.")
            return None
        return text.strip()
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Gemini error %s: %s", exc.code, body)
        return None
    except URLError as exc:
        logger.error("Gemini network error: %s", exc.reason)
        return None
    except Exception as exc:
        logger.exception("Gemini request failed: %s", exc)
        return None


def _call_openrouter_single(
    api_key: str, model: str, prompt: str, base_url: str
) -> tuple[str | None, str | None]:
    """Call OpenRouter with a specific model. Returns (result, error_code)."""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if title:
        headers["X-Title"] = title
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=OPENROUTER_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        choices = parsed.get("choices") or []
        if not choices:
            return None, "no_choices"
        message = choices[0].get("message") or {}
        text = message.get("content")
        if not text:
            return None, "no_content"
        return str(text).strip(), None
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        return None, f"http_{exc.code}"
    except URLError as exc:
        return None, f"network_{exc.reason}"
    except TimeoutError:
        return None, "timeout"
    except Exception as exc:
        return None, f"error_{exc}"


def _call_openrouter(
    api_key: str, model: str, prompt: str, base_url: str
) -> str | None:
    """
    Call OpenRouter with smart fallback.
    Tries the configured model first, then falls back through free → cheap paid models.
    """
    # Build model chain: configured model first, then fallback list
    models_to_try = [model] + [m for m in OPENROUTER_FALLBACK_MODELS if m != model]
    
    for try_model in models_to_try:
        result, error = _call_openrouter_single(api_key, try_model, prompt, base_url)
        if result:
            if try_model != model:
                logger.info("Summary: Used fallback model %s", try_model)
            return result
        # Check if error is retriable (rate limit, not found, timeout)
        if error and ("429" in error or "404" in error or "timeout" in error):
            logger.warning("Summary model %s failed (%s), trying next...", try_model, error)
            continue
        # For other errors (network, etc.), also try next model
        logger.warning("Summary model %s failed (%s), trying next...", try_model, error)
    
    logger.error("All OpenRouter models failed for summary")
    return None


def _call_summary_llm(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    api_version: str | None = None,
    openrouter_base_url: str | None = None,
) -> str | None:
    if provider == "openrouter":
        base_url = openrouter_base_url or _get_openrouter_base_url()
        return _call_openrouter(api_key, model, prompt, base_url)
    return _call_gemini(api_key, model, prompt, api_version)


def _is_summary_valid(text: str) -> bool:
    if not text:
        return False
    for line in text.splitlines():
        if _BULLET_RE.match(line):
            return True
    return False


def _build_message_lines(
    messages: list[models.NewsArchive],
    max_chars: int,
    tz: timezone,
) -> tuple[list[str], int]:
    lines: list[str] = []
    used = 0
    total_chars = 0
    for msg in messages:
        timestamp = _ensure_aware(msg.timestamp)
        local_time = timestamp.astimezone(tz) if timestamp else None
        time_label = local_time.strftime("%H:%M") if local_time else "--:--"
        author = f" ({msg.author_name})" if msg.author_name else ""
        line = f"[{time_label}] {msg.source_name}{author}: {msg.content}"
        if total_chars + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += 1
        total_chars += len(line) + 1
    return lines, used


def _summarize_period(
    db,
    provider: str,
    api_key: str,
    model: str,
    api_version: str | None,
    openrouter_base_url: str | None,
    period_type: str,
    start_utc: datetime,
    end_utc: datetime,
    tz: timezone,
    max_messages: int,
    max_chars: int,
) -> tuple[models.Summary | None, bool]:
    existing = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == period_type,
            models.Summary.period_start == start_utc,
        )
        .first()
    )
    if existing:
        return existing, False

    message_count = (
        db.query(func.count(models.NewsArchive.id))
        .filter(
            models.NewsArchive.timestamp >= start_utc,
            models.NewsArchive.timestamp < end_utc,
        )
        .scalar()
        or 0
    )

    if message_count == 0:
        summary_text = NO_MESSAGES_SUMMARY
        summary = models.Summary(
            period_type=period_type,
            period_start=start_utc,
            period_end=end_utc,
            content=summary_text,
        )
        db.add(summary)
        db.commit()
        return summary, True

    messages = (
        db.query(models.NewsArchive)
        .filter(
            models.NewsArchive.timestamp >= start_utc,
            models.NewsArchive.timestamp < end_utc,
        )
        .order_by(models.NewsArchive.timestamp.asc())
        .limit(max_messages)
        .all()
    )

    lines, used = _build_message_lines(messages, max_chars, tz)
    omitted = max(0, message_count - used)
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    prompt = _build_daily_prompt(start_local, end_local, lines, message_count, omitted)
    summary_text = _call_summary_llm(
        provider,
        api_key,
        model,
        prompt,
        api_version=api_version,
        openrouter_base_url=openrouter_base_url,
    )
    if not summary_text:
        return None, False
    if not _is_summary_valid(summary_text):
        logger.warning(
            "Summary invalid for %s to %s; keeping messages for retry.",
            start_utc.isoformat(),
            end_utc.isoformat(),
        )
        return None, False

    summary = models.Summary(
        period_type=period_type,
        period_start=start_utc,
        period_end=end_utc,
        content=summary_text,
    )
    db.add(summary)
    db.commit()
    return summary, True


def _summarize_period_from_staging(
    db,
    provider: str,
    api_key: str,
    model: str,
    api_version: str | None,
    openrouter_base_url: str | None,
    period_type: str,
    start_utc: datetime,
    end_utc: datetime,
    tz: timezone,
    staging_messages: list,
    max_chars: int,
) -> tuple[models.Summary | None, bool]:
    """
    Create summary from staging messages (already filtered for news relevance).
    """
    existing = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == period_type,
            models.Summary.period_start == start_utc,
        )
        .first()
    )
    if existing:
        return existing, False

    message_count = len(staging_messages)
    
    if message_count == 0:
        summary_text = NO_MESSAGES_SUMMARY
        summary = models.Summary(
            period_type=period_type,
            period_start=start_utc,
            period_end=end_utc,
            content=summary_text,
        )
        db.add(summary)
        db.commit()
        return summary, True

    # Build message lines from staging messages
    lines: list[str] = []
    total_chars = 0
    used = 0
    
    for msg in staging_messages:
        timestamp = _ensure_aware(msg.timestamp)
        local_time = timestamp.astimezone(tz) if timestamp else None
        time_label = local_time.strftime("%H:%M") if local_time else "--:--"
        author = f" ({msg.author_name})" if msg.author_name else ""
        content = msg.content or msg.clean_content or ""
        line = f"[{time_label}] {msg.source_name}{author}: {content}"
        if total_chars + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += 1
        total_chars += len(line) + 1

    omitted = max(0, message_count - used)
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    prompt = _build_daily_prompt(start_local, end_local, lines, message_count, omitted)
    
    summary_text = _call_summary_llm(
        provider,
        api_key,
        model,
        prompt,
        api_version=api_version,
        openrouter_base_url=openrouter_base_url,
    )
    
    if not summary_text:
        return None, False
    if not _is_summary_valid(summary_text):
        logger.warning(
            "Summary invalid for %s to %s; keeping messages for retry.",
            start_utc.isoformat(),
            end_utc.isoformat(),
        )
        return None, False

    summary = models.Summary(
        period_type=period_type,
        period_start=start_utc,
        period_end=end_utc,
        content=summary_text,
    )
    db.add(summary)
    db.commit()
    return summary, True


def _summarize_rollup(
    db,
    provider: str,
    api_key: str,
    model: str,
    api_version: str | None,
    openrouter_base_url: str | None,
    period_type: str,
    source_type: str,
    start_utc: datetime,
    end_utc: datetime,
    tz: timezone,
    max_chars: int,
) -> tuple[models.Summary | None, bool]:
    existing = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == period_type,
            models.Summary.period_start == start_utc,
        )
        .first()
    )
    if existing:
        return existing, False

    summaries = (
        db.query(models.Summary)
        .filter(
            models.Summary.period_type == source_type,
            models.Summary.period_start >= start_utc,
            models.Summary.period_start < end_utc,
        )
        .order_by(models.Summary.period_start.asc())
        .all()
    )
    if not summaries:
        return None, False

    lines: list[str] = []
    total_chars = 0
    for summary in summaries:
        local_date = summary.period_start.astimezone(tz).strftime("%Y-%m-%d")
        line = f"{local_date}: {summary.content}"
        if total_chars + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total_chars += len(line) + 1

    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    
    # Determine the correct label based on period type
    if period_type == "daily":
        label = "daily"
    elif period_type == "weekly":
        label = "weekly"
    else:
        label = "monthly"
    
    prompt = _build_rollup_prompt(label, start_local, end_local, lines, source_count=len(summaries))
    summary_text = _call_summary_llm(
        provider,
        api_key,
        model,
        prompt,
        api_version=api_version,
        openrouter_base_url=openrouter_base_url,
    )
    if not summary_text:
        return None, False
    if not _is_summary_valid(summary_text):
        logger.warning(
            "Rollup summary invalid for %s to %s; skipping save.",
            start_utc.isoformat(),
            end_utc.isoformat(),
        )
        return None, False

    summary = models.Summary(
        period_type=period_type,
        period_start=start_utc,
        period_end=end_utc,
        content=summary_text,
    )
    db.add(summary)
    db.commit()
    return summary, True


def _summarize_interval(
    db,
    provider: str,
    api_key: str,
    model: str,
    api_version: str | None,
    openrouter_base_url: str | None,
    tz: timezone,
    max_messages: int,
    max_chars: int,
) -> list[models.Summary]:
    """
    Create interval summaries from staging table with smart filtering.
    Only processes news-related messages and moves them to archive on success.
    """
    now_local = datetime.now(tz)
    anchor_local = _daily_anchor(now_local)
    interval_end_local = _interval_end_local(now_local, anchor_local)

    last_summary = (
        db.query(models.Summary)
        .filter(models.Summary.period_type == "interval")
        .order_by(models.Summary.period_start.desc())
        .first()
    )
    if last_summary:
        candidate = last_summary.period_end.astimezone(tz)
        next_start_local = candidate if candidate > anchor_local else anchor_local
    else:
        next_start_local = anchor_local

    created: list[models.Summary] = []
    while next_start_local + timedelta(minutes=INTERVAL_MINUTES) <= interval_end_local:
        end_local = next_start_local + timedelta(minutes=INTERVAL_MINUTES)
        start_utc = next_start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        
        # Mark importance scores in staging before processing
        _mark_staging_importance(db, start_utc, end_utc)
        
        # Get only news-related messages from staging
        staging_messages = (
            db.query(models.NewsFeedStaging)
            .filter(
                models.NewsFeedStaging.timestamp >= start_utc,
                models.NewsFeedStaging.timestamp < end_utc,
                models.NewsFeedStaging.is_news_related == True,
            )
            .order_by(models.NewsFeedStaging.timestamp.asc())
            .limit(max_messages)
            .all()
        )
        
        # Count total for logging
        total_staging = (
            db.query(func.count(models.NewsFeedStaging.id))
            .filter(
                models.NewsFeedStaging.timestamp >= start_utc,
                models.NewsFeedStaging.timestamp < end_utc,
            )
            .scalar() or 0
        )
        filtered_count = total_staging - len(staging_messages)
        
        if staging_messages:
            logger.info(
                "Processing %d news messages (filtered %d casual) for interval %s",
                len(staging_messages),
                filtered_count,
                next_start_local.isoformat(),
            )
        
        # Use staging messages for summarization
        summary, is_new = _summarize_period_from_staging(
            db,
            provider,
            api_key,
            model,
            api_version,
            openrouter_base_url,
            "interval",
            start_utc,
            end_utc,
            tz,
            staging_messages,
            max_chars,
        )
        
        if summary is None:
            logger.warning(
                "Interval summary failed for %s; will retry next cycle.",
                next_start_local.isoformat(),
            )
            break
        
        # Move messages from staging to archive after successful summary
        moved = _move_staging_to_archive(db, start_utc, end_utc)
        if moved:
            logger.info("Moved %d news messages to archive.", moved)
        
        if is_new:
            created.append(summary)
        next_start_local = end_local

    return created


def _summarize_daily(db, tz: timezone) -> list[models.Summary]:
    """
    Aggregate daily summaries from interval summaries (no LLM).
    This keeps daily reports continuously filled during the day.
    """
    now_local = datetime.now(tz)
    current_day_start = _daily_anchor(now_local)

    earliest_interval = (
        db.query(func.min(models.Summary.period_start))
        .filter(models.Summary.period_type == "interval")
        .scalar()
    )
    earliest_interval = _ensure_aware(earliest_interval)
    if not earliest_interval:
        return []

    next_start_local = _daily_anchor(earliest_interval.astimezone(tz))
    last_summary = (
        db.query(models.Summary)
        .filter(models.Summary.period_type == "daily")
        .order_by(models.Summary.period_start.desc())
        .first()
    )
    if last_summary:
        last_start_local = last_summary.period_start.astimezone(tz)
        if last_start_local > next_start_local:
            next_start_local = last_start_local

    changed: list[models.Summary] = []
    while next_start_local <= current_day_start:
        end_local = next_start_local + timedelta(days=1)
        start_utc = next_start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        summary, did_change = _aggregate_period_summaries(
            db,
            "daily",
            "interval",
            start_utc,
            end_utc,
        )
        if summary is not None and did_change:
            changed.append(summary)
        next_start_local = end_local

    return changed


def _summarize_weekly(db, tz: timezone) -> list[models.Summary]:
    """
    Aggregate weekly summaries from daily summaries (no LLM).
    Weekly reports are continuously filled as daily reports update.
    """
    now_local = datetime.now(tz)
    current_week_start = _weekly_anchor(now_local)

    earliest_daily = (
        db.query(func.min(models.Summary.period_start))
        .filter(models.Summary.period_type == "daily")
        .scalar()
    )
    earliest_daily = _ensure_aware(earliest_daily)
    if not earliest_daily:
        return []

    next_start_local = _weekly_anchor(earliest_daily.astimezone(tz))
    last_summary = (
        db.query(models.Summary)
        .filter(models.Summary.period_type == "weekly")
        .order_by(models.Summary.period_start.desc())
        .first()
    )
    if last_summary:
        last_start_local = last_summary.period_start.astimezone(tz)
        if last_start_local > next_start_local:
            next_start_local = last_start_local

    changed: list[models.Summary] = []
    while next_start_local <= current_week_start:
        week_end_local = next_start_local + timedelta(days=7)
        start_utc = next_start_local.astimezone(timezone.utc)
        end_utc = week_end_local.astimezone(timezone.utc)
        summary, did_change = _aggregate_period_summaries_grouped(
            db,
            "weekly",
            "daily",
            start_utc,
            end_utc,
            tz,
            lambda s, tzinfo: s.period_start.astimezone(tzinfo).strftime("%Y-%m-%d"),
        )
        if summary is not None and did_change:
            changed.append(summary)
        next_start_local = week_end_local

    return changed


def _summarize_monthly(db, tz: timezone) -> list[models.Summary]:
    """
    Aggregate monthly summaries from weekly summaries (no LLM).
    Monthly reports are continuously filled as weekly reports update.
    """
    now_local = datetime.now(tz)
    current_month_start = _monthly_anchor(now_local, tz)

    earliest_weekly = (
        db.query(func.min(models.Summary.period_start))
        .filter(models.Summary.period_type == "weekly")
        .scalar()
    )
    earliest_weekly = _ensure_aware(earliest_weekly)
    if not earliest_weekly:
        return []

    next_start_local = _monthly_anchor(earliest_weekly.astimezone(tz), tz)
    last_summary = (
        db.query(models.Summary)
        .filter(models.Summary.period_type == "monthly")
        .order_by(models.Summary.period_start.desc())
        .first()
    )
    if last_summary:
        last_start_local = last_summary.period_start.astimezone(tz)
        if last_start_local > next_start_local:
            next_start_local = last_start_local

    changed: list[models.Summary] = []
    while next_start_local <= current_month_start:
        month_end_local = _next_monthly_anchor(next_start_local, tz)
        start_utc = next_start_local.astimezone(timezone.utc)
        end_utc = month_end_local.astimezone(timezone.utc)
        summary, did_change = _aggregate_period_summaries_grouped(
            db,
            "monthly",
            "weekly",
            start_utc,
            end_utc,
            tz,
            lambda s, tzinfo: (
                f"{s.period_start.astimezone(tzinfo):%Y-%m-%d} -> "
                f"{s.period_end.astimezone(tzinfo):%Y-%m-%d}"
            ),
        )
        if summary is not None and did_change:
            changed.append(summary)
        next_start_local = month_end_local

    return changed


def _format_summary_message(
    period_type: str, summary: models.Summary, tz: timezone
) -> str:
    labels = {
        "daily": "Daily summary",
        "weekly": "Weekly summary",
        "monthly": "Monthly summary",
    }
    label = labels.get(period_type, "Summary")
    start_local = summary.period_start.astimezone(tz)
    end_local = summary.period_end.astimezone(tz)
    header = f"{label} ({start_local:%Y-%m-%d %H:%M} -> {end_local:%Y-%m-%d %H:%M})"
    return f"{header}\n\n{summary.content}".strip()


def _send_summary_notifications(
    db, period_type: str, summaries: list[models.Summary], tz: timezone
) -> int:
    if not summaries:
        return 0
    from app import telegram_bot

    config = telegram_bot.get_bot_config(db)
    if not config.get("enabled") or not config.get("token"):
        return 0
    preference_map = {
        "daily": models.User.telegram_daily_enabled,
        "weekly": models.User.telegram_weekly_enabled,
        "monthly": models.User.telegram_monthly_enabled,
    }
    preference = preference_map.get(period_type)
    if preference is None:
        return 0
    users = (
        db.query(models.User)
        .filter(models.User.telegram_chat_id.isnot(None), preference.is_(True))
        .all()
    )
    if not users:
        return 0

    sent = 0
    for summary in summaries:
        if summary.content.strip() == NO_MESSAGES_SUMMARY:
            continue
        message = _format_summary_message(period_type, summary, tz)
        for user in users:
            chat_id = user.telegram_chat_id
            if chat_id is None:
                continue
            result = telegram_bot.send_message(config["token"], chat_id, message)
            if result.get("retry_after"):
                time.sleep(result["retry_after"])
                result = telegram_bot.send_message(config["token"], chat_id, message)
            if result.get("ok"):
                sent += 1
            time.sleep(0.08)
    return sent


def run_summary_cycle() -> None:
    with SessionLocal() as db:
        provider = _get_summary_provider(db)
        api_key = ""
        interval_summaries: list[models.Summary] = []
        daily_summaries: list[models.Summary] = []
        weekly_summaries: list[models.Summary] = []
        monthly_summaries: list[models.Summary] = []
        interval_count = 0
        daily_count = 0
        weekly_count = 0
        monthly_count = 0
        daily_archived = 0
        weekly_archived = 0
        notify_daily = 0
        notify_weekly = 0
        notify_monthly = 0
        tz_name = _get_string_setting(db, "summary_timezone", "SUMMARY_TIMEZONE", "UTC")
        tz = _get_timezone(tz_name)
        if provider == "openrouter":
            api_key = _get_string_setting(
                db, "openrouter_api_key", "OPENROUTER_API_KEY", ""
            ).strip()
            if not api_key:
                logger.warning("OPENROUTER_API_KEY missing; summaries are disabled.")
        else:
            api_key = _get_string_setting(
                db, "gemini_api_key", "GEMINI_API_KEY", ""
            ).strip()
            if not api_key:
                logger.warning("GEMINI_API_KEY missing; summaries are disabled.")

        if api_key:
            model = _get_summary_model(db, provider)
            api_version = (
                _get_string_setting(db, "gemini_api_version", "GEMINI_API_VERSION", "v1")
                if provider == "gemini"
                else None
            )
            openrouter_base_url = (
                _get_openrouter_base_url() if provider == "openrouter" else None
            )
            max_messages = _get_int_setting(
                db,
                "summary_max_messages",
                "SUMMARY_MAX_MESSAGES",
                DEFAULT_MAX_MESSAGES,
                1,
                5000,
            )
            max_chars = _get_int_setting(
                db,
                "summary_max_chars",
                "SUMMARY_MAX_CHARS",
                DEFAULT_MAX_INPUT_CHARS,
                1000,
                500000,
            )

            interval_summaries = _summarize_interval(
                db,
                provider,
                api_key,
                model,
                api_version,
                openrouter_base_url,
                tz,
                max_messages,
                max_chars,
            )
            interval_count = len(interval_summaries)

        daily_summaries = _summarize_daily(db, tz)
        weekly_summaries = _summarize_weekly(db, tz)
        monthly_summaries = _summarize_monthly(db, tz)
        daily_count = len(daily_summaries)
        weekly_count = len(weekly_summaries)
        monthly_count = len(monthly_summaries)

        now_local = datetime.now(tz)
        current_day_start = _daily_anchor(now_local)
        current_month_start = _monthly_anchor(now_local, tz)
        _cleanup_interval_summaries_before(db, current_day_start.astimezone(timezone.utc))
        daily_archive_cutoff = (current_day_start - timedelta(days=7)).astimezone(timezone.utc)
        weekly_archive_cutoff = current_month_start.astimezone(timezone.utc)
        daily_archived = _archive_summaries_before(db, "daily", daily_archive_cutoff)
        weekly_archived = _archive_summaries_before(db, "weekly", weekly_archive_cutoff)

        now_utc = datetime.now(timezone.utc)
        completed_daily = [s for s in daily_summaries if s.period_end <= now_utc]
        completed_weekly = [s for s in weekly_summaries if s.period_end <= now_utc]
        completed_monthly = [s for s in monthly_summaries if s.period_end <= now_utc]
        notify_daily = _send_summary_notifications(db, "daily", completed_daily, tz)
        notify_weekly = _send_summary_notifications(db, "weekly", completed_weekly, tz)
        notify_monthly = _send_summary_notifications(db, "monthly", completed_monthly, tz)
        chat_retention_days = _get_chat_retention_days(db)
        chat_history_deleted = _cleanup_chat_history(db, chat_retention_days)
        chat_messages_deleted, chat_sessions_deleted = _cleanup_chat_sessions(
            db, chat_retention_days
        )

        summary_cleanup = _cleanup_old_summaries(db)

    if interval_count or daily_count or weekly_count or monthly_count:
        logger.info(
            "Summaries generated: interval=%d daily=%d weekly=%d monthly=%d.",
            interval_count,
            daily_count,
            weekly_count,
            monthly_count,
        )
    if notify_daily or notify_weekly or notify_monthly:
        logger.info(
            "Summary notifications sent: daily=%d weekly=%d monthly=%d.",
            notify_daily,
            notify_weekly,
            notify_monthly,
        )
    if chat_history_deleted or chat_messages_deleted or chat_sessions_deleted:
        logger.info(
            "Deleted %d legacy chat rows, %d chat messages, %d chat sessions older than %d days.",
            chat_history_deleted,
            chat_messages_deleted,
            chat_sessions_deleted,
            chat_retention_days,
        )
    
    if sum(summary_cleanup.values()) > 0:
        logger.info(
            "Cleaned up old summaries: interval=%d daily=%d weekly=%d",
            summary_cleanup.get("interval", 0),
            summary_cleanup.get("daily", 0),
            summary_cleanup.get("weekly", 0),
        )
    if daily_archived or weekly_archived:
        logger.info(
            "Archived summaries: daily=%d weekly=%d.",
            daily_archived,
            weekly_archived,
        )


def _summary_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            run_summary_cycle()
        except Exception as exc:
            logger.exception("Summary cycle failed: %s", exc)
        interval = _get_summary_interval_seconds()
        stop_event.wait(interval)


def start_summary_worker(app) -> None:
    stop_event = threading.Event()
    thread = threading.Thread(target=_summary_loop, args=(stop_event,), daemon=True)
    thread.start()
    app.state.summary_stop_event = stop_event
    app.state.summary_thread = thread


def stop_summary_worker(app) -> None:
    stop_event = getattr(app.state, "summary_stop_event", None)
    if stop_event:
        stop_event.set()
    thread = getattr(app.state, "summary_thread", None)
    if thread:
        thread.join(timeout=5)
