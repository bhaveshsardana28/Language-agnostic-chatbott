"""Durable SQLite storage for conversations, extracted documents and chunks.

SQLite remains the least disruptive vector store for this local application.
Document metadata and the structured extraction report are persisted beside the
chunk rows, while the original upload is stored under a generated SHA-256 name
with restrictive permissions.  No user-supplied path is ever opened.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from typing import Iterable

from backend import settings

SCHEMA_VERSION = 2


def db_path() -> str:
    return settings.GAIA_DB_PATH


@contextmanager
def connect():
    path = db_path()
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass
    connection = sqlite3.connect(path, timeout=settings.SQLITE_TIMEOUT)
    connection.row_factory = sqlite3.Row
    for database_file in (path, f"{path}-wal", f"{path}-shm"):
        try:
            os.chmod(database_file, 0o600)
        except OSError:
            pass
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {int(settings.SQLITE_TIMEOUT * 1000)}")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_column(db: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL DEFAULT 'local',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS messages_conversation_idx ON messages(conversation_id, id);
        CREATE TABLE IF NOT EXISTS rag_sessions (
            session_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL DEFAULT 'local',
            mode TEXT NOT NULL CHECK (mode IN ('embedding', 'keyword')),
            embedding_model TEXT,
            embedding_dim INTEGER,
            chunker_version TEXT NOT NULL DEFAULT 'chars-1200-overlap-150-v2',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_hash TEXT,
            status TEXT NOT NULL DEFAULT 'ready',
            extraction_method TEXT,
            detected_language TEXT,
            page_count INTEGER,
            char_count INTEGER NOT NULL DEFAULT 0,
            warnings TEXT NOT NULL DEFAULT '[]',
            extraction_json TEXT,
            source_path TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES rag_sessions(session_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS documents_session_idx ON documents(session_id);
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            page INTEGER,
            embedding BLOB,
            embedding_dim INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id, chunk_index);
        PRAGMA user_version = 2;
        """)
        # Additive migration for databases made by the earlier V2 RAG layer.
        _ensure_column(db, "documents", "content_hash", "TEXT")
        _ensure_column(db, "documents", "status", "TEXT NOT NULL DEFAULT 'ready'")
        _ensure_column(db, "documents", "extraction_method", "TEXT")
        _ensure_column(db, "documents", "detected_language", "TEXT")
        _ensure_column(db, "documents", "page_count", "INTEGER")
        _ensure_column(db, "documents", "char_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(db, "documents", "warnings", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "documents", "extraction_json", "TEXT")
        _ensure_column(db, "documents", "source_path", "TEXT")
        _ensure_column(db, "conversations", "owner_id", "TEXT NOT NULL DEFAULT 'local'")
        _ensure_column(db, "conversations", "created_at", "REAL NOT NULL DEFAULT 0")
        _ensure_column(db, "conversations", "updated_at", "REAL NOT NULL DEFAULT 0")
        _ensure_column(db, "rag_sessions", "owner_id", "TEXT NOT NULL DEFAULT 'local'")
        _ensure_column(db, "rag_sessions", "mode", "TEXT NOT NULL DEFAULT 'keyword'")
        _ensure_column(db, "rag_sessions", "embedding_model", "TEXT")
        _ensure_column(db, "rag_sessions", "embedding_dim", "INTEGER")
        _ensure_column(db, "rag_sessions", "chunker_version", "TEXT NOT NULL DEFAULT 'chars-1200-overlap-150-v2'")
        _ensure_column(db, "rag_sessions", "created_at", "REAL NOT NULL DEFAULT 0")
        _ensure_column(db, "rag_sessions", "updated_at", "REAL NOT NULL DEFAULT 0")
        _ensure_column(db, "chunks", "page", "INTEGER")
        _ensure_column(db, "chunks", "embedding", "BLOB")
        _ensure_column(db, "chunks", "embedding_dim", "INTEGER")
        db.execute("CREATE INDEX IF NOT EXISTS documents_hash_idx ON documents(session_id, content_hash)")
        try:
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS documents_session_hash_unique ON documents(session_id, content_hash) WHERE content_hash IS NOT NULL")
        except sqlite3.IntegrityError:
            # A pre-migration database may already contain duplicate uploads;
            # new writes still perform an atomic lookup and old rows remain readable.
            pass


def _now() -> float:
    return time.time()


def create_conversation(owner_id: str = "local") -> str:
    import uuid

    conversation_id = uuid.uuid4().hex[:12]
    now = _now()
    with connect() as db:
        db.execute("INSERT INTO conversations(id, owner_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, owner_id, now, now))
    return conversation_id


def ensure_conversation(conversation_id: str, owner_id: str = "local") -> None:
    now = _now()
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO conversations(id, owner_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, owner_id, now, now))


def conversation_owner(conversation_id: str) -> str | None:
    with connect() as db:
        row = db.execute("SELECT owner_id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    return row["owner_id"] if row else None


def conversation_exists(conversation_id: str, owner_id: str | None = None) -> bool:
    with connect() as db:
        if owner_id is None:
            row = db.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        else:
            row = db.execute("SELECT 1 FROM conversations WHERE id = ? AND owner_id = ?",
                             (conversation_id, owner_id)).fetchone()
    return row is not None


def claim_legacy_workspace(conversation_id: str, owner_id: str) -> bool:
    """One-time compatibility path for conversations made before workspace cookies."""
    if not owner_id or owner_id == "local":
        return False
    with connect() as db:
        row = db.execute("SELECT owner_id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not row or row["owner_id"] != "local":
            return False
        updated = db.execute("UPDATE conversations SET owner_id = ? WHERE id = ? AND owner_id = 'local'",
                             (owner_id, conversation_id))
        if updated.rowcount != 1:
            return False
        db.execute("UPDATE rag_sessions SET owner_id = ? WHERE session_id = ? AND owner_id = 'local'",
                   (owner_id, conversation_id))
    return True


def append_message(conversation_id: str, role: str, content: str, limit: int) -> None:
    now = _now()
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO conversations(id, owner_id, created_at, updated_at) VALUES (?, 'local', ?, ?)",
                   (conversation_id, now, now))
        db.execute("INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, role, content, now))
        db.execute("""DELETE FROM messages WHERE conversation_id = ? AND id NOT IN
                    (SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?)""",
                   (conversation_id, conversation_id, limit))
        db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))


def history(conversation_id: str) -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
                          (conversation_id,)).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def delete_conversation(conversation_id: str) -> bool:
    rag_deleted = delete_rag_session(conversation_id)
    with connect() as db:
        result = db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return result.rowcount > 0 or rag_deleted


