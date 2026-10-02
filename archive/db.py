"""
SQLite storage for conversation-based chat history.

Schema is created on import and migrations run idempotently.
All connection handling goes through a single context manager so we never
leak file handles.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import List, Tuple, Optional, Iterator

# Database location (hidden folder in the user home directory)
DB_PATH = os.path.join(
    os.path.expanduser("~"), ".language_agnostic_chatbot", "chat_history.db"
)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    """Yield a sqlite connection that closes itself and enables FK enforcement."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()


def _get_columns(table_name: str) -> list:
    with _conn() as c:
        cur = c.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cur.fetchall()]


def _add_column(table: str, column: str, column_def: str) -> None:
    with _conn() as c:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
            c.commit()
        except sqlite3.OperationalError as exc:
            # Column likely already exists — fine. Re-raise anything else.
            if "already exists" not in str(exc).lower():
                raise


def _ensure_db() -> None:
    """Create tables and run idempotent migrations. Never deletes data."""
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
            """
        )
        c.commit()

    if "is_archived" not in _get_columns("conversations"):
        _add_column("conversations", "is_archived", "INTEGER DEFAULT 0")


# Ensure tables exist on import
_ensure_db()


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------

def create_conversation(initial_user_message: str) -> int:
    """Create a new conversation and store the first user message.

    Returns the generated conversation_id. Title is set to "Untitled"
    until update_conversation_title is called.
    """
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO conversations (title) VALUES (?)", ("Untitled",)
        )
        conversation_id = cur.lastrowid
        c.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, "user", initial_user_message),
        )
        c.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        c.commit()
        return conversation_id


def update_conversation_title(conversation_id: int, title: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, conversation_id),
        )
        c.commit()


def get_conversations(
    limit: int = 100,
    search: Optional[str] = None,
    include_archived: bool = False,
) -> List[Tuple[int, str, str, int]]:
    """Return (id, title, updated_at, is_archived) ordered by most recent activity."""
    where_clauses: list = []
    params: list = []

    if not include_archived:
        where_clauses.append("is_archived = 0")
    if search:
        where_clauses.append("lower(title) LIKE ?")
        params.append(f"%{search.lower()}%")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = (
        f"SELECT id, title, updated_at, is_archived "
        f"FROM conversations {where_sql} ORDER BY updated_at DESC LIMIT ?"
    )
    params.append(limit)

    with _conn() as c:
        cur = c.execute(query, tuple(params))
        rows = cur.fetchall()
    return [tuple(r) for r in rows]


def load_conversation_messages(conversation_id: int, limit: int = 1000) -> List[Tuple[str, str]]:
    """Load messages for a conversation in chronological order. Returns (role, content) pairs."""
    with _conn() as c:
        cur = c.execute(
            "SELECT role, content FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
            (conversation_id, limit),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def add_message(conversation_id: int, role: str, content: str) -> None:
    """Append a new message to a conversation and bump updated_at."""
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        c.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        c.commit()


def clear_conversation(conversation_id: int) -> None:
    """Delete all messages belonging to a conversation (keeps the conversation entry)."""
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        c.execute(
            "UPDATE conversations SET updated_at = created_at WHERE id = ?",
            (conversation_id,),
        )
        c.commit()


def archive_conversation(conversation_id: int) -> None:
    """Mark a conversation as archived (soft-delete from main view)."""
    with _conn() as c:
        c.execute(
            "UPDATE conversations SET is_archived = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        c.commit()


def restore_conversation(conversation_id: int) -> None:
    """Restore an archived conversation to the main view."""
    with _conn() as c:
        c.execute(
            "UPDATE conversations SET is_archived = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        c.commit()


def delete_conversation(conversation_id: int) -> None:
    """Completely remove a conversation and its messages. FK cascade deletes messages."""
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        c.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        c.commit()


def rename_conversation(conversation_id: int, title: str) -> None:
    """Alias of update_conversation_title for clarity in the UI layer."""
    update_conversation_title(conversation_id, title)


# ---------------------------------------------------------------------------
# Legacy helpers (kept for backward compatibility – they proxy to the current
# conversation via st.session_state)
# ---------------------------------------------------------------------------

def save_message(role: str, content: str):
    import streamlit as st
    conversation_id = st.session_state.get("conversation_id")
    if conversation_id is None:
        raise RuntimeError("No active conversation – set st.session_state['conversation_id'] first.")
    add_message(conversation_id, role, content)


def load_history(limit: int = 50) -> List[Tuple[str, str]]:
    import streamlit as st
    conversation_id = st.session_state.get("conversation_id")
    if conversation_id is None:
        return []
    return load_conversation_messages(conversation_id, limit)


def clear_history() -> None:
    import streamlit as st
    conversation_id = st.session_state.get("conversation_id")
    if conversation_id is not None:
        clear_conversation(conversation_id)
