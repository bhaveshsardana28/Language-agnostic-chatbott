"""
Document intelligence — extract text from PDF/DOCX/TXT, chunk it, and
retrieve the most relevant chunks for a query.

ponytail: in-memory TF-IDF-ish keyword overlap scoring instead of a vector
store. Upgrade path: swap `score_chunks` for embeddings + FAISS/Pinecone.
"""

from __future__ import annotations

import io
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a PDF/DOCX/TXT/MD file's bytes."""
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            return _extract_pdf(file_bytes)
        if name.endswith(".docx"):
            return _extract_docx(file_bytes)
        if name.endswith((".txt", ".md", ".csv", ".json", ".py", ".js")):
            return file_bytes.decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("extract_text failed for %s: %s", filename, exc)
        raise RuntimeError(f"Could not read {filename}: {exc}")
    raise RuntimeError(f"Unsupported file type: {filename}")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    out = []
    for i, page in enumerate(reader.pages):
        try:
            out.append(page.extract_text() or "")
        except Exception as exc:
            logger.debug("pdf page %d extract failed: %s", i, exc)
    return "\n".join(out).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text).strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """Split text into overlapping chunks of ~chunk_size chars on word boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # walk back to a whitespace to avoid cutting words
            for offset in range(end, max(start, end - 50), -1):
                if text[offset].isspace():
                    end = offset
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0
    return [c for c in chunks if c]


def _tokens(text: str) -> set:
    return set(t.lower() for t in _WORD_RE.findall(text))


def score_chunks(query: str, chunks: List[str], top_k: int = 5) -> List[Tuple[float, int, str]]:
    """Return top_k chunks ranked by simple keyword overlap with the query.

    Returns list of (score, index, chunk_text) sorted desc.
    ponytail: term frequency overlap, no embeddings. Replace with embeddings
    when semantic match quality matters more than keyword match.
    """
    if not chunks:
        return []
    q_tokens = _tokens(query)
    if not q_tokens:
        return [(0.0, i, c) for i, c in enumerate(chunks[:top_k])]

    scored = []
    for i, c in enumerate(chunks):
        ct = _tokens(c)
        if not ct:
            scored.append((0.0, i, c))
            continue
        overlap = len(q_tokens & ct)
        # Jaccard-like: overlap / union
        union = len(q_tokens | ct)
        score = overlap / union if union else 0.0
        # small length normalization boost
        scored.append((score, i, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def build_context(query: str, chunks: List[str], top_k: int = 5) -> Tuple[str, List[int]]:
    """Return (context_text, list_of_chunk_indices_used)."""
    top = score_chunks(query, chunks, top_k=top_k)
    if not top:
        return "", []
    parts = []
    idxs = []
    for rank, (score, idx, c) in enumerate(top, 1):
        parts.append(f"[{rank}] {c}")
        idxs.append(idx)
    return "\n\n".join(parts), idxs
