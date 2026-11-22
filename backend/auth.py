"""Authentication with salted PBKDF2 password hashing (standard library only).

Passwords are never stored or logged in plain text. User IDs are used as the
session key for orders and chat history, so accounts cannot see each other's
data.
"""

import hashlib
import hmac
import re
import secrets
import time
from typing import Any

from .database import get_connection
from .utils import BackendError, clean_text

ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 8
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Very small in-memory throttle; sufficient for a single-process Streamlit app.
_failed: dict[str, tuple[int, float]] = {}
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return f"{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS
        )
        return hmac.compare_digest(derived.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _validate(username: str, email: str, password: str) -> tuple[str, str]:
    username = clean_text(username, 40)
    email = clean_text(email, 120).lower()
    if not _USERNAME_RE.match(username):
        raise ValueError("Username must be 3-30 letters, numbers or underscores.")
    if not _EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return username, email


def create_user(username: str, email: str, password: str) -> dict[str, Any]:
    """Create an account. Raises ValueError for invalid/duplicate details."""
    username, email = _validate(username, email, password)
    user_id = secrets.token_hex(16)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, username, email, hash_password(password)),
            )
    except Exception as exc:
        text = str(exc).lower()
        if "username" in text:
            raise ValueError("That username is already taken.") from None
        if "email" in text:
            raise ValueError("That email is already registered.") from None
        raise BackendError("Could not create the account.") from exc
    return {"id": user_id, "username": username, "email": email}


def authenticate(identifier: str, password: str) -> dict[str, Any] | None:
    """Return the user on valid credentials, otherwise None."""
    identifier = clean_text(identifier, 120).lower()
    now = time.time()
    recent = _failed.get(identifier)
    if recent and now - recent[1] < _WINDOW_SECONDS and recent[0] >= _MAX_ATTEMPTS:
        return None

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email, password_hash, is_active FROM users "
            "WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (identifier, identifier),
        ).fetchone()

    valid = bool(
        row and row["is_active"] and verify_password(password, row["password_hash"])
    )
    if valid:
        _failed.pop(identifier, None)
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
        }

    count, _ = _failed.get(identifier, (0, now))
    _failed[identifier] = (count + 1, now)
    return None


def get_user(user_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None
