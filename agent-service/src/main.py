import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=os.getenv("AGENT_LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("agent-service")


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://app:app@db:5432/app_db"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

DEFAULT_AGENT_DEFS: dict[str, dict[str, Any]] = {
    "router": {
        "key": "router",
        "name": "Router",
        "description": "Routes tasks to the best agent.",
        "agent_type": "router",
        "system_prompt": (
            "You are a router that assigns a task to one of the agents: "
            "monitor, editor, search, or general. "
            "monitor = SQL analysis of News_Archive or monitoring reports. "
            "editor = rewrite or summarize content. "
            "search = web lookup or verification. "
            "general = anything else."
        ),
        "user_prompt": "Task: {task}\nContext: {context}\n{format_instructions}",
        "is_active": True,
    },
    "monitor": {
        "key": "monitor",
        "name": "Monitor",
        "description": "Summarizes volume and trends from recent messages.",
        "agent_type": "monitor",
        "system_prompt": (
            "You are a newsroom monitoring analyst. "
            "Write the response in Arabic. "
            "Use concise bullet points and highlight notable changes."
        ),
        "user_prompt": "Time window: {window}\nStats (JSON): {stats}\n",
        "is_active": True,
    },
    "editor": {
        "key": "editor",
        "name": "Editor",
        "description": "Summarizes or rewrites content into concise bullets.",
        "agent_type": "editor",
        "system_prompt": (
            "You are a newsroom editor. "
            "Write the response in Arabic. "
            "Provide 5-12 concise bullets and avoid speculation."
        ),
        "user_prompt": "Task: {task}\nContent:\n{content}",
        "is_active": True,
    },
    "search": {
        "key": "search",
        "name": "Search",
        "description": "Uses SearXNG for external verification.",
        "agent_type": "search",
        "system_prompt": "Search agent uses SearXNG and returns raw results.",
        "user_prompt": "Query: {task}",
        "is_active": True,
    },
    "general": {
        "key": "general",
        "name": "General",
        "description": "Handles general newsroom tasks.",
        "agent_type": "general",
        "system_prompt": "You are a newsroom assistant. Write the response in Arabic.",
        "user_prompt": "Task: {task}\nContext: {context}",
        "is_active": True,
    },
}

DEFAULT_GEMINI_AGENT_MODEL = "gemini-2.0-flash"
DEFAULT_OPENROUTER_MODEL = "openrouter/auto"
DEFAULT_AGENT_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OpenRouter fallback chain: try free models first, then cheap paid ones
# Order: Best free models → Good free models → Cheap paid models
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
    "openai/gpt-4o-mini",                       # $0.15/M input - good value
]



class RouteDecision(BaseModel):
    route: str = Field(..., description="Which agent should handle the task.")
    reason: str = Field(..., description="Why the route was chosen.")


class AgentRequest(BaseModel):
    task: str = Field(..., min_length=1)
    context: str | None = None
    route: str | None = None
    window_hours: int | None = Field(default=24, ge=1, le=168)
    max_items: int | None = Field(default=50, ge=1, le=200)
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None


class AgentResponse(BaseModel):
    route: str
    output: str
    meta: dict[str, Any] = Field(default_factory=dict)


def _normalize_model(model: str) -> str:
    normalized = model.strip()
    if normalized.startswith("models/"):
        return normalized.split("/", 1)[1]
    return normalized


def _get_config_value(key: str, env_key: str, default: str) -> str:
    try:
        with SessionLocal() as db:
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
        return str(row[0])
    env_value = os.getenv(env_key)
    if env_value is not None and env_value != "":
        return env_value
    return default


def _get_llm_provider() -> str:
    provider = _get_config_value(
        "agent_llm_provider", "AGENT_LLM_PROVIDER", DEFAULT_AGENT_PROVIDER
    ).strip().lower()
    if provider not in {"openrouter", "gemini"}:
        return DEFAULT_AGENT_PROVIDER
    return provider


