import asyncio
import contextlib
import logging
import os
import time
from datetime import timezone
from urllib.parse import urljoin

import httpx
from telethon import TelegramClient, events

SETTINGS_CACHE_TTL_SEC = 30.0
SYNC_INTERVAL_SEC = float(os.getenv("TG_SYNC_INTERVAL_SEC", "300"))


def _ingest_headers() -> dict[str, str]:
    token = os.getenv("INGEST_TOKEN", "").strip()
    if not token:
        return {}
    return {"X-Ingest-Token": token}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_chat_name(chat) -> str:
    if not chat:
        return "unknown"
    title = getattr(chat, "title", None)
    if title:
        return title
    username = getattr(chat, "username", None)
    if username:
        return f"@{username}"
    first = getattr(chat, "first_name", "") or ""
    last = getattr(chat, "last_name", "") or ""
    name = f"{first} {last}".strip()
    return name or str(getattr(chat, "id", "unknown"))


def get_sender_name(sender) -> str | None:
    if not sender:
        return None
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    first = getattr(sender, "first_name", "") or ""
    last = getattr(sender, "last_name", "") or ""
    name = f"{first} {last}".strip()
    return name or str(getattr(sender, "id", ""))


async def list_groups(client: TelegramClient, logger: logging.Logger) -> None:
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group or d.is_channel]
    groups.sort(key=lambda d: (d.name or "").lower())
    logger.info("Groups (%d):", len(groups))
    for dialog in groups:
        entity = dialog.entity
        title = dialog.name or getattr(entity, "title", "") or "unknown"
        logger.info("- %s (%s)", title, getattr(entity, "id", "unknown"))


async def send_to_backend(
    http: httpx.AsyncClient, logger: logging.Logger, payload: dict
) -> None:
    try:
        response = await http.post(
            os.getenv("BACKEND_INGEST_URL", "http://backend:8000/news"),
            json=payload,
            headers=_ingest_headers(),
        )
        if response.status_code >= 400:
            logger.error("ingest failed %s %s", response.status_code, response.text)
    except Exception as exc:
        logger.exception("ingest error: %s", exc)


async def fetch_sources(
    http: httpx.AsyncClient, logger: logging.Logger, platform: str
) -> list[dict] | None:
    try:
        sources_url = urljoin(
            os.getenv("BACKEND_INGEST_URL", "http://backend:8000/news"),
            "/sources",
        )
        response = await http.get(
            sources_url,
            params={"platform": platform},
            headers=_ingest_headers(),
        )
        if response.status_code == 401 or response.status_code == 403:
            logger.error("source list unauthorized; check INGEST_TOKEN.")
        if response.status_code >= 400:
            logger.error("source list failed %s %s", response.status_code, response.text)
            return None
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.exception("source list error: %s", exc)
        return None


async def fetch_runtime_settings(
    http: httpx.AsyncClient, logger: logging.Logger
) -> dict | None:
    try:
        settings_url = urljoin(
            os.getenv("BACKEND_INGEST_URL", "http://backend:8000/news"),
            "/settings/runtime",
        )
        response = await http.get(settings_url, headers=_ingest_headers())
        if response.status_code == 401 or response.status_code == 403:
            logger.error("settings fetch unauthorized; check INGEST_TOKEN.")
        if response.status_code >= 400:
            logger.error(
                "settings fetch failed %s %s", response.status_code, response.text
            )
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.exception("settings fetch error: %s", exc)
        return None


def merge_telegram_settings(raw: dict | None) -> dict:
    raw = raw or {}
    return {
        "enabled": bool(raw.get("enabled", True)),
        "api_id": raw.get("api_id") or os.getenv("TG_API_ID"),
        "api_hash": raw.get("api_hash") or os.getenv("TG_API_HASH"),
        "phone_number": raw.get("phone_number") or os.getenv("TG_PHONE_NUMBER"),
        "session_name": raw.get("session_name") or os.getenv("TG_SESSION_NAME", "telegram"),
        "log_level": raw.get("log_level") or os.getenv("TG_LOG_LEVEL", "INFO"),
        "include_private": bool(raw.get("include_private", env_bool("TG_INCLUDE_PRIVATE", False))),
        "log_groups": bool(raw.get("log_groups", env_bool("TG_LOG_GROUPS", False))),
    }


async def create_source(
    http: httpx.AsyncClient, logger: logging.Logger, payload: dict
) -> None:
    try:
        sources_url = urljoin(
            os.getenv("BACKEND_INGEST_URL", "http://backend:8000/news"),
            "/sources",
        )
        response = await http.post(
            sources_url,
            json=payload,
            headers=_ingest_headers(),
        )
        if response.status_code == 401 or response.status_code == 403:
            logger.error("source create unauthorized; check INGEST_TOKEN.")
        if response.status_code in {200, 201, 409}:
            return
        logger.error("source create failed %s %s", response.status_code, response.text)
    except Exception as exc:
        logger.exception("source create error: %s", exc)


async def update_source(
    http: httpx.AsyncClient, logger: logging.Logger, source_id: int, payload: dict
) -> None:
    try:
        sources_url = urljoin(
            os.getenv("BACKEND_INGEST_URL", "http://backend:8000/news"),
            f"/sources/{source_id}",
        )
        response = await http.patch(
            sources_url,
            json=payload,
            headers=_ingest_headers(),
        )
        if response.status_code == 401 or response.status_code == 403:
            logger.error("source update unauthorized; check INGEST_TOKEN.")
        if response.status_code >= 400:
            logger.error("source update failed %s %s", response.status_code, response.text)
    except Exception as exc:
        logger.exception("source update error: %s", exc)




