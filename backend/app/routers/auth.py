import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_user_id_for_token, hash_password, issue_token, verify_password
from app.authz import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTRATION_KEY = "registration_enabled"


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_registration_enabled(db: Session) -> bool:
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


def _normalize_username(value: str) -> str:
    return value.strip().lower()


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    username = _normalize_username(payload.username)
    user = (
        db.query(models.User).filter(models.User.username == username).first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")
    user.last_login_at = func.now()
    db.add(user)
    db.commit()
    db.refresh(user)
    token = issue_token(user.id)
    return {"token": token, "user": user}


@router.post("/register", response_model=schemas.LoginResponse)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if not _is_registration_enabled(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled.",
        )
    username = _normalize_username(payload.username)
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")
    user = models.User(
        username=username,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role="journalist",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = issue_token(user.id)
    return {"token": token, "user": user}


@router.get("/me", response_model=schemas.UserRead)
def me(user: models.User = Depends(get_current_user)):
    return user
