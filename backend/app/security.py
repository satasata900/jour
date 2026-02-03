import base64
import hashlib
import hmac
import os
import secrets
from typing import Final

SCHEME: Final = "pbkdf2_sha256"
DEFAULT_ITERATIONS: Final = 260_000
SALT_BYTES: Final = 16

_SESSION_TOKENS: dict[str, int] = {}


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, DEFAULT_ITERATIONS
    )
    return (
        f"{SCHEME}${DEFAULT_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('utf-8')}$"
        f"{base64.b64encode(digest).decode('utf-8')}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
    except ValueError:
        return False
    if scheme != SCHEME:
        return False
    try:
        rounds = int(iterations)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))
    except (ValueError, OSError):
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, rounds
    )
    return hmac.compare_digest(candidate, expected)


def issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _SESSION_TOKENS[token] = user_id
    return token


def get_user_id_for_token(token: str) -> int | None:
    return _SESSION_TOKENS.get(token)


def revoke_token(token: str) -> None:
    _SESSION_TOKENS.pop(token, None)