async def main() -> None:
    log_level = os.getenv("TG_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("telegram")

    session_dir = os.getenv("TG_SESSION_DIR", os.path.join(os.getcwd(), "session"))
    os.makedirs(session_dir, exist_ok=True)

    async with httpx.AsyncClient(timeout=10.0) as http:
        settings_cache: dict[str, dict] = {
            "fetched_at": 0.0,
            "telegram": merge_telegram_settings({}),
        }

        async def get_telegram_settings() -> dict:
            now = time.monotonic()
            if (
                not settings_cache["fetched_at"]
                or now - settings_cache["fetched_at"] > SETTINGS_CACHE_TTL_SEC
            ):
                runtime = await fetch_runtime_settings(http, logger)
                if runtime and isinstance(runtime.get("telegram"), dict):
                    settings_cache["telegram"] = merge_telegram_settings(
                        runtime.get("telegram")
                    )
                settings_cache["fetched_at"] = now
            return settings_cache["telegram"]

        while True:
            settings = await get_telegram_settings()
            if not settings.get("enabled", True):
                logger.info("Telegram connector disabled; waiting 30s.")
                await asyncio.sleep(30)
                continue

            api_id = settings.get("api_id")
            api_hash = settings.get("api_hash")
            if not api_id or not api_hash:
                logger.error("Missing TG_API_ID or TG_API_HASH.")
                await asyncio.sleep(30)
                continue

            session_name = settings.get("session_name", "telegram")
            session_path = os.path.join(session_dir, session_name)
            include_private = bool(settings.get("include_private", False))
            log_groups = bool(settings.get("log_groups", False))

            client = TelegramClient(session_path, int(api_id), api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                logger.error(
                    "Telegram not authorized. Run: docker compose exec -it telegram python src/login.py"
                )
                await client.disconnect()
                await asyncio.sleep(30)
                continue

            if log_groups:
                try:
                    await list_groups(client, logger)
                except Exception as exc:
                    logger.exception("group list failed: %s", exc)

            async def fetch_existing_sources() -> list[dict]:
                sources = await fetch_sources(http, logger, "telegram")
                return sources if sources is not None else []

            async def sync_group_sources() -> None:
                dialogs = await client.get_dialogs()
                groups = [d for d in dialogs if d.is_group or d.is_channel]
                existing_sources = await fetch_existing_sources()
                existing_by_id = {
                    str(source.get("identifier")): source for source in existing_sources
                }
                current_ids = {str(dialog.id) for dialog in groups}
                created = 0
                renamed = 0
                enabled = 0
                disabled = 0
                for dialog in groups:
                    identifier = str(dialog.id)
                    entity = dialog.entity
                    name = dialog.name or getattr(entity, "title", "") or "unknown"
                    existing = existing_by_id.get(identifier)
                    if existing:
                        if existing.get("name") != name:
                            await update_source(
                                http, logger, existing["id"], {"name": name}
                            )
                            renamed += 1
                        if existing.get("is_active") is False:
                            await update_source(
                                http, logger, existing["id"], {"is_active": True}
                            )
                            enabled += 1
                        continue
                    await create_source(
                        http,
                        logger,
                        {
                            "name": name,
                            "platform": "telegram",
                            "identifier": identifier,
                            "is_active": True,
                        },
                    )
                    created += 1
                for identifier, source in existing_by_id.items():
                    if identifier not in current_ids:
                        if source.get("is_active") is True:
                            await update_source(
                                http, logger, source["id"], {"is_active": False}
                            )
                            disabled += 1
                if created or renamed or enabled or disabled:
                    logger.info(
                        "Sources synced: added %d, renamed %d, enabled %d, disabled %d.",
                        created,
                        renamed,
                        enabled,
                        disabled,
                    )

            try:
                await sync_group_sources()
            except Exception as exc:
                logger.exception("group source sync failed: %s", exc)

            async def sync_loop() -> None:
                interval = max(30.0, SYNC_INTERVAL_SEC)
                while True:
                    try:
                        await sync_group_sources()
                    except Exception as exc:
                        logger.exception("group source sync failed: %s", exc)
                    await asyncio.sleep(interval)

            @client.on(events.NewMessage)
            async def handle_message(event):  # noqa: ANN001
                if event.out:
                    return
                settings = await get_telegram_settings()
                if not settings.get("enabled", True):
                    return
                allow_private = bool(settings.get("include_private", include_private))
                if event.is_private and not allow_private:
                    return

                message = event.message
                if not message:
                    return

                text = (message.message or message.raw_text or "").strip()
                if not text:
                    return

                source_identifier = str(event.chat_id)
                chat = await event.get_chat()
                sender = await event.get_sender()
                author_name = get_sender_name(sender)
                payload = {
                    "source_name": get_chat_name(chat),
                    "source_identifier": source_identifier,
                    "platform": "telegram",
                    "source_message_id": f"{event.chat_id}:{message.id}",
                    "author_name": author_name,
                    "content": text,
                    "timestamp": (
                        message.date.replace(tzinfo=timezone.utc)
                        if message.date.tzinfo is None
                        else message.date.astimezone(timezone.utc)
                    ).isoformat(),
                }
                await send_to_backend(http, logger, payload)

            sync_task = asyncio.create_task(sync_loop())
            logger.info("Telegram listener started.")
            try:
                await client.run_until_disconnected()
            finally:
                sync_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await sync_task
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
