import os

import os

from sqlalchemy.orm import Session

from app import models
from app.security import hash_password

DEFAULT_TEST_EMAIL = "demo@jour2.local"
DEFAULT_TEST_PASSWORD = "Jour2Demo123!"


def _normalize_username(value: str) -> str:
    return value.strip().lower()


def seed_test_user(db: Session) -> models.User | None:
    if os.getenv("SEED_TEST_USER", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None
    email = _normalize_username(os.getenv("TEST_USER_EMAIL", DEFAULT_TEST_EMAIL))
    password = os.getenv("TEST_USER_PASSWORD", DEFAULT_TEST_PASSWORD)
    if not email or not password:
        return None

    existing = (
        db.query(models.User).filter(models.User.username == email).first()
    )
    if existing:
        return existing

    display_name = email.split("@", 1)[0] if "@" in email else email
    user = models.User(
        username=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
