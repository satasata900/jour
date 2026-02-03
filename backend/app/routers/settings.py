import json
import logging
import os
from enum import Enum
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.authz import require_admin, require_admin_or_ingest, require_user_or_admin_key

logger = logging.getLogger("settings")

router = APIRouter(prefix="/settings", tags=["settings"])

RETENTION_KEY = "news_retention_days"
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 365
DEFAULT_RETENTION_DAYS = 1
CHAT_RETENTION_KEY = "chat_retention_days"
MIN_CHAT_RETENTION_DAYS = 1
MAX_CHAT_RETENTION_DAYS = 30
DEFAULT_CHAT_RETENTION_DAYS = 7
DEFAULT_SUMMARY_RUN_INTERVAL_SECONDS = 300
DEFAULT_SUMMARY_MAX_MESSAGES = 200
DEFAULT_SUMMARY_MAX_CHARS = 120000
GEMINI_LITE_MODEL = "gemini-flash-lite-latest"
DEFAULT_GEMINI_SUMMARY_MODEL = GEMINI_LITE_MODEL
DEFAULT_OPENROUTER_SUMMARY_MODEL = "openrouter/auto"
DEFAULT_SUMMARY_MODEL = DEFAULT_GEMINI_SUMMARY_MODEL
DEFAULT_GEMINI_AGENT_MODEL = GEMINI_LITE_MODEL
DEFAULT_OPENROUTER_AGENT_MODEL = "openrouter/auto"
DEFAULT_AGENT_MODEL = DEFAULT_GEMINI_AGENT_MODEL
DEFAULT_AGENT_PROVIDER = "openrouter"
DEFAULT_TIMEZONE = "Asia/Damascus"
DEFAULT_GEMINI_API_VERSION = "v1"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_TIMEOUT_SECONDS = 15
DEFAULT_SEARCH_PROVIDER = "searxng"
DEFAULT_SEARXNG_BASE_URL = "http://searxng:8080"
DEFAULT_SEARXNG_TIMEOUT_SECONDS = 15
DEFAULT_SEARXNG_MAX_RESULTS = 5
DEFAULT_SEARXNG_LANGUAGE = "all"
DEFAULT_SEARXNG_SAFESEARCH = 0
DEFAULT_SEARXNG_TIME_RANGE = ""
DEFAULT_SEARXNG_CATEGORIES = ""
DEFAULT_SEARXNG_ENGINES = ""

