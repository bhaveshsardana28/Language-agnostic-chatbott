"""Per-session document store with multilingual embeddings.

Design decisions (documented, not vibes):
  - Model: paraphrase-multilingual-MiniLM-L12-v2 — CPU-friendly, 50+ languages,
    made for sentence-level cross-lingual similarity (exactly our use case:
    English docs, hi/pa/es/fr/de/it queries).
  - SQLite persists document text, metadata and float32 vectors. A small
    in-memory NumPy matrix is rebuilt lazily per active session, so restart
    recovery does not require a vector-DB service.
  - Session scope = conversation_id; deleting the conversation deletes the
    persisted vectors (documents never outlive the chat).
  - If the embedding model is unavailable (offline first run), degrade to
    TF-overlap retrieval (backend/documents.py) and say so via `degraded`.
"""

from __future__ import annotations

from functools import lru_cache
import logging
import hashlib
import json
import threading

import numpy as np

from backend import documents, settings, storage

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 4
OVERVIEW_TOP_K = 8
GROUND_THRESHOLD = 0.45  # cosine gate: live-measured good cross-lingual hit = 0.709,
# topic-adjacent-but-unanswerable hit = 0.397
KEYWORD_GROUND_THRESHOLD = 0.05

_model = None
_model_lock = threading.Lock()


def _load_store(session_id: str, owner_id: str | None = None) -> dict | None:
    session = storage.rag_session(session_id)
    if not session or (owner_id is not None and session["owner_id"] != owner_id):
        return None
    return _read_index(storage.db_path(), session_id, session["owner_id"], session["updated_at"],
                       session["mode"], session["embedding_model"], session["embedding_dim"])


@lru_cache(maxsize=16)
def _read_index(db_path, session_id, owner_id, revision, mode, model, dimension):
    """Cache immutable snapshots by database, owner and committed revision."""
    rows = storage.rag_chunks(session_id, owner_id)
    if not rows:
        return None
    texts = [row["text"] for row in rows]
    metas = []
    for row in rows:
        meta = {"document": row["filename"], "chunk": row["chunk_index"]}
        if row.get("document_id") is not None:
            meta["document_id"] = row["document_id"]
        if row["page"] is not None:
            meta["page"] = row["page"]
        metas.append(meta)

    matrix = None
    if mode == "embedding":
        vectors = []
        if model != EMBEDDING_MODEL:
            raise RuntimeError("persisted embedding model does not match configured model")
        for row in rows:
            if not row["embedding"] or row["embedding_dim"] != dimension:
                raise RuntimeError(f"persisted embedding is invalid for session {session_id}")
            vector = np.frombuffer(row["embedding"], dtype=np.float32)
            if len(vector) != dimension or not np.isfinite(vector).all():
                raise RuntimeError(f"persisted embedding has invalid shape for session {session_id}")
            vectors.append(vector)
        matrix = np.vstack(vectors).astype(np.float32, copy=False)
    store = {"texts": texts, "metas": metas, "matrix": matrix}
    return store


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


def has_session(session_id: str, owner_id: str | None = None) -> bool:
    return bool(storage.list_documents(session_id, owner_id))


