"""Durability and workspace-boundary regressions for the V2 storage layer."""

from __future__ import annotations

import os
import sqlite3
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import memory, rag, settings, storage  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


class TinyEmbed:
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        rows = []
        for text in texts:
            vector = np.zeros(8, dtype=np.float32)
            for token in text.lower().split():
                vector[hash(token) % len(vector)] += 1
            norm = np.linalg.norm(vector)
            rows.append(vector / norm if norm else vector)
        return np.asarray(rows, dtype=np.float32)


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GAIA_DB_PATH", str(tmp_path / "recovery.db"))
    storage.init_db()
    memory._conversations.clear()
    rag._sessions.clear()
    old_model = rag._model
    rag._model = TinyEmbed()
    yield
    rag._model = old_model
    memory._conversations.clear()
    rag._sessions.clear()


def test_conversation_and_document_recover_after_cache_reset(isolated_store):
    cid = memory.create("workspace-a")
    memory.append(cid, "user", "hello")
    memory.append(cid, "assistant", "hi")
    report = rag.add_document(cid, b"Aurora headquarters are in Jaipur.", "aurora.txt",
                              owner_id="workspace-a")
    assert report["embeddings"] is True

    # A process restart discards both hot caches but not SQLite state.
    memory._conversations.clear()
    rag._sessions.clear()
    assert memory.history(cid) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert rag.has_session(cid, "workspace-a")
    listed = rag.list_documents(cid, "workspace-a")
    assert listed and listed[0]["document"] == "aurora.txt"
    assert listed[0]["chunks"] == 1 and listed[0]["status"] == "completed"
    assert rag.query(cid, "Where is Aurora headquartered?", top_k=1)["hits"]


def test_document_session_has_workspace_boundary(isolated_store):
    cid = memory.create("workspace-a")
    rag.add_document(cid, b"Private workspace facts.", "private.txt", owner_id="workspace-a")

    assert not rag.has_session(cid, "workspace-b")
    assert rag.list_documents(cid, "workspace-b") == []
    with pytest.raises(PermissionError):
        rag.add_document(cid, b"Should not be accepted.", "attack.txt", owner_id="workspace-b")


def test_api_rejects_cross_workspace_document_access():
    first = TestClient(app, raise_server_exceptions=False)
    second = TestClient(app, raise_server_exceptions=False)
    cid = first.post("/api/v1/conversations").json()["conversation_id"]

    denied_upload = second.post("/api/v1/documents", data={"conversation_id": cid},
                                files={"file": ("private.txt", b"private facts")})
    assert denied_upload.status_code == 403
    assert second.get(f"/api/v1/documents/{cid}").json()["documents"] == []
    assert second.delete(f"/api/v1/chat/{cid}").json()["deleted"] is False


def test_additive_migration_handles_legacy_table_shapes(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE conversations (id TEXT PRIMARY KEY, created_at REAL, updated_at REAL);
        CREATE TABLE rag_sessions (session_id TEXT PRIMARY KEY, mode TEXT, created_at REAL, updated_at REAL);
        CREATE TABLE documents (id INTEGER PRIMARY KEY, session_id TEXT, filename TEXT, created_at REAL);
        CREATE TABLE chunks (id INTEGER PRIMARY KEY, document_id INTEGER, chunk_index INTEGER, text TEXT);
    """)
    db.commit()
    db.close()
    monkeypatch.setattr(settings, "GAIA_DB_PATH", str(path))
    storage.init_db()
    cid = storage.create_conversation("workspace-a")
    assert storage.conversation_owner(cid) == "workspace-a"


def test_preview_origin_can_use_workspace_cookie_credentials():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.options(
        "/api/v1/conversations",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
