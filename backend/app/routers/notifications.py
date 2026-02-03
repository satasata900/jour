import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, telegram_bot
from app.database import get_db
from app.authz import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _ensure_link_token(db: Session, user: models.User) -> str:
    if user.telegram_link_token:
        return user.telegram_link_token
    for _ in range(5):
        token = secrets.token_urlsafe(16)
        existing = (
            db.query(models.User)
            .filter(models.User.telegram_link_token == token)
            .first()
        )
        if existing:
            continue
        user.telegram_link_token = token
        db.commit()
        return token
    raise HTTPException(status_code=500, detail="Failed to generate link token.")


def _build_telegram_response(db: Session, user: models.User) -> schemas.TelegramPreferencesRead:
    config = telegram_bot.get_bot_config(db)
    bot_username = config.get("username") or ""
    if config.get("enabled") and config.get("token") and not bot_username:
        bot_username = telegram_bot.ensure_bot_username(db, config["token"]) or ""
    link_token = _ensure_link_token(db, user)
    link_url = None
    if config.get("enabled") and bot_username:
        link_url = f"https://t.me/{bot_username}?start={link_token}"
    return schemas.TelegramPreferencesRead(
        linked=user.telegram_chat_id is not None,
        chat_id=user.telegram_chat_id,
        username=user.telegram_username,
        bot_username=bot_username or None,
        link_url=link_url,
        daily_enabled=bool(user.telegram_daily_enabled),
        weekly_enabled=bool(user.telegram_weekly_enabled),
        monthly_enabled=bool(user.telegram_monthly_enabled),
    )


@router.get("/telegram", response_model=schemas.TelegramPreferencesRead)
def get_telegram_preferences(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return _build_telegram_response(db, user)


@router.put("/telegram", response_model=schemas.TelegramPreferencesRead)
def update_telegram_preferences(
    payload: schemas.TelegramPreferencesUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if payload.daily_enabled is not None:
        user.telegram_daily_enabled = payload.daily_enabled
    if payload.weekly_enabled is not None:
        user.telegram_weekly_enabled = payload.weekly_enabled
    if payload.monthly_enabled is not None:
        user.telegram_monthly_enabled = payload.monthly_enabled
    db.commit()
    return _build_telegram_response(db, user)


@router.post("/telegram/unlink", response_model=schemas.TelegramPreferencesRead)
def unlink_telegram(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    user.telegram_chat_id = None
    user.telegram_username = None
    user.telegram_linked_at = None
    user.telegram_daily_enabled = False
    user.telegram_weekly_enabled = False
    user.telegram_monthly_enabled = False
    user.telegram_link_token = None
    db.commit()
    return _build_telegram_response(db, user)
