import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import text

from app import models
from app.database import SessionLocal

logger = logging.getLogger("telegram_bot")

DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_POLL_TIMEOUT_SECONDS = 10


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


def _get_bool_setting(db, key: str, env_key: str, default: bool) -> bool:
    return _parse_bool_value(_get_config_value(db, key, env_key, default), default)


def _get_int_setting(db, key: str, env_key: str, default: int) -> int:
    value = _get_config_value(db, key, env_key, default)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _upsert_config(db, key: str, value: str | int) -> None:
    db.execute(
        text(
            """
            INSERT INTO system_config (config_key, config_value)
            VALUES (:key, :value)
            ON CONFLICT (config_key)
            DO UPDATE SET config_value = EXCLUDED.config_value
            """
        ),
        {"key": key, "value": str(value)},
    )
    db.commit()


def get_bot_config(db) -> dict[str, str | bool]:
    token = _get_string_setting(db, "telegram_bot_token", "TG_BOT_TOKEN", "").strip()
    username = _get_string_setting(
        db, "telegram_bot_username", "TG_BOT_USERNAME", ""
    ).strip()
    enabled = _get_bool_setting(db, "telegram_bot_enabled", "TG_BOT_ENABLED", False)
    return {"token": token, "username": username, "enabled": enabled}


def _call_bot_api(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "description": body, "error_code": exc.code}
    except URLError as exc:
        logger.error("Telegram network error: %s", exc.reason)
        return {"ok": False, "description": str(exc.reason)}
    except Exception as exc:
        logger.exception("Telegram request failed: %s", exc)
        return {"ok": False, "description": str(exc)}


def fetch_bot_username(token: str) -> str | None:
    payload = _call_bot_api(token, "getMe", {})
    if not payload.get("ok"):
        return None
    result = payload.get("result") or {}
    return result.get("username")


def ensure_bot_username(db, token: str) -> str | None:
    username = _get_string_setting(
        db, "telegram_bot_username", "TG_BOT_USERNAME", ""
    ).strip()
    if username:
        return username
    fetched = fetch_bot_username(token)
    if fetched:
        _upsert_config(db, "telegram_bot_username", fetched)
    return fetched


def send_message(token: str, chat_id: int, text: str) -> dict[str, int | bool | None]:
    payload = _call_bot_api(token, "sendMessage", {"chat_id": chat_id, "text": text})
    if payload.get("ok"):
        return {"ok": True, "retry_after": None}
    params = payload.get("parameters") or {}
    retry_after = params.get("retry_after")
    return {"ok": False, "retry_after": retry_after}


def _get_update_offset(db) -> int:
    return _get_int_setting(db, "telegram_bot_update_offset", "TG_BOT_OFFSET", 0)


def _set_update_offset(db, offset: int) -> None:
    _upsert_config(db, "telegram_bot_update_offset", offset)


def _handle_start_command(db, chat_id: int, token: str, username: str | None) -> str:
    if not token:
        return "Use the app to link your Telegram account."
    user = (
        db.query(models.User).filter(models.User.telegram_link_token == token).first()
    )
    if not user:
        return "Link token not found. Please reconnect from the app."

    existing = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if existing and existing.id != user.id:
        existing.telegram_chat_id = None
        existing.telegram_username = None
        existing.telegram_linked_at = None
        existing.telegram_daily_enabled = False
        existing.telegram_weekly_enabled = False
        existing.telegram_monthly_enabled = False

    user.telegram_chat_id = chat_id
    user.telegram_username = username
    user.telegram_linked_at = datetime.now(timezone.utc)
    db.commit()
    return "Telegram linked. You can enable summaries in the app."


def _handle_stop_command(db, chat_id: int) -> str:
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if user:
        user.telegram_chat_id = None
        user.telegram_username = None
        user.telegram_linked_at = None
        user.telegram_daily_enabled = False
        user.telegram_weekly_enabled = False
        user.telegram_monthly_enabled = False
        db.commit()
    return "Unsubscribed. You can link again from the app anytime."


def _process_update(db, update: dict, token: str) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return
    chat_id = chat.get("id")
    if chat_id is None:
        return
    text = message.get("text") or ""
    if not text:
        return
    username = chat.get("username") or (message.get("from") or {}).get("username")

    if text.startswith("/start"):
        token_value = ""
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            token_value = parts[1].strip()
        reply = _handle_start_command(db, chat_id, token_value, username)
        send_message(token, chat_id, reply)
    elif text.startswith("/stop"):
        reply = _handle_stop_command(db, chat_id)
        send_message(token, chat_id, reply)


def _poll_updates(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        with SessionLocal() as db:
            config = get_bot_config(db)
            token = config.get("token") or ""
            if not config.get("enabled") or not token:
                stop_event.wait(DEFAULT_POLL_INTERVAL_SECONDS)
                continue
            offset = _get_update_offset(db)
            payload = {
                "timeout": DEFAULT_POLL_TIMEOUT_SECONDS,
                "allowed_updates": ["message"],
            }
            if offset:
                payload["offset"] = offset
            data = _call_bot_api(token, "getUpdates", payload)
            updates = data.get("result") if data.get("ok") else None
            if isinstance(updates, list) and updates:
                for update in updates:
                    _process_update(db, update, token)
                    update_id = update.get("update_id")
                    if isinstance(update_id, int) and update_id >= offset:
                        offset = update_id + 1
                _set_update_offset(db, offset)
        stop_event.wait(DEFAULT_POLL_INTERVAL_SECONDS)


def start_telegram_bot_worker(app) -> None:
    stop_event = threading.Event()
    thread = threading.Thread(target=_poll_updates, args=(stop_event,), daemon=True)
    thread.start()
    app.state.telegram_bot_stop_event = stop_event
    app.state.telegram_bot_thread = thread


def stop_telegram_bot_worker(app) -> None:
    stop_event = getattr(app.state, "telegram_bot_stop_event", None)
    if stop_event:
        stop_event.set()
    thread = getattr(app.state, "telegram_bot_thread", None)
    if thread:
        thread.join(timeout=5)
