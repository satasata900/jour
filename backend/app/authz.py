import os

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import get_user_id_for_token

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "").strip()


def _admin_key_valid(value: str | None) -> bool:
    if not ADMIN_API_KEY:
        return False
    return (value or "").strip() == ADMIN_API_KEY


def _ingest_token_valid(value: str | None) -> bool:
    if not INGEST_TOKEN:
        return False
    return (value or "").strip() == INGEST_TOKEN


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token."
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )
    user_id = get_user_id_for_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled."
        )
    return user


def require_user_or_admin_key(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> models.User | None:
    if _admin_key_valid(x_admin_key):
        return None
    return get_current_user(db=db, authorization=authorization)


def require_admin(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> models.User | None:
    if _admin_key_valid(x_admin_key):
        return None
    user = get_current_user(db=db, authorization=authorization)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def require_admin_or_ingest(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> models.User | None:
    if _admin_key_valid(x_admin_key) or _ingest_token_valid(x_ingest_token):
        return None
    user = get_current_user(db=db, authorization=authorization)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
