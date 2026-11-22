"""Persistent, session-isolated conversation storage in SQLite."""

import uuid
from typing import Any

from .database import get_connection


def new_conversation_id() -> str:
    return uuid.uuid4().hex


def create_conversation(session_id: str, conversation_id: str | None = None, title: str = "New chat") -> str:
    conversation_id = conversation_id or new_conversation_id()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, session_id, title) VALUES (?, ?, ?)",
            (conversation_id, session_id, title),
        )
    return conversation_id


def append_message(
    conversation_id: str,
    role: str,
    content: str,
    client_id: str | None = None,
) -> None:
    """Store a message. ``client_id`` makes Streamlit reruns idempotent."""
    if role not in ("user", "assistant", "system"):
        raise ValueError("Unsupported message role.")
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_messages (conversation_id, role, content, client_id) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, client_id),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )


def get_messages(conversation_id: str) -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
    return [{"role": row[0], "content": row[1]} for row in rows]


def list_conversations(session_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE session_id = ? ORDER BY updated_at DESC",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_conversation(conversation_id: str, session_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND session_id = ?",
            (conversation_id, session_id),
        )
        return cursor.rowcount > 0
