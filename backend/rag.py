"""Per-session document store with multilingual embeddings.

Design decisions (documented, not vibes):
  - Model: paraphrase-multilingual-MiniLM-L12-v2 — CPU-friendly, 50+ languages,
    made for sentence-level cross-lingual similarity (exactly our use case:
    English docs, hi/pa/es/fr/de/it queries).
  - No vector-DB server: sessions hold a handful of chunks; brute-force cosine
    over an in-memory numpy matrix is exact ANN and gives session isolation
    for free. Upgrade path if a corpus outgrows RAM: Qdrant local.
  - Session scope = conversation_id; deleting the conversation deletes the
    vectors (memory of documents never outlives the chat).
  - If the embedding model is unavailable (offline first run), degrade to
    TF-overlap retrieval (backend/documents.py) and say so via `degraded`.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from backend import documents

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 4
GROUND_THRESHOLD = 0.45  # cosine gate: live-measured good cross-lingual hit = 0.709,
                         # topic-adjacent-but-unanswerable hit = 0.397

_model = None
_model_lock = threading.Lock()
_sessions: dict[str, dict] = {}  # session_id -> {texts, metas, matrix}


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embeddings_available() -> bool:
    try:
        _get_model()
        return True
    except Exception as exc:
        logger.warning("embedding model unavailable: %s", exc)
        return False


def has_session(session_id: str) -> bool:
    return bool(_sessions.get(session_id, {}).get("texts"))


def add_document(session_id: str, file_bytes: bytes, filename: str) -> dict:
    """Extract -> chunk -> embed -> store under the session. Returns an
    ingestion report (never silently skips a failed document — caller 400s)."""
    text = documents.extract_text(file_bytes, filename)
    if not text or not text.strip():
        raise ValueError(f"no extractable text in {filename}")
    chunks = documents.chunk_text(text)
    metas = [{"document": filename, "chunk": i} for i in range(len(chunks))]

    store = _sessions.setdefault(session_id, {"texts": [], "metas": [], "matrix": None})
    store["texts"].extend(chunks)
    store["metas"].extend(metas)

    if embeddings_available():
        vecs = _get_model().encode(chunks, normalize_embeddings=True,
                                   show_progress_bar=False)
        vecs = np.asarray(vecs, dtype=np.float32)
        store["matrix"] = vecs if store["matrix"] is None else np.vstack([store["matrix"], vecs])
    return {"document": filename, "chars": len(text), "chunks": len(chunks),
            "chunk_size": 1200, "overlap": 150,
            "embeddings": store["matrix"] is not None}


def query(session_id: str, query_text: str, top_k: int = TOP_K) -> dict:
    store = _sessions.get(session_id)
    if not store or not store["texts"]:
        return {"hits": [], "degraded": False}

    if store["matrix"] is not None:
        q = _get_model().encode([query_text], normalize_embeddings=True,
                                show_progress_bar=False)
        sims = (store["matrix"] @ np.asarray(q, dtype=np.float32)[0])
        idxs = np.argsort(-sims)[:top_k]
        hits = [{"text": store["texts"][i], "score": float(sims[i]),
                 **store["metas"][i]} for i in idxs]
        return {"hits": hits, "degraded": False}

    # degraded: TF-overlap (no embeddings)
    ranked = documents.score_chunks(query_text, store["texts"], top_k=top_k)
    hits = [{"text": c, "score": float(s), **store["metas"][i]} for s, i, c in ranked]
    return {"hits": hits, "degraded": True}


def grounded(hits: list[dict]) -> bool:
    return bool(hits) and hits[0]["score"] >= GROUND_THRESHOLD


def list_documents(session_id: str) -> list[dict]:
    """Unique documents + chunk counts for this session (UI document panel)."""
    store = _sessions.get(session_id)
    if not store:
        return []
    counts: dict[str, int] = {}
    for m in store["metas"]:
        counts[m["document"]] = counts.get(m["document"], 0) + 1
    return [{"document": d, "chunks": c} for d, c in counts.items()]


def delete_session(session_id: str) -> bool:
    return _sessions.pop(session_id, None) is not None
