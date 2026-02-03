import csv
import os
from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.authz import require_admin
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])

REGISTRATION_KEY = "registration_enabled"


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_registration_enabled(db: Session) -> bool:
    row = db.execute(
        text(
            "SELECT config_value FROM system_config WHERE config_key = :key LIMIT 1"
        ),
        {"key": REGISTRATION_KEY},
    ).fetchone()
    if row and row[0] is not None:
        return _parse_bool(row[0], True)
    env_value = os.getenv("REGISTRATION_ENABLED")
    if env_value is not None and env_value != "":
        return _parse_bool(env_value, True)
    return True


def _set_registration_enabled(db: Session, enabled: bool) -> None:
    db.execute(
        text(
            """
            INSERT INTO system_config (config_key, config_value)
            VALUES (:key, :value)
            ON CONFLICT (config_key)
            DO UPDATE SET config_value = EXCLUDED.config_value
            """
        ),
        {"key": REGISTRATION_KEY, "value": "true" if enabled else "false"},
    )
    db.commit()


def _normalize_username(value: str) -> str:
    return value.strip().lower()


def _normalize_display_name(value: str) -> str:
    return value.strip()


@router.get("/stats", response_model=schemas.UserStatsRead)
def user_stats(db: Session = Depends(get_db)):
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = (
        db.query(func.count(models.User.id))
        .filter(models.User.is_active.is_(True))
        .scalar()
        or 0
    )
    total_sessions = db.query(func.count(models.ChatSession.id)).scalar() or 0
    total_messages = db.query(func.count(models.ChatMessage.id)).scalar() or 0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
    }


@router.get("", response_model=schemas.UserListRead)
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    sessions_sub = (
        db.query(
            models.ChatSession.user_id.label("user_id"),
            func.count(models.ChatSession.id).label("session_count"),
            func.max(models.ChatSession.updated_at).label("last_session_at"),
        )
        .group_by(models.ChatSession.user_id)
        .subquery()
    )
    messages_sub = (
        db.query(
            models.ChatSession.user_id.label("user_id"),
            func.count(models.ChatMessage.id).label("message_count"),
        )
        .join(models.ChatMessage, models.ChatMessage.session_id == models.ChatSession.id)
        .group_by(models.ChatSession.user_id)
        .subquery()
    )
    base_query = db.query(models.User)
    if search:
        term = f"%{search.strip().lower()}%"
        base_query = base_query.filter(
            func.lower(models.User.username).like(term)
            | func.lower(func.coalesce(models.User.display_name, "")).like(term)
        )
    if is_active is not None:
        base_query = base_query.filter(models.User.is_active.is_(is_active))
    total = base_query.count()

    query = (
        db.query(
            models.User,
            sessions_sub.c.session_count,
            sessions_sub.c.last_session_at,
            messages_sub.c.message_count,
        )
        .outerjoin(sessions_sub, sessions_sub.c.user_id == models.User.id)
        .outerjoin(messages_sub, messages_sub.c.user_id == models.User.id)
    )
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(models.User.username).like(term)
            | func.lower(func.coalesce(models.User.display_name, "")).like(term)
        )
    if is_active is not None:
        query = query.filter(models.User.is_active.is_(is_active))
    results = (
        query.order_by(models.User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    payload: list[schemas.UserAdminRead] = []
    for user, session_count, last_session_at, message_count in results:
        payload.append(
            schemas.UserAdminRead(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                role=user.role,
                created_at=user.created_at,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                session_count=session_count or 0,
                message_count=message_count or 0,
                last_session_at=last_session_at,
            )
        )
    return {"items": payload, "total": total}


@router.get("/registration", response_model=schemas.RegistrationStatusRead)
def registration_status(db: Session = Depends(get_db)):
    return {"enabled": _get_registration_enabled(db)}


@router.patch("/registration", response_model=schemas.RegistrationStatusRead)
def update_registration(payload: schemas.RegistrationUpdate, db: Session = Depends(get_db)):
    _set_registration_enabled(db, payload.enabled)
    return {"enabled": payload.enabled}


@router.post("", response_model=schemas.UserRead)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
    user = models.User(
        username=username,
        display_name=_normalize_display_name(payload.display_name),
        password_hash=hash_password(payload.password),
        role="journalist",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.username is not None:
        username = _normalize_username(payload.username)
        existing = (
            db.query(models.User)
            .filter(models.User.username == username, models.User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists.")
        user.username = username
    if payload.display_name is not None:
        user.display_name = _normalize_display_name(payload.display_name)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: schemas.UserPasswordReset,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.password_hash = hash_password(payload.password)
    db.add(user)
    db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)
    db.commit()
    return {"status": "ok"}


@router.get("/export")
def export_users(db: Session = Depends(get_db)):
    sessions_sub = (
        db.query(
            models.ChatSession.user_id.label("user_id"),
            func.count(models.ChatSession.id).label("session_count"),
            func.max(models.ChatSession.updated_at).label("last_session_at"),
        )
        .group_by(models.ChatSession.user_id)
        .subquery()
    )
    messages_sub = (
        db.query(
            models.ChatSession.user_id.label("user_id"),
            func.count(models.ChatMessage.id).label("message_count"),
        )
        .join(models.ChatMessage, models.ChatMessage.session_id == models.ChatSession.id)
        .group_by(models.ChatSession.user_id)
        .subquery()
    )
    rows = (
        db.query(
            models.User,
            sessions_sub.c.session_count,
            sessions_sub.c.last_session_at,
            messages_sub.c.message_count,
        )
        .outerjoin(sessions_sub, sessions_sub.c.user_id == models.User.id)
        .outerjoin(messages_sub, messages_sub.c.user_id == models.User.id)
        .order_by(models.User.created_at.desc())
        .all()
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "display_name",
            "username",
            "role",
            "is_active",
            "created_at",
            "last_login_at",
            "session_count",
            "message_count",
            "last_session_at",
        ]
    )
    for user, session_count, last_session_at, message_count in rows:
        writer.writerow(
            [
                user.id,
                user.display_name or "",
                user.username,
                user.role,
                "true" if user.is_active else "false",
                user.created_at.isoformat() if user.created_at else "",
                user.last_login_at.isoformat() if user.last_login_at else "",
                session_count or 0,
                message_count or 0,
                last_session_at.isoformat() if last_session_at else "",
            ]
        )
    filename = f"users_export_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/backup")
def backup_users(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    sessions = db.query(models.ChatSession).order_by(models.ChatSession.id.asc()).all()
    messages = db.query(models.ChatMessage).order_by(models.ChatMessage.id.asc()).all()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "users": [
            {
                "id": user.id,
                "display_name": user.display_name,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
                if user.created_at
                else None,
                "last_login_at": user.last_login_at.isoformat()
                if user.last_login_at
                else None,
            }
            for user in users
        ],
        "chat_sessions": [
            {
                "id": session.id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at.isoformat()
                if session.created_at
                else None,
                "updated_at": session.updated_at.isoformat()
                if session.updated_at
                else None,
            }
            for session in sessions
        ],
        "chat_messages": [
            {
                "id": message.id,
                "session_id": message.session_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat()
                if message.created_at
                else None,
            }
            for message in messages
        ],
    }