def add_document(session_id: str, file_bytes: bytes, filename: str, owner_id: str = "local",
                 require_conversation: bool = False) -> dict:
    """Extract -> chunk -> embed -> store under the session. Returns an
    ingestion report (never silently skips a failed document — caller 400s)."""
    session = storage.rag_session(session_id)
    if session and session["owner_id"] != owner_id:
        raise PermissionError("document session belongs to another workspace")
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    duplicate = storage.document_by_hash(session_id, content_hash, owner_id=owner_id)
    if duplicate:
        try:
            report = json.loads(duplicate.get("extraction_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            report = {}
        report["document_id"] = duplicate["id"]
        existing_docs = {
            item["document_id"]: item for item in storage.list_documents(session_id)
        }
        existing = existing_docs.get(duplicate["id"], {})
        return _ingestion_response(
            report, duplicate["id"], duplicate=True, document=duplicate.get("filename"),
            chars=duplicate.get("char_count", report.get("char_count", 0)),
            chunks=existing.get("chunks"), embeddings=(session or {}).get("mode") == "embedding",
        )

    report = documents.extract_document(file_bytes, filename)
    text = report.full_text
    if report.status != "completed" or not text.strip():
        detail = "no extractable text"
        if "pdf_ocr_unavailable" in report.warnings:
            detail = "no extractable text; local PDF OCR is unavailable"
        elif "ocr_language_unavailable" in report.warnings:
            detail = "no extractable text; the configured OCR language pack is unavailable"
        elif "ocr_disabled" in report.warnings:
            detail = "no extractable text; OCR is disabled"
        raise documents.EmptyExtraction(f"{detail} in {filename}")
    chunk_records = documents.chunk_report(report)
    chunks = [chunk for chunk, _ in chunk_records]
    if not chunks:
        raise documents.EmptyExtraction(f"no extractable text in {filename}")

    # A keyword session stays keyword-only after restart. Conversely, an
    # embedding session must keep its model/dimension contract stable.
    if session and session["mode"] == "keyword":
        use_embeddings = False
    else:
        use_embeddings = embeddings_available()
    if session and session["mode"] == "embedding" and not use_embeddings:
        raise RuntimeError("embedding service is unavailable for this persisted document session")

    embedding_dim = None
    if use_embeddings:
        vecs = np.asarray(_get_model().encode(chunks, normalize_embeddings=True,
                                              show_progress_bar=False), dtype=np.float32)
        if vecs.ndim != 2 or len(vecs) != len(chunks) or not np.isfinite(vecs).all():
            raise RuntimeError("invalid embedding matrix")
        embedding_dim = int(vecs.shape[1])
    chunk_rows = []
    for index, (chunk, page) in enumerate(chunk_records):
        row = {"text": chunk, "page": page if page is not None else documents.page_number(chunk)}
        if use_embeddings:
            row["embedding"] = np.asarray(vecs[index], dtype=np.float32).tobytes()
            row["embedding_dim"] = int(vecs.shape[1])
        else:
            row["embedding"] = None
            row["embedding_dim"] = None

        chunk_rows.append(row)

    # Commit text, metadata and vectors together only after extraction and
    # embedding have both succeeded. SQLite's transaction means a failed
    # upload cannot poison either the durable or hot session.
    saved = storage.save_document(
        session_id, filename, chunk_rows, mode="embedding" if use_embeddings else "keyword",
        embedding_model=EMBEDDING_MODEL if use_embeddings else None,
        embedding_dim=embedding_dim, owner_id=owner_id, content_hash=content_hash,
        extraction=report.to_dict(), source_bytes=file_bytes, require_conversation=require_conversation,
    )
    if saved["duplicate"]:
        # A concurrent upload indexed these bytes first. Return its canonical filename/report.
        canonical = storage.document_report(session_id, saved["document_id"], owner_id)
        if canonical:
            report_data = canonical["report"]
            return _ingestion_response(report_data, saved["document_id"], duplicate=True,
                                       chunks=len(chunks), embeddings=use_embeddings)
    report.document_id = saved["document_id"]
    return _ingestion_response(report.to_dict(), saved["document_id"],
                               duplicate=saved.get("duplicate", False),
                               document=filename, chars=report.to_dict()["char_count"], chunks=len(chunks),
                               embeddings=use_embeddings)


def _ingestion_response(report: dict, document_id: int, *, duplicate: bool = False,
                        document: str | None = None, chars: int | None = None,
                        chunks: int | None = None, embeddings: bool | None = None) -> dict:
    """Return a bounded upload response; full text is available via the report endpoint."""
    pages = report.get("pages", [])
    response = {
        "document": document or report.get("filename"),
        "document_id": document_id,
        "duplicate": duplicate,
        "status": report.get("status", "completed"),
        "chars": chars if chars is not None else report.get("char_count", 0),
        "chunks": chunks,
        "page_count": report.get("page_count", len(pages)),
        "detected_language": report.get("detected_language"),
        "extraction_method": report.get("extraction_method"),
        "warnings": report.get("warnings", []),
        "pages": [
            {"page_number": page.get("page_number"),
             "method": page.get("extraction_method"),
             "warnings": page.get("warnings", []),
             "quality": page.get("quality", {})}
            for page in pages
        ],
    }
    if chunks is not None:
        response.update({"chunk_size": 1200, "overlap": 150, "embeddings": embeddings})
    return response


def query(session_id: str, query_text: str, top_k: int = TOP_K, overview: bool = False,
          owner_id: str | None = None) -> dict:
    store = _load_store(session_id, owner_id)
    if not store or not store["texts"]:
        return {"hits": [], "degraded": False}

    if overview:
        if not store["texts"]: return {"hits": [], "degraded": store["matrix"] is None}
        count = min(top_k, len(store["texts"]))
        if count == 1: idxs = [0]
        else: idxs = sorted({round(i * (len(store["texts"]) - 1) / (count - 1)) for i in range(count)})
        return {"hits": [{"text": store["texts"][i], **store["metas"][i]} for i in idxs],
                "degraded": store["matrix"] is None}

    if store["matrix"] is not None:
        try:
            q = _get_model().encode([query_text], normalize_embeddings=True,
                                    show_progress_bar=False)
            q = np.asarray(q, dtype=np.float32)
            if q.ndim != 2 or q.shape[1] != store["matrix"].shape[1]:
                raise RuntimeError("query embedding dimension does not match persisted index")
            sims = (store["matrix"] @ q[0])
            idxs = np.argsort(-sims)[:top_k]
            hits = [{"text": store["texts"][i], "score": float(sims[i]),
                     **store["metas"][i]} for i in idxs]
            return {"hits": hits, "degraded": False}
        except Exception as exc:
            logger.warning("embedding query unavailable; using keyword fallback: %s", exc)
            # A persisted vector index remains usable for exact lexical terms
            # during a temporary model outage instead of returning a 500.
            ranked = documents.score_chunks(query_text, store["texts"], top_k=top_k)
            hits = [{"text": c, "score": float(s), **store["metas"][i]} for s, i, c in ranked]
            return {"hits": hits, "degraded": True}

    # degraded: TF-overlap (no embeddings)
    ranked = documents.score_chunks(query_text, store["texts"], top_k=top_k)
    hits = [{"text": c, "score": float(s), **store["metas"][i]} for s, i, c in ranked]
    return {"hits": hits, "degraded": True}


def grounded(hits: list[dict], degraded: bool = False, query_text: str = "") -> bool:
    threshold = KEYWORD_GROUND_THRESHOLD if degraded else GROUND_THRESHOLD
    if not hits:
        return False
    if any(hit.get("score", 0.0) >= threshold for hit in hits):
        return True
    if degraded or not query_text:
        return False

    # Short factual questions often use wording that is not close enough to
    # the document sentence for a 0.45 cosine gate, e.g. "what year was it
    # created?" versus "created in 2024". Search every retrieved candidate,
    # not just the top cosine hit, and require a meaningful lexical anchor.
    for hit in hits:
        score = hit.get("score", 0.0)
        matches = documents.matching_keywords(query_text, hit.get("text", ""))
        if score >= 0.12 and any(len(term) >= 5 for term in matches):
            return True
    return False


def list_documents(session_id: str, owner_id: str | None = None) -> list[dict]:
    """Unique documents + chunk counts for this session (UI document panel)."""
    return storage.list_documents(session_id, owner_id)


def delete_session(session_id: str, owner_id: str | None = None) -> bool:
    return storage.delete_rag_session(session_id, owner_id)


def delete_document(session_id: str, document_id: int, owner_id: str | None = None) -> bool:
    return storage.delete_document(session_id, document_id, owner_id)