STRING_SETTINGS = {
    "gemini_api_key": ("GEMINI_API_KEY", ""),
    "openrouter_api_key": ("OPENROUTER_API_KEY", ""),
    "gemini_api_version": ("GEMINI_API_VERSION", DEFAULT_GEMINI_API_VERSION),
    "agent_llm_provider": ("AGENT_LLM_PROVIDER", DEFAULT_AGENT_PROVIDER),
    "summary_model": ("SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL),
    "agent_llm_model": ("AGENT_LLM_MODEL", DEFAULT_AGENT_MODEL),
    "summary_timezone": ("SUMMARY_TIMEZONE", DEFAULT_TIMEZONE),
    "mobile_system_prompt": ("MOBILE_SYSTEM_PROMPT", ""),
    "mobile_model": ("MOBILE_MODEL", GEMINI_LITE_MODEL),
    "tavily_api_key": ("TAVILY_API_KEY", ""),
    "search_provider": ("SEARCH_PROVIDER", DEFAULT_SEARCH_PROVIDER),
    "searxng_base_url": ("SEARXNG_BASE_URL", DEFAULT_SEARXNG_BASE_URL),
    "searxng_language": ("SEARXNG_LANGUAGE", DEFAULT_SEARXNG_LANGUAGE),
    "searxng_time_range": ("SEARXNG_TIME_RANGE", DEFAULT_SEARXNG_TIME_RANGE),
    "searxng_categories": ("SEARXNG_CATEGORIES", DEFAULT_SEARXNG_CATEGORIES),
    "searxng_engines": ("SEARXNG_ENGINES", DEFAULT_SEARXNG_ENGINES),
    "telegram_api_id": ("TG_API_ID", ""),
    "telegram_api_hash": ("TG_API_HASH", ""),
    "telegram_phone_number": ("TG_PHONE_NUMBER", ""),
    "telegram_session_name": ("TG_SESSION_NAME", "telegram"),
    "telegram_log_level": ("TG_LOG_LEVEL", "info"),
    "telegram_bot_token": ("TG_BOT_TOKEN", ""),
    "telegram_bot_username": ("TG_BOT_USERNAME", ""),
    "whatsapp_phone_number": ("WA_PHONE_NUMBER", ""),
    "whatsapp_log_level": ("WA_LOG_LEVEL", "info"),
}

INT_SETTINGS = {
    "summary_run_interval_seconds": (
        "SUMMARY_RUN_INTERVAL_SECONDS",
        DEFAULT_SUMMARY_RUN_INTERVAL_SECONDS,
    ),
    "summary_max_messages": ("SUMMARY_MAX_MESSAGES", DEFAULT_SUMMARY_MAX_MESSAGES),
    "summary_max_chars": ("SUMMARY_MAX_CHARS", DEFAULT_SUMMARY_MAX_CHARS),
    "searxng_timeout_seconds": (
        "SEARXNG_TIMEOUT_SECONDS",
        DEFAULT_SEARXNG_TIMEOUT_SECONDS,
    ),
    "searxng_max_results": ("SEARXNG_MAX_RESULTS", DEFAULT_SEARXNG_MAX_RESULTS),
    "searxng_safe_search": ("SEARXNG_SAFESEARCH", DEFAULT_SEARXNG_SAFESEARCH),
    RETENTION_KEY: ("NEWS_RETENTION_DAYS", DEFAULT_RETENTION_DAYS),
    CHAT_RETENTION_KEY: ("CHAT_RETENTION_DAYS", DEFAULT_CHAT_RETENTION_DAYS),
}

BOOL_SETTINGS = {
    "telegram_include_private": ("TG_INCLUDE_PRIVATE", False),
    "telegram_log_groups": ("TG_LOG_GROUPS", False),
    "telegram_enabled": ("TG_ENABLED", True),
    "telegram_bot_enabled": ("TG_BOT_ENABLED", False),
    "whatsapp_enabled": ("WA_ENABLED", True),
}


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


def _get_config_value(db: Session, key: str, env_key: str, default: str | int) -> tuple[str | int, str]:
    try:
        row = db.execute(
            text(
                "SELECT config_value FROM system_config WHERE config_key = :key LIMIT 1"
            ),
            {"key": key},
        ).fetchone()
    except Exception as exc:
        logger.warning("Failed to read config %s: %s", key, exc)
        row = None

    if row and row[0] is not None:
        return row[0], "config"
    env_value = os.getenv(env_key)
    if env_value is not None and env_value != "":
        return env_value, "env"
    return default, "default"


def _get_string_setting(db: Session, key: str) -> str:
    env_key, default = STRING_SETTINGS[key]
    value, _ = _get_config_value(db, key, env_key, default)
    return str(value) if value is not None else str(default)


def _get_int_setting(db: Session, key: str) -> int:
    env_key, default = INT_SETTINGS[key]
    value, _ = _get_config_value(db, key, env_key, default)
    return _parse_int_value(value, int(default))


def _get_bool_setting(db: Session, key: str) -> bool:
    env_key, default = BOOL_SETTINGS[key]
    value, _ = _get_config_value(db, key, env_key, default)
    return _parse_bool_value(value, bool(default))


def _clamp_days(value: int) -> int:
    if value < MIN_RETENTION_DAYS:
        return MIN_RETENTION_DAYS
    if value > MAX_RETENTION_DAYS:
        return MAX_RETENTION_DAYS
    return value


def _clamp_chat_days(value: int) -> int:
    if value < MIN_CHAT_RETENTION_DAYS:
        return MIN_CHAT_RETENTION_DAYS
    if value > MAX_CHAT_RETENTION_DAYS:
        return MAX_CHAT_RETENTION_DAYS
    return value


def _clamp_range(value: int, minimum: int, maximum: int) -> int:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _get_retention_days(db: Session) -> tuple[int, str]:
    env_key, default = INT_SETTINGS[RETENTION_KEY]
    value, source = _get_config_value(db, RETENTION_KEY, env_key, default)
    parsed = _parse_int_value(value, int(default))
    return _clamp_days(parsed), source


def _get_chat_retention_days(db: Session) -> tuple[int, str]:
    env_key, default = INT_SETTINGS[CHAT_RETENTION_KEY]
    value, source = _get_config_value(db, CHAT_RETENTION_KEY, env_key, default)
    parsed = _parse_int_value(value, int(default))
    return _clamp_chat_days(parsed), source


def _get_agent_provider(db: Session) -> str:
    provider = _get_string_setting(db, "agent_llm_provider").strip().lower()
    if provider not in {"openrouter", "gemini"}:
        return DEFAULT_AGENT_PROVIDER
    return provider


def _get_agent_model(db: Session, provider: str) -> str:
    if provider == "gemini":
        return GEMINI_LITE_MODEL
    
    default = DEFAULT_OPENROUTER_AGENT_MODEL
    value, _ = _get_config_value(db, "agent_llm_model", "AGENT_LLM_MODEL", default)
    model = str(value).strip() if value is not None else str(default)
    if not model:
        return default
    if provider == "openrouter":
        if model.startswith("gemini") or model.startswith("models/"):
            return default
    return model


def _get_summary_model(db: Session, provider: str) -> str:
    if provider == "gemini":
        return GEMINI_LITE_MODEL
        
    default = DEFAULT_OPENROUTER_SUMMARY_MODEL
    value, _ = _get_config_value(db, "summary_model", "SUMMARY_MODEL", default)
    model = str(value).strip() if value is not None else str(default)
    if not model:
        return default
    if provider == "openrouter":
        if model.startswith("gemini") or model.startswith("models/"):
            return default
    return model


def _parse_openrouter_price(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_openrouter_free(pricing: dict[str, object] | None) -> bool:
    if not pricing:
        return False
    values = []
    for key in ("prompt", "completion", "request", "image"):
        if key in pricing:
            values.append(_parse_openrouter_price(pricing.get(key)))
    if not values:
        return False
    return all(price == 0.0 for price in values)


def _fetch_openrouter_models(api_key: str) -> list[dict[str, object]]:
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip()
    if not base_url:
        base_url = DEFAULT_OPENROUTER_BASE_URL
    base_url = base_url.rstrip("/")
    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if title:
        headers["X-Title"] = title
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=OPENROUTER_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
        payload = json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise HTTPException(
            status_code=502, detail=f"OpenRouter error {exc.code}: {body}"
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenRouter network error: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="OpenRouter response invalid.") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    items = data if isinstance(data, list) else []
    models: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        name = str(item.get("name") or model_id).strip()
        pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
        models.append(
            {
                "id": model_id,
                "name": name or model_id,
                "context_length": item.get("context_length"),
                "is_free": _is_openrouter_free(pricing),
            }
        )

    models.sort(key=lambda model: (0 if model.get("is_free") else 1, model.get("id", "")))
    return models


def _upsert_config(db: Session, key: str, value: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO system_config (config_key, config_value)
            VALUES (:key, :value)
            ON CONFLICT (config_key)
            DO UPDATE SET config_value = EXCLUDED.config_value
            """
        ),
        {"key": key, "value": value},
    )


def _serialize_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _build_settings(db: Session) -> dict:
    retention_days, retention_source = _get_retention_days(db)
    chat_days, chat_source = _get_chat_retention_days(db)
    provider = _get_string_setting(db, "search_provider").strip().lower()
    if provider not in {"searxng", "disabled"}:
        provider = DEFAULT_SEARCH_PROVIDER
    agent_provider = _get_agent_provider(db)
    agent_model = _get_agent_model(db, agent_provider)
    summary_model = _get_summary_model(db, agent_provider)
    safe_search = _clamp_range(_get_int_setting(db, "searxng_safe_search"), 0, 2)
    max_results = _clamp_range(_get_int_setting(db, "searxng_max_results"), 1, 50)
    timeout_seconds = _clamp_range(
        _get_int_setting(db, "searxng_timeout_seconds"), 3, 60
    )
    return {
        "keys": {
            "gemini_api_key": _get_string_setting(db, "gemini_api_key"),
            "openrouter_api_key": _get_string_setting(db, "openrouter_api_key"),
            "tavily_api_key": _get_string_setting(db, "tavily_api_key"),
        },
        "ai": {
            "gemini_api_version": _get_string_setting(db, "gemini_api_version"),
            "agent_llm_provider": agent_provider,
            "summary_model": summary_model,
            "agent_llm_model": agent_model,
            "summary_timezone": _get_string_setting(db, "summary_timezone"),
            "summary_run_interval_seconds": _get_int_setting(
                db, "summary_run_interval_seconds"
            ),
            "summary_max_messages": _get_int_setting(db, "summary_max_messages"),
            "summary_max_chars": _get_int_setting(db, "summary_max_chars"),
        },
        "search": {
            "provider": provider,
            "searxng_base_url": _get_string_setting(db, "searxng_base_url"),
            "searxng_timeout_seconds": timeout_seconds,
            "searxng_max_results": max_results,
            "searxng_language": _get_string_setting(db, "searxng_language"),
            "searxng_safe_search": safe_search,
            "searxng_time_range": _get_string_setting(db, "searxng_time_range"),
            "searxng_categories": _get_string_setting(db, "searxng_categories"),
            "searxng_engines": _get_string_setting(db, "searxng_engines"),
        },
        "retention": {
            "days": retention_days,
            "min_days": MIN_RETENTION_DAYS,
            "max_days": MAX_RETENTION_DAYS,
            "source": retention_source,
        },
        "chat_retention": {
            "days": chat_days,
            "min_days": MIN_CHAT_RETENTION_DAYS,
            "max_days": MAX_CHAT_RETENTION_DAYS,
            "source": chat_source,
        },
        "telegram": {
            "enabled": _get_bool_setting(db, "telegram_enabled"),
            "api_id": _get_string_setting(db, "telegram_api_id"),
            "api_hash": _get_string_setting(db, "telegram_api_hash"),
            "phone_number": _get_string_setting(db, "telegram_phone_number"),
            "session_name": _get_string_setting(db, "telegram_session_name"),
            "log_level": _get_string_setting(db, "telegram_log_level"),
            "include_private": _get_bool_setting(db, "telegram_include_private"),
            "log_groups": _get_bool_setting(db, "telegram_log_groups"),
        },
        "telegram_bot": {
            "enabled": _get_bool_setting(db, "telegram_bot_enabled"),
            "token": _get_string_setting(db, "telegram_bot_token"),
            "username": _get_string_setting(db, "telegram_bot_username"),
        },
        "whatsapp": {
            "enabled": _get_bool_setting(db, "whatsapp_enabled"),
            "phone_number": _get_string_setting(db, "whatsapp_phone_number"),
            "log_level": _get_string_setting(db, "whatsapp_log_level"),
        },
    }


@router.get("/retention", response_model=schemas.RetentionSettingsRead)
def get_retention_settings(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
):
    days, source = _get_retention_days(db)
    return {
        "days": days,
        "min_days": MIN_RETENTION_DAYS,
        "max_days": MAX_RETENTION_DAYS,
        "source": source,
    }


@router.put("/retention", response_model=schemas.RetentionSettingsRead)
def update_retention_settings(
    payload: schemas.RetentionSettings,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
):
    days = _clamp_days(payload.days)
    _upsert_config(db, RETENTION_KEY, str(days))
    db.commit()
    return {
        "days": days,
        "min_days": MIN_RETENTION_DAYS,
        "max_days": MAX_RETENTION_DAYS,
        "source": "config",
    }


@router.get("", response_model=schemas.SettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
):
    return _build_settings(db)


@router.get("/openrouter/models")
def get_openrouter_models(
    db: Session = Depends(get_db),
    x_openrouter_key: str | None = Header(default=None, alias="X-OpenRouter-Key"),
    _access: models.User | None = Depends(require_admin),
):
    api_key = (x_openrouter_key or _get_string_setting(db, "openrouter_api_key")).strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key is missing.")
    models = _fetch_openrouter_models(api_key)
    return {"models": models, "count": len(models)}


@router.put("", response_model=schemas.SettingsRead)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin),
):
    if payload.keys:
        if payload.keys.gemini_api_key is not None:
            _upsert_config(
                db, "gemini_api_key", _serialize_value(payload.keys.gemini_api_key)
            )
        if payload.keys.openrouter_api_key is not None:
            _upsert_config(
                db,
                "openrouter_api_key",
                _serialize_value(payload.keys.openrouter_api_key),
            )
        if payload.keys.tavily_api_key is not None:
            _upsert_config(
                db, "tavily_api_key", _serialize_value(payload.keys.tavily_api_key)
            )

    if payload.ai:
        ai = payload.ai
        if ai.gemini_api_version is not None:
            _upsert_config(
                db, "gemini_api_version", _serialize_value(ai.gemini_api_version)
            )
        if ai.agent_llm_provider is not None:
            _upsert_config(
                db, "agent_llm_provider", _serialize_value(ai.agent_llm_provider)
            )
        if ai.summary_model is not None:
            _upsert_config(db, "summary_model", _serialize_value(ai.summary_model))
        if ai.agent_llm_model is not None:
            _upsert_config(db, "agent_llm_model", _serialize_value(ai.agent_llm_model))
        if ai.summary_timezone is not None:
            _upsert_config(db, "summary_timezone", _serialize_value(ai.summary_timezone))
        if ai.summary_run_interval_seconds is not None:
            _upsert_config(
                db,
                "summary_run_interval_seconds",
                _serialize_value(ai.summary_run_interval_seconds),
            )
        if ai.summary_max_messages is not None:
            _upsert_config(
                db, "summary_max_messages", _serialize_value(ai.summary_max_messages)
            )
        if ai.summary_max_chars is not None:
            _upsert_config(
                db, "summary_max_chars", _serialize_value(ai.summary_max_chars)
            )

    if payload.search:
        search = payload.search
        if search.provider is not None:
            _upsert_config(
                db, "search_provider", _serialize_value(search.provider)
            )
        if search.searxng_base_url is not None:
            _upsert_config(
                db, "searxng_base_url", _serialize_value(search.searxng_base_url)
            )
        if search.searxng_timeout_seconds is not None:
            _upsert_config(
                db,
                "searxng_timeout_seconds",
                _serialize_value(search.searxng_timeout_seconds),
            )
        if search.searxng_max_results is not None:
            _upsert_config(
                db,
                "searxng_max_results",
                _serialize_value(search.searxng_max_results),
            )
        if search.searxng_language is not None:
            _upsert_config(
                db, "searxng_language", _serialize_value(search.searxng_language)
            )
        if search.searxng_safe_search is not None:
            _upsert_config(
                db,
                "searxng_safe_search",
                _serialize_value(search.searxng_safe_search),
            )
        if search.searxng_time_range is not None:
            _upsert_config(
                db,
                "searxng_time_range",
                _serialize_value(search.searxng_time_range),
            )
        if search.searxng_categories is not None:
            _upsert_config(
                db,
                "searxng_categories",
                _serialize_value(search.searxng_categories),
            )
        if search.searxng_engines is not None:
            _upsert_config(
                db,
                "searxng_engines",
                _serialize_value(search.searxng_engines),
            )

    if payload.retention:
        days = _clamp_days(payload.retention.days)
        _upsert_config(db, RETENTION_KEY, str(days))

    if payload.chat_retention:
        days = _clamp_chat_days(payload.chat_retention.days)
        _upsert_config(db, CHAT_RETENTION_KEY, str(days))

    if payload.telegram:
        tg = payload.telegram
        if tg.enabled is not None:
            _upsert_config(db, "telegram_enabled", _serialize_value(tg.enabled))
        if tg.api_id is not None:
            _upsert_config(db, "telegram_api_id", _serialize_value(tg.api_id))
        if tg.api_hash is not None:
            _upsert_config(db, "telegram_api_hash", _serialize_value(tg.api_hash))
        if tg.phone_number is not None:
            _upsert_config(
                db, "telegram_phone_number", _serialize_value(tg.phone_number)
            )
        if tg.session_name is not None:
            _upsert_config(
                db, "telegram_session_name", _serialize_value(tg.session_name)
            )
        if tg.log_level is not None:
            _upsert_config(db, "telegram_log_level", _serialize_value(tg.log_level))
        if tg.include_private is not None:
            _upsert_config(
                db,
                "telegram_include_private",
                _serialize_value(tg.include_private),
            )
        if tg.log_groups is not None:
            _upsert_config(
                db, "telegram_log_groups", _serialize_value(tg.log_groups)
            )
    if payload.telegram_bot:
        bot = payload.telegram_bot
        if bot.enabled is not None:
            _upsert_config(db, "telegram_bot_enabled", _serialize_value(bot.enabled))
        if bot.token is not None:
            _upsert_config(db, "telegram_bot_token", _serialize_value(bot.token))
        if bot.username is not None:
            _upsert_config(db, "telegram_bot_username", _serialize_value(bot.username))

    if payload.whatsapp:
        wa = payload.whatsapp
        if wa.enabled is not None:
            _upsert_config(db, "whatsapp_enabled", _serialize_value(wa.enabled))
        if wa.phone_number is not None:
            _upsert_config(
                db, "whatsapp_phone_number", _serialize_value(wa.phone_number)
            )
        if wa.log_level is not None:
            _upsert_config(db, "whatsapp_log_level", _serialize_value(wa.log_level))

    db.commit()
    return _build_settings(db)


@router.get("/runtime")
def get_runtime_settings(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_admin_or_ingest),
):
    return {
        "telegram": {
            "enabled": _get_bool_setting(db, "telegram_enabled"),
            "api_id": _get_string_setting(db, "telegram_api_id"),
            "api_hash": _get_string_setting(db, "telegram_api_hash"),
            "phone_number": _get_string_setting(db, "telegram_phone_number"),
            "session_name": _get_string_setting(db, "telegram_session_name"),
            "log_level": _get_string_setting(db, "telegram_log_level"),
            "include_private": _get_bool_setting(db, "telegram_include_private"),
            "log_groups": _get_bool_setting(db, "telegram_log_groups"),
        },
        "telegram_bot": {
            "enabled": _get_bool_setting(db, "telegram_bot_enabled"),
            "token": _get_string_setting(db, "telegram_bot_token"),
            "username": _get_string_setting(db, "telegram_bot_username"),
        },
        "whatsapp": {
            "enabled": _get_bool_setting(db, "whatsapp_enabled"),
            "phone_number": _get_string_setting(db, "whatsapp_phone_number"),
            "log_level": _get_string_setting(db, "whatsapp_log_level"),
        },
    }

class MobileConfig(BaseModel):
    system_prompt: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.3
    features: dict[str, bool] = {"local_search": True, "voice": False}


@router.get("/mobile-config", response_model=MobileConfig)
def get_mobile_config(
    db: Session = Depends(get_db),
    _access: models.User | None = Depends(require_user_or_admin_key),
):
    """
    Get configuration for the mobile app agent.
    This allows updating the agent's behavior remotely without app updates.
    """
    # Get system prompt form config or usage default
    system_prompt = _get_string_setting(db, "mobile_system_prompt")
    if not system_prompt:
        system_prompt = (
            "You are 'The Journalist Assistant' (مساعد الصحفي), created by Hassan Qaddour (known as Abu Noah). "
            "Your role is to assist journalists by answering questions based on the provided news context. "
            "IMPORTANT: Greet the user (e.g., 'حياك الله' or 'هلا بالورد') ONLY once at the very beginning of the chat or if they explicitly greet you. "
            "Do NOT repeat greetings in every message. Stay professional and direct in follow-up messages. "
            "Adapt your tone: "
            "- For casual users: Humorous and warm (use 'هلا بالورد', 'أبشر'). "
            "- For formal users: Strictly professional. "
            "GUIDELINES for CONTEXT:"
            "1. If the user engages in small talk (e.g., 'hello', 'how represent you'), reply naturally and briefly. Do NOT look for news."
            "2. If the user asks for news (e.g., 'what happened today?') and you have context, summarize it clearly."
            "3. If the user asks for specific news and NO context is provided in your prompt, clearly state that you don't have information on that specific topic in your current database. Do NOT hallunicate or invent news."
            "Always be direct and practical. Never refer to yourself as an 'AI model'. You are 'مساعد الصحفي'."
        )
    
    # Force model to available alias
    model = GEMINI_LITE_MODEL
    
    return MobileConfig(
        system_prompt=system_prompt,
        model=model,
        max_tokens=1000,
        temperature=0.3
    )
