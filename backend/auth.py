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
from datetime import datetime, timedelta
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


def create_user(
    username: str, email: str, password: str, role: str = "user"
) -> dict[str, Any]:
    """Create an account. Raises ValueError for invalid/duplicate details."""
    username, email = _validate(username, email, password)
    if role not in ("user", "admin"):
        raise ValueError("Invalid account role.")
    user_id = secrets.token_hex(16)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (id, username, email, password_hash, role) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username, email, hash_password(password), role),
            )
    except Exception as exc:
        text = str(exc).lower()
        if "username" in text:
            raise ValueError("That username is already taken.") from None
        if "email" in text:
            raise ValueError("That email is already registered.") from None
        raise BackendError("Could not create the account.") from exc
    return {"id": user_id, "username": username, "email": email, "role": role}


def authenticate(identifier: str, password: str) -> dict[str, Any] | None:
    """Return the user on valid credentials, otherwise None."""
    identifier = clean_text(identifier, 120).lower()
    now = time.time()
    recent = _failed.get(identifier)
    if recent and now - recent[1] < _WINDOW_SECONDS and recent[0] >= _MAX_ATTEMPTS:
        return None

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email, password_hash, is_active, role FROM users "
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
            "role": row["role"] or "user",
        }

    count, _ = _failed.get(identifier, (0, now))
    _failed[identifier] = (count + 1, now)
    return None


SESSION_HOURS = 12


def create_session(user_id: str) -> str:
    """Create a persistent web session. The token goes in the URL, never the password."""
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=SESSION_HOURS)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO web_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )
    return token


def get_session_user(token: str | None) -> dict[str, Any] | None:
    """Resolve a URL session token back to an active user."""
    if not token:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT u.id, u.username, u.email, u.role FROM web_sessions s "
            "JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND u.is_active = 1 AND s.expires_at > ?",
            (token, datetime.now().isoformat()),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"] or "user",
    }


def delete_session(token: str | None) -> None:
    if not token:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM web_sessions WHERE token = ?", (token,))


def get_user(user_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email, role FROM users WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    """Admin-only listing of all accounts with their order counts."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT u.id, u.username, u.email, u.role, u.is_active, u.created_at, "
            "       COUNT(o.id) AS orders, COALESCE(SUM(o.total_amount), 0) AS spent "
            "FROM users u LEFT JOIN orders o ON o.session_id = 'user_' || u.id "
            "GROUP BY u.id ORDER BY u.created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def set_user_active(user_id: str, active: bool) -> bool:
    """Admin-only account enable/disable. Never disables the last admin."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row and row["role"] == "admin" and not active:
            admins = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1"
            ).fetchone()[0]
            if admins <= 1:
                return False
        cursor = conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if active else 0, user_id),
        )
        return cursor.rowcount > 0


def promote_to_admin(identifier: str) -> dict[str, Any]:
    """Promote an existing account to admin (used by the bootstrap CLI)."""
    identifier = clean_text(identifier, 120).lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email, role FROM users "
            "WHERE LOWER(username)=? OR LOWER(email)=?",
            (identifier, identifier),
        ).fetchone()
        if not row:
            raise ValueError("No account with that username or email exists.")
        conn.execute("UPDATE users SET role='admin' WHERE id=?", (row["id"],))
    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": "admin"}