def _get_agent_model(provider: str) -> str:
    default = (
        DEFAULT_OPENROUTER_MODEL if provider == "openrouter" else DEFAULT_GEMINI_AGENT_MODEL
    )
    model = _get_config_value("agent_llm_model", "AGENT_LLM_MODEL", default).strip()
    if not model:
        model = default
    if provider == "openrouter":
        if model.startswith("gemini") or model.startswith("models/"):
            model = default
        return model
    if "/" in model and not model.startswith("models/"):
        model = default
    return _normalize_model(model)


def _get_gemini_config(api_key_override: str | None = None) -> tuple[str, str, str]:
    api_key = (api_key_override or _get_config_value("gemini_api_key", "GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    model = _get_agent_model("gemini")
    api_version = _get_config_value("gemini_api_version", "GEMINI_API_VERSION", "v1").strip().lstrip("/")
    if not api_version:
        api_version = "v1"
    return api_key, model, api_version


def _get_openrouter_config(
    api_key_override: str | None = None,
) -> tuple[str, str, str]:
    api_key = (
        api_key_override
        or _get_config_value("openrouter_api_key", "OPENROUTER_API_KEY", "")
    ).strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")
    model = _get_agent_model("openrouter")
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip()
    if not base_url:
        base_url = DEFAULT_OPENROUTER_BASE_URL
    return api_key, model, base_url.rstrip("/")


def _parse_int(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_search_provider() -> str:
    provider = _get_config_value("search_provider", "SEARCH_PROVIDER", "searxng")
    return provider.strip().lower() or "searxng"


def _get_searxng_settings() -> dict[str, Any]:
    base_url = _get_config_value(
        "searxng_base_url", "SEARXNG_BASE_URL", "http://searxng:8080"
    ).strip()
    if not base_url:
        base_url = "http://searxng:8080"
    base_url = base_url.rstrip("/")
    return {
        "base_url": base_url,
        "timeout_seconds": _parse_int(
            _get_config_value("searxng_timeout_seconds", "SEARXNG_TIMEOUT_SECONDS", "15"),
            15,
        ),
        "max_results": _parse_int(
            _get_config_value("searxng_max_results", "SEARXNG_MAX_RESULTS", "5"),
            5,
        ),
        "language": _get_config_value("searxng_language", "SEARXNG_LANGUAGE", "all")
        .strip()
        .lower()
        or "all",
        "safe_search": _parse_int(
            _get_config_value("searxng_safe_search", "SEARXNG_SAFESEARCH", "0"),
            0,
        ),
        "time_range": _get_config_value("searxng_time_range", "SEARXNG_TIME_RANGE", "").strip(),
        "categories": _parse_csv(
            _get_config_value("searxng_categories", "SEARXNG_CATEGORIES", "")
        ),
        "engines": _parse_csv(
            _get_config_value("searxng_engines", "SEARXNG_ENGINES", "")
        ),
    }


def _messages_to_prompt(messages: list[Any]) -> str:
    role_map = {"system": "System", "human": "User", "ai": "Assistant"}
    lines: list[str] = []
    for message in messages:
        role = getattr(message, "type", None) or getattr(message, "role", "user")
        label = role_map.get(str(role).lower(), str(role).title())
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=True)
        lines.append(f"{label}: {content}")
    return "\n".join(lines).strip()


def _messages_to_openai(messages: list[Any]) -> list[dict[str, str]]:
    role_map = {"system": "system", "human": "user", "ai": "assistant"}
    payload: list[dict[str, str]] = []
    for message in messages:
        role = getattr(message, "type", None) or getattr(message, "role", "user")
        mapped = role_map.get(str(role).lower(), "user")
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=True)
        payload.append({"role": mapped, "content": content})
    if not payload:
        payload.append({"role": "user", "content": ""})
    return payload


def _call_gemini(
    prompt: str,
    temperature: float = 0.2,
    api_key_override: str | None = None,
) -> str:
    api_key, model, api_version = _get_gemini_config(api_key_override)
    url = (
        f"https://generativelanguage.googleapis.com/{api_version}/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "topP": 0.8, "maxOutputTokens": 1024},
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"Gemini error {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    candidates = parsed.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini response missing candidates.")
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts:
        raise RuntimeError("Gemini response missing content parts.")
    text = parts[0].get("text")
    if not text:
        raise RuntimeError("Gemini response missing text.")
    return text.strip()


def _call_openrouter_single(
    messages: list[Any],
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.2,
) -> str:
    """Call OpenRouter with a specific model. Raises on error."""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": _messages_to_openai(messages),
        "temperature": temperature,
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
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"OpenRouter error {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"OpenRouter timeout for model {model}") from exc

    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter response missing choices.")
    message = choices[0].get("message") or {}
    text = message.get("content")
    if not text:
        raise RuntimeError("OpenRouter response missing content.")
    return str(text).strip()


def _call_openrouter(
    messages: list[Any],
    temperature: float = 0.2,
    api_key_override: str | None = None,
) -> str:
    """
    Call OpenRouter with smart fallback.
    Tries the configured model first, then falls back through free → cheap paid models.
    """
    api_key, configured_model, base_url = _get_openrouter_config(api_key_override)
    
    # Build model chain: configured model first, then fallback list
    models_to_try = [configured_model] + [m for m in OPENROUTER_FALLBACK_MODELS if m != configured_model]
    
    last_error = None
    for model in models_to_try:
        try:
            result = _call_openrouter_single(messages, model, api_key, base_url, temperature)
            if model != configured_model:
                logger.info("Used fallback model: %s", model)
            return result
        except RuntimeError as exc:
            error_str = str(exc)
            # Check for rate limit, model not found, or timeout errors - retry with next model
            if "429" in error_str or "404" in error_str or "rate" in error_str.lower() or "timeout" in error_str.lower():
                logger.warning("Model %s failed (%s), trying next...", model, error_str[:80])
                last_error = exc
                continue
            # For other errors, don't retry
            raise
    
    # All models failed
    raise last_error or RuntimeError("All OpenRouter models failed")


def _invoke_llm(
    messages: list[Any],
    temperature: float = 0.2,
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> str:
    provider = _get_llm_provider()
    if provider == "openrouter":
        return _call_openrouter(
            messages,
            temperature=temperature,
            api_key_override=openrouter_api_key_override,
        )
    prompt = _messages_to_prompt(messages)
    return _call_gemini(
        prompt, temperature=temperature, api_key_override=gemini_api_key_override
    )


def _parse_route_decision(content: str) -> RouteDecision:
    try:
        return ROUTER_PARSER.parse(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return ROUTER_PARSER.parse(match.group(0))
        raise


def _fetch_agent_profiles() -> list[dict[str, Any]]:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT key, name, description, agent_type, system_prompt, user_prompt, is_active
                    FROM agent_profiles
                    ORDER BY id ASC
                    """
                )
            ).fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as exc:
        logger.warning("Failed to load agent profiles: %s", exc)
        return []


def _load_profiles() -> list[dict[str, Any]]:
    profiles = _fetch_agent_profiles()
    for profile in profiles:
        agent_type = profile.get("agent_type")
        defaults = DEFAULT_AGENT_DEFS.get(agent_type)
        if defaults:
            for field in ("system_prompt", "user_prompt"):
                if not profile.get(field):
                    profile[field] = defaults[field]
    return profiles


def _find_profile_by_key(profiles: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for profile in profiles:
        if profile.get("key") == key:
            return profile
    return None


def _active_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [profile for profile in profiles if profile.get("is_active", True)]


def _prompt_from_profile(profile: dict[str, Any]) -> tuple[str, str]:
    agent_type = profile.get("agent_type")
    defaults = DEFAULT_AGENT_DEFS.get(agent_type, {})
    system_prompt = profile.get("system_prompt") or defaults.get("system_prompt", "")
    user_prompt = profile.get("user_prompt") or defaults.get("user_prompt", "")
    return system_prompt, user_prompt


ROUTER_PARSER = PydanticOutputParser(pydantic_object=RouteDecision)


def _build_messages(system_prompt: str, user_prompt: str, **values: Any) -> list[Any]:
    template = ChatPromptTemplate.from_messages(
        [("system", system_prompt.strip()), ("human", user_prompt.strip())]
    )
    return template.format_messages(**values)


def _route_task(
    task: str,
    context: str | None,
    profiles: list[dict[str, Any]],
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> RouteDecision:
    active_profiles = _active_profiles(profiles)
    available = [
        profile for profile in active_profiles if profile.get("agent_type") != "router"
    ]
    if not available:
        available = active_profiles

    available_keys = {profile.get("key") for profile in available if profile.get("key")}
    router_profile = next(
        (profile for profile in active_profiles if profile.get("agent_type") == "router"),
        None,
    )

    route_lines = "\n".join(
        f"- {profile.get('key')}: {profile.get('description') or profile.get('agent_type')}"
        for profile in available
    ).strip()

    if router_profile and available:
        try:
            system_prompt, user_prompt = _prompt_from_profile(router_profile)
            system_prompt = (
                f"{system_prompt}\nAvailable routes:\n{route_lines}\n"
                "Return a JSON object that matches the schema."
            )
            messages = _build_messages(
                system_prompt,
                user_prompt,
                task=task,
                context=context or "",
                format_instructions=ROUTER_PARSER.get_format_instructions(),
            )
            content = _invoke_llm(
                messages,
                temperature=0.0,
                gemini_api_key_override=gemini_api_key_override,
                openrouter_api_key_override=openrouter_api_key_override,
            )
            decision = _parse_route_decision(content)
            decision.route = decision.route.strip().lower()
            if decision.route in available_keys:
                return decision
            logger.warning("Router returned unknown route: %s", decision.route)
        except Exception as exc:
            logger.warning("Router fallback: %s", exc)

    lowered = f"{task} {context or ''}".lower()
    target_type = "general"
    if any(token in lowered for token in ["sql", "monitor", "trend", "volume", "count"]):
        target_type = "monitor"
    elif any(token in lowered for token in ["summary", "summarize", "rewrite", "edit"]):
        target_type = "editor"
    elif any(token in lowered for token in ["search", "verify", "source", "lookup"]):
        target_type = "search"

    for profile in available:
        if profile.get("agent_type") == target_type:
            return RouteDecision(route=profile.get("key") or "", reason="keyword match")

    if available:
        return RouteDecision(route=available[0].get("key") or "", reason="default")

    return RouteDecision(route="general", reason="default")


def _fetch_recent_messages(window_hours: int, limit: int) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=window_hours)
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT source_name, author_name, content, timestamp, platform
                FROM news_archive
                WHERE timestamp >= :start AND timestamp < :end
                ORDER BY timestamp DESC
                LIMIT :limit
                """
            ),
            {"start": start, "end": end, "limit": limit},
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def _fetch_latest_summary() -> dict[str, Any] | None:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT period_type, period_start, period_end, content
                    FROM summaries
                    ORDER BY period_end DESC
                    LIMIT 1
                    """
                )
            ).fetchone()
        return dict(row._mapping) if row else None
    except Exception as exc:
        logger.warning("Failed to load summaries: %s", exc)
        return None


def _fetch_summaries_for_context(hours: int = 24) -> str:
    """
    Fetch relevant summaries for agent context.
    Prioritizes: daily > interval summaries within the time window.
    Returns formatted text suitable for LLM context.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    
    try:
        with SessionLocal() as db:
            # First try to get daily summary for today
            daily = db.execute(
                text(
                    """
                    SELECT period_type, period_start, period_end, content
                    FROM summaries
                    WHERE period_type = 'daily'
                    AND period_end >= :start
                    ORDER BY period_end DESC
                    LIMIT 1
                    """
                ),
                {"start": start},
            ).fetchone()
            
            if daily and daily.content:
                period_label = f"ملخص يومي ({daily.period_start:%Y-%m-%d})"
                return f"### {period_label}\n{daily.content}"
            
            # Fall back to interval summaries
            intervals = db.execute(
                text(
                    """
                    SELECT period_type, period_start, period_end, content
                    FROM summaries
                    WHERE period_type = 'interval'
                    AND period_end >= :start
                    ORDER BY period_end DESC
                    LIMIT 5
                    """
                ),
                {"start": start},
            ).fetchall()
            
            if intervals:
                lines = ["### ملخصات الفترة الأخيرة"]
                for row in intervals:
                    time_label = row.period_end.strftime("%Y-%m-%d %H:%M") if row.period_end else ""
                    lines.append(f"\n#### ملخص {time_label}")
                    lines.append(row.content or "")
                return "\n".join(lines)
            
            # Final fallback: any recent summary
            any_summary = db.execute(
                text(
                    """
                    SELECT period_type, period_start, period_end, content
                    FROM summaries
                    ORDER BY period_end DESC
                    LIMIT 1
                    """
                )
            ).fetchone()
            
            if any_summary and any_summary.content:
                period_label = f"آخر ملخص ({any_summary.period_type})"
                return f"### {period_label}\n{any_summary.content}"
            
            return ""
    except Exception as exc:
        logger.warning("Failed to fetch summaries for context: %s", exc)
        return ""


def _format_summary_label(summary: dict[str, Any]) -> str:
    period_type = summary.get("period_type") or "summary"
    start = summary.get("period_start")
    end = summary.get("period_end")
    if isinstance(start, datetime) and isinstance(end, datetime):
        return f"{period_type} summary ({start:%Y-%m-%d} -> {end:%Y-%m-%d})"
    return f"{period_type} summary"


def _monitor_agent(
    window_hours: int,
    profile: dict[str, Any],
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> tuple[str, dict[str, Any]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=window_hours)
    with SessionLocal() as db:
        total = db.execute(
            text(
                "SELECT COUNT(*) FROM news_archive WHERE timestamp >= :start AND timestamp < :end"
            ),
            {"start": start, "end": end},
        ).scalar() or 0
        platforms = db.execute(
            text(
                """
                SELECT platform, COUNT(*) AS count
                FROM news_archive
                WHERE timestamp >= :start AND timestamp < :end
                GROUP BY platform
                ORDER BY count DESC
                """
            ),
            {"start": start, "end": end},
        ).fetchall()
        top_sources = db.execute(
            text(
                """
                SELECT source_name, COUNT(*) AS count
                FROM news_archive
                WHERE timestamp >= :start AND timestamp < :end
                GROUP BY source_name
                ORDER BY count DESC
                LIMIT 10
                """
            ),
            {"start": start, "end": end},
        ).fetchall()
        top_authors = db.execute(
            text(
                """
                SELECT author_name, COUNT(*) AS count
                FROM news_archive
                WHERE timestamp >= :start AND timestamp < :end
                  AND author_name IS NOT NULL
                GROUP BY author_name
                ORDER BY count DESC
                LIMIT 10
                """
            ),
            {"start": start, "end": end},
        ).fetchall()

    stats = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "total_messages": total,
        "platforms": [dict(row._mapping) for row in platforms],
        "top_sources": [dict(row._mapping) for row in top_sources],
        "top_authors": [dict(row._mapping) for row in top_authors],
    }

    try:
        system_prompt, user_prompt = _prompt_from_profile(profile)
        messages = _build_messages(
            system_prompt,
            user_prompt,
            window=f"last {window_hours} hours",
            stats=json.dumps(stats, ensure_ascii=True),
        )
        content = _invoke_llm(
            messages,
            temperature=0.2,
            gemini_api_key_override=gemini_api_key_override,
            openrouter_api_key_override=openrouter_api_key_override,
        )
        return content.strip(), stats
    except Exception as exc:
        logger.warning("Monitor agent LLM failed: %s", exc)

    lines = [
        f"Window: {stats['window_start']} -> {stats['window_end']}",
        f"Total messages: {stats['total_messages']}",
    ]
    for row in stats["platforms"]:
        lines.append(f"{row['platform']}: {row['count']}")
    for row in stats["top_sources"]:
        lines.append(f"Source {row['source_name']}: {row['count']}")
    return "\n".join(lines), stats


def _editor_agent(
    task: str,
    context: str | None,
    window_hours: int,
    limit: int,
    profile: dict[str, Any],
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> str:
    """
    Editor agent that prioritizes summaries over raw messages.
    Only uses raw messages as a last resort to reduce token consumption.
    """
    content = (context or "").strip()
    
    if not content:
        # Priority 1: Use summaries (efficient, pre-processed)
        content = _fetch_summaries_for_context(hours=window_hours)
        
        # Priority 2: Fall back to latest summary only
        if not content:
            summary = _fetch_latest_summary()
            if summary and summary.get("content"):
                label = _format_summary_label(summary)
                content = f"{label}\n{summary['content']}".strip()
        
        # Priority 3: Only if no summaries exist, use a small sample of raw messages
        # This is a fallback for new installations or empty summary tables
        if not content:
            rows = _fetch_recent_messages(window_hours, min(limit, 10))  # Limit to 10 max
            if rows:
                lines = []
                for row in rows:
                    timestamp = row["timestamp"]
                    time_label = (
                        timestamp.astimezone(timezone.utc).strftime("%H:%M") if timestamp else "--:--"
                    )
                    # Truncate content to reduce tokens
                    msg_content = row["content"][:200] + "..." if len(row["content"]) > 200 else row["content"]
                    line = f"[{time_label}] {row['source_name']}: {msg_content}"
                    lines.append(line)
                content = "\n".join(lines)
            else:
                content = "لا توجد أخبار أو ملخصات متاحة حالياً."

    system_prompt, user_prompt = _prompt_from_profile(profile)
    messages = _build_messages(system_prompt, user_prompt, task=task, content=content)
    output = _invoke_llm(
        messages,
        temperature=0.2,
        gemini_api_key_override=gemini_api_key_override,
        openrouter_api_key_override=openrouter_api_key_override,
    )
    return output.strip()



def _searxng_search(query: str) -> tuple[str, dict[str, Any]]:
    provider = _get_search_provider()
    if provider != "searxng":
        raise RuntimeError("Search provider is disabled.")

    settings = _get_searxng_settings()
    params: dict[str, Any] = {"q": query, "format": "json"}
    if settings["language"] and settings["language"] != "all":
        params["language"] = settings["language"]
    if settings["time_range"]:
        params["time_range"] = settings["time_range"]
    if settings["safe_search"] is not None:
        params["safesearch"] = str(settings["safe_search"])
    if settings["max_results"]:
        params["results"] = str(settings["max_results"])
    if settings["categories"]:
        params["categories"] = ",".join(settings["categories"])
    if settings["engines"]:
        params["engines"] = ",".join(settings["engines"])

    url = f"{settings['base_url']}/search?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=settings["timeout_seconds"]) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"SearXNG error {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"SearXNG network error: {exc.reason}") from exc

    answers = parsed.get("answers") or []
    results = parsed.get("results") or []
    lines = []
    for answer in answers:
        if answer:
            lines.append(f"Answer: {answer}")
    for item in results:
        title = item.get("title") or "Result"
        url = item.get("url") or ""
        snippet = item.get("content") or item.get("snippet") or ""
        engine = item.get("engine") or ""
        engine_label = f" [{engine}]" if engine else ""
        line = f"- {title}{engine_label}"
        if url:
            line = f"{line} ({url})"
        if snippet:
            line = f"{line} {snippet}"
        lines.append(line.strip())
    if not lines:
        lines.append("No results returned.")
    meta = {
        "provider": provider,
        "query": query,
        "params": params,
        "result_count": len(results),
    }
    return "\n".join(lines).strip(), meta


def _general_agent(
    task: str,
    context: str | None,
    profile: dict[str, Any],
    window_hours: int = 24,
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> str:
    """
    General agent that uses summaries as context.
    If no context provided, fetches recent summaries from database.
    """
    # Build context from summaries if not provided
    effective_context = (context or "").strip()
    if not effective_context:
        effective_context = _fetch_summaries_for_context(hours=window_hours)
    
    if not effective_context:
        effective_context = "لا توجد ملخصات متاحة حالياً."
    
    system_prompt, user_prompt = _prompt_from_profile(profile)
    messages = _build_messages(
        system_prompt, user_prompt, task=task, context=effective_context
    )
    output = _invoke_llm(
        messages,
        temperature=0.2,
        gemini_api_key_override=gemini_api_key_override,
        openrouter_api_key_override=openrouter_api_key_override,
    )
    return output.strip()


def _custom_agent(
    task: str,
    context: str | None,
    profile: dict[str, Any],
    window_hours: int = 24,
    gemini_api_key_override: str | None = None,
    openrouter_api_key_override: str | None = None,
) -> str:
    """
    Custom agent that uses summaries as context.
    Allows user-defined prompts while automatically providing news summaries.
    """
    # For post writers, do not auto-inject summaries. Use only provided context.
    key = (profile.get("key") or "").strip().lower()
    effective_context = (context or "").strip()
    if key not in {"post_official", "post_casual"}:
        if not effective_context:
            effective_context = _fetch_summaries_for_context(hours=window_hours)
        if not effective_context:
            effective_context = "لا توجد ملخصات متاحة حالياً."
    
    system_prompt, user_prompt = _prompt_from_profile(profile)
    if not system_prompt:
        system_prompt = DEFAULT_AGENT_DEFS["general"]["system_prompt"]
    if not user_prompt:
        user_prompt = DEFAULT_AGENT_DEFS["general"]["user_prompt"]
    messages = _build_messages(
        system_prompt, user_prompt, task=task, context=effective_context
    )
    output = _invoke_llm(
        messages,
        temperature=0.2,
        gemini_api_key_override=gemini_api_key_override,
        openrouter_api_key_override=openrouter_api_key_override,
    )
    return output.strip()



app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agents/run", response_model=AgentResponse)
def run_agent(request: AgentRequest) -> AgentResponse:
    try:
        profiles = _load_profiles()
        if not profiles:
            raise HTTPException(status_code=400, detail="No agents configured.")

        gemini_api_key_override = request.gemini_api_key
        openrouter_api_key_override = request.openrouter_api_key
        if request.route:
            route_key = request.route.strip().lower()
            profile = _find_profile_by_key(profiles, route_key)
            if not profile:
                raise HTTPException(status_code=404, detail="Agent route not found.")
            if not profile.get("is_active", True):
                raise HTTPException(status_code=400, detail="Agent route is inactive.")
            decision = RouteDecision(route=route_key, reason="manual override")
        else:
            try:
                decision = _route_task(
                    request.task,
                    request.context,
                    profiles,
                    gemini_api_key_override=gemini_api_key_override,
                    openrouter_api_key_override=openrouter_api_key_override,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        route_key = decision.route.strip().lower()
        profile = _find_profile_by_key(profiles, route_key)
        if not profile:
            active = _active_profiles(profiles)
            if not active:
                raise HTTPException(status_code=400, detail="No active agents configured.")
            profile = active[0]
            route_key = profile.get("key", "unknown")

        window_hours = request.window_hours or 24
        max_items = request.max_items or 50
        agent_type = profile.get("agent_type", "general")

        if agent_type == "router":
            decision = _route_task(
                request.task,
                request.context,
                profiles,
                gemini_api_key_override=gemini_api_key_override,
                openrouter_api_key_override=openrouter_api_key_override,
            )
            payload = decision.model_dump()
            return AgentResponse(route=route_key, output=json.dumps(payload), meta=payload)
        if agent_type == "monitor":
            output, stats = _monitor_agent(
                window_hours,
                profile,
                gemini_api_key_override=gemini_api_key_override,
                openrouter_api_key_override=openrouter_api_key_override,
            )
            return AgentResponse(route=route_key, output=output, meta=stats)
        if agent_type == "editor":
            output = _editor_agent(
                request.task,
                request.context,
                window_hours,
                max_items,
                profile,
                gemini_api_key_override=gemini_api_key_override,
                openrouter_api_key_override=openrouter_api_key_override,
            )
            return AgentResponse(route=route_key, output=output)
        if agent_type == "search":
            try:
                output, meta = _searxng_search(request.task)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            return AgentResponse(route=route_key, output=output, meta=meta)
        if agent_type == "custom":
            output = _custom_agent(
                request.task,
                request.context,
                profile,
                window_hours=window_hours,
                gemini_api_key_override=gemini_api_key_override,
                openrouter_api_key_override=openrouter_api_key_override,
            )
            return AgentResponse(route=route_key, output=output)

        output = _general_agent(
            request.task,
            request.context,
            profile,
            window_hours=window_hours,
            gemini_api_key_override=gemini_api_key_override,
            openrouter_api_key_override=openrouter_api_key_override,
        )
        return AgentResponse(route=route_key, output=output)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