def _persist_source(source_bytes: bytes, content_hash: str) -> tuple[str, bool]:
    root = os.path.abspath(settings.DOCUMENT_STORAGE_DIR)
    os.makedirs(root, mode=0o700, exist_ok=True)
    path = os.path.join(root, f"{content_hash}.bin")
    if os.path.exists(path):
        return path, False
    fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=root)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(source_bytes)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        return path, True
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def save_document(session_id: str, filename: str, chunks: Iterable[dict], *, mode: str,
                  embedding_model: str | None, embedding_dim: int | None,
                  owner_id: str = "local", content_hash: str | None = None,
                  extraction: dict | None = None, source_bytes: bytes | None = None) -> dict:
    now = _now()
    chunks = list(chunks)
    extraction = extraction or {}
    if source_bytes is not None:
        content_hash = content_hash or hashlib.sha256(source_bytes).hexdigest()
    source_path = None
    created_source = False
    try:
        if source_bytes is not None and content_hash:
            source_path, created_source = _persist_source(source_bytes, content_hash)
        with connect() as db:
            existing = db.execute("SELECT owner_id, mode, embedding_model, embedding_dim FROM rag_sessions WHERE session_id = ?",
                                  (session_id,)).fetchone()
            if existing is None:
                db.execute("""INSERT INTO rag_sessions(session_id, owner_id, mode, embedding_model,
                            embedding_dim, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (session_id, owner_id, mode, embedding_model, embedding_dim, now, now))
            else:
                if existing["owner_id"] != owner_id:
                    raise PermissionError("document session belongs to another workspace")
                if existing["mode"] != mode:
                    raise RuntimeError("cannot mix embedding and keyword indexes in one document session")
                if embedding_dim and existing["embedding_dim"] and embedding_dim != existing["embedding_dim"]:
                    raise RuntimeError("embedding dimension changed within this document session")
                db.execute("UPDATE rag_sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            if content_hash:
                duplicate = db.execute(
                    "SELECT id FROM documents WHERE session_id = ? AND content_hash = ? ORDER BY id LIMIT 1",
                    (session_id, content_hash),
                ).fetchone()
                if duplicate:
                    return {"document_id": duplicate["id"], "duplicate": True}
            try:
                document = db.execute(
                    "INSERT INTO documents(session_id, filename, content_hash, created_at) VALUES (?, ?, ?, ?)",
                    (session_id, filename, content_hash, now),
                )
            except sqlite3.IntegrityError:
                if not content_hash:
                    raise
                duplicate = db.execute(
                    "SELECT id FROM documents WHERE session_id = ? AND content_hash = ? ORDER BY id LIMIT 1",
                    (session_id, content_hash),
                ).fetchone()
                if duplicate:
                    return {"document_id": duplicate["id"], "duplicate": True}
                raise
            document_id = document.lastrowid
            db.execute("""UPDATE documents SET content_hash = ?, status = ?, extraction_method = ?,
                        detected_language = ?, page_count = ?, char_count = ?, warnings = ?,
                        extraction_json = ?, source_path = ? WHERE id = ?""",
                       (content_hash, extraction.get("status", "ready"), extraction.get("extraction_method"),
                        extraction.get("detected_language"), extraction.get("page_count"),
                        extraction.get("char_count", 0), json.dumps(extraction.get("warnings", []), ensure_ascii=False),
                        json.dumps(extraction, ensure_ascii=False), source_path, document_id))
            for index, chunk in enumerate(chunks):
                db.execute("""INSERT INTO chunks(document_id, chunk_index, text, page, embedding, embedding_dim)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                           (document_id, index, chunk["text"], chunk.get("page"), chunk.get("embedding"),
                            chunk.get("embedding_dim")))
        return {"document_id": document_id, "duplicate": False}
    except Exception:
        if created_source and source_path:
            try:
                os.unlink(source_path)
            except OSError:
                pass
        raise


def rag_session(session_id: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT * FROM rag_sessions WHERE session_id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def rag_chunks(session_id: str) -> list[dict]:
    with connect() as db:
        rows = db.execute("""SELECT c.chunk_index, c.text, c.page, c.embedding, c.embedding_dim,
                                  d.id AS document_id, d.filename
                           FROM chunks c JOIN documents d ON d.id = c.document_id
                           WHERE d.session_id = ? ORDER BY c.id""", (session_id,)).fetchall()
    return [dict(row) for row in rows]


def list_documents(session_id: str) -> list[dict]:
    with connect() as db:
        rows = db.execute("""SELECT d.id AS document_id, d.filename AS document, COUNT(*) AS chunks,
                                  d.status, d.extraction_method, d.detected_language,
                                  d.page_count, d.char_count, d.warnings
                           FROM documents d JOIN chunks c ON c.document_id = d.id
                           WHERE d.session_id = ? GROUP BY d.id ORDER BY d.id""",
                          (session_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["warnings"] = json.loads(item.get("warnings") or "[]")
        except (TypeError, json.JSONDecodeError):
            item["warnings"] = []
        result.append(item)
    return result


def document_by_hash(session_id: str, content_hash: str, owner_id: str | None = None) -> dict | None:
    with connect() as db:
        row = db.execute("""SELECT d.*, r.owner_id FROM documents d
                           JOIN rag_sessions r ON r.session_id = d.session_id
                           WHERE d.session_id = ? AND d.content_hash = ? ORDER BY d.id LIMIT 1""",
                         (session_id, content_hash)).fetchone()
    if not row or (owner_id is not None and row["owner_id"] != owner_id):
        return None
    return dict(row)


def document_report(session_id: str, document_id: int, owner_id: str | None = None) -> dict | None:
    with connect() as db:
        row = db.execute("""SELECT d.*, r.owner_id FROM documents d
                           JOIN rag_sessions r ON r.session_id = d.session_id
                           WHERE d.id = ? AND d.session_id = ?""",
                         (document_id, session_id)).fetchone()
    if not row or (owner_id is not None and row["owner_id"] != owner_id):
        return None
    result = dict(row)
    raw = result.pop("extraction_json", None)
    result.pop("source_path", None)
    result.pop("owner_id", None)
    try:
        report = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        report = {}
    if not report.get("document_id"):
        report["document_id"] = document_id
    report.setdefault("filename", result.get("filename"))
    report.setdefault("status", result.get("status", "ready"))
    result["report"] = report
    try:
        result["warnings"] = json.loads(result.get("warnings") or "[]")
    except (TypeError, json.JSONDecodeError):
        result["warnings"] = []
    return result


def delete_rag_session(session_id: str) -> bool:
    with connect() as db:
        paths = [row[0] for row in db.execute(
            "SELECT source_path FROM documents WHERE session_id = ? AND source_path IS NOT NULL",
            (session_id,),
        ).fetchall()]
        result = db.execute("DELETE FROM rag_sessions WHERE session_id = ?", (session_id,))
        remaining = {
            row[0] for row in db.execute(
                "SELECT source_path FROM documents WHERE source_path IS NOT NULL"
            ).fetchall()
        }
    root = os.path.abspath(settings.DOCUMENT_STORAGE_DIR)
    for path in paths:
        try:
            if path and path not in remaining and os.path.commonpath([root, os.path.abspath(path)]) == root:
                os.unlink(path)
        except (OSError, ValueError):
            pass
    return result.rowcount > 0


def reset_for_tests() -> None:
    with connect() as db:
        db.execute("DELETE FROM conversations")
        db.execute("DELETE FROM rag_sessions")


init_db()
