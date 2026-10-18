"""Deterministic document QA regressions for the production retrieval path.

Run: python -m pytest -q tests/test_rag_qa.py
Embeddings and generation are replaced with deterministic local doubles; upload,
routing, retrieval, prompt assembly, isolation and source metadata remain real.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys

import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import llm, memory, rag, router, settings  # noqa: E402
from backend.main import app  # noqa: E402
from backend.main import _format_sources  # noqa: E402
from backend import documents  # noqa: E402


client = TestClient(app, raise_server_exceptions=False)


class StableEmbed:
    """Deterministic lexical vectorizer with enough dimensions to avoid collisions."""

    aliases = {"कर्मचारी": "employees", "कितने": "how", "मुख्यालय": "headquarters",
               "कहाँ": "where", "कोड": "code", "हैं": "are"}

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        rows = []
        for text in texts:
            vector = np.zeros(8192, dtype=np.float32)
            for raw in text.lower().split():
                token = self.aliases.get(raw.strip("?।,."), raw.strip("?।,."))
                index = int(hashlib.sha1(token.encode()).hexdigest(), 16) % len(vector)
                vector[index] += 1
            norm = np.linalg.norm(vector)
            rows.append(vector / norm if norm else vector)
        return np.asarray(rows)


def pdf_fixture(pages: list[str]) -> bytes:
    """Build a tiny text PDF without adding a test-only PDF dependency."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + i * 3} 0 R".encode() for i in range(len(pages)))
        + f"] /Count {len(pages)} >>".encode(),
    ]
    for i, text in enumerate(pages):
        page_id, content_id, font_id = 3 + i * 3, 4 + i * 3, 5 + i * 3
        stream = f"BT /F1 12 Tf 72 700 Td ({text}) Tj ET".encode()
        objects.extend([
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ])
    # Each page owns a content stream and a font object, keeping page extraction
    # deterministic without a third-party PDF generator.
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    body.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    body.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(body)


def parse_sse(response_text):
    return [json.loads(block[5:].strip()) for block in response_text.split("\n\n") if block.startswith("data:")]


def post(message, conversation_id):
    response = client.post("/api/v1/chat", json={"message": message, "conversation_id": conversation_id})
    assert response.status_code == 200, response.text
    return parse_sse(response.text)


def upload(conversation_id, filename="aurora.txt", content=None):
    content = content or (
        b"Project Aurora has 42 employees. Its headquarters are in Jaipur. "
        b"The internal project code is AURORA-731."
    )
    response = client.post("/api/v1/documents", data={"conversation_id": conversation_id},
                           files={"file": (filename, content)})
    assert response.status_code == 200, response.text
    return response.json()


def test_document_qa_broad_specific_absent_and_prompt_context():
    real_model, real_threshold, real_stream, real_key = rag._model, rag.GROUND_THRESHOLD, llm.stream_chat, settings.LLM_API_KEY
    captured = []

    def fake_stream(messages, model=None):
        captured.append(messages)
        context = "\n".join(item["content"] for item in messages)
        question = messages[-1]["content"].split("\n\n--- Document excerpts ---", 1)[0]
        if "internal project code" in question:
            yield "The internal project code is AURORA-731."
        elif "42 employees" in context:
            yield "Project Aurora has 42 employees and is headquartered in Jaipur."
        else:
            yield "I couldn't find that in the uploaded documents."

    rag._model = StableEmbed()
    rag.GROUND_THRESHOLD = 0.45
    llm.stream_chat = fake_stream
    settings.LLM_API_KEY = "test-key"
    try:
        cid = client.post("/api/v1/conversations").json()["conversation_id"]
        report = upload(cid)
        assert report["embeddings"] is True and report["chunks"] == 1
        assert router.decide("What does the uploaded document say about the 2026 exam?",
                             {"language": "en"}, has_docs=True).route == "document"

        overview = post("What is in this document?", cid)
        overview_text = "".join(frame.get("text", "") for frame in overview if frame["type"] == "delta")
        assert "42 employees" in overview_text
        assert overview[0]["route"] == "document"
        assert captured and "uploaded documents" in captured[-1][0]["content"]
        assert "42 employees" in captured[-1][-1]["content"]

        specific = post("What is the internal project code?", cid)
        specific_text = "".join(frame.get("text", "") for frame in specific if frame["type"] == "delta")
        assert "AURORA-731" in specific_text
        assert specific[-1]["sources"][0]["document"] == "aurora.txt"
        hindi_hits = rag.query(cid, "Aurora में कितने कर्मचारी हैं?", top_k=1)
        assert hindi_hits["hits"] and hindi_hits["hits"][0]["document"] == "aurora.txt"

        before = len(captured)
        absent = post("Who is the CEO of Zephyr-999?", cid)
        absent_text = "".join(frame.get("text", "") for frame in absent if frame["type"] == "delta")
        assert "couldn't find" in absent_text
        assert len(captured) == before  # retrieval gate rejects unsupported content before generation
    finally:
        rag._sessions.clear()
        rag._model, rag.GROUND_THRESHOLD = real_model, real_threshold
        llm.stream_chat, settings.LLM_API_KEY = real_stream, real_key


def test_grounding_rescues_natural_fact_wording_without_accepting_absent_query():
    hit = [{"score": 0.395, "text": "Project Aurora has 42 employees."}]
    assert rag.grounded(hit, query_text="What is the total number of employees?")
    assert not rag.grounded(hit, query_text="Who is the CEO of Zephyr-999?")
    assert router.is_document_overview("What is this document about?")
    assert router.is_document_overview("Give me information about this file")


def test_pdf_page_metadata_and_docx_table_extraction():
    pdf = pdf_fixture(["Project Aurora has 42 employees.", "Headquarters are in Jaipur.", "Code AURORA-731."])
    extracted = documents.extract_text(pdf, "aurora.pdf")
    assert "[Page 1]" in extracted and "[Page 3]" in extracted and "AURORA-731" in extracted
    chunks = documents.chunk_text(extracted, chunk_size=80, overlap=10)
    assert any(documents.page_number(chunk) == 3 for chunk in chunks)
    context, sources = _format_sources([{"document": "aurora.pdf", "chunk": 2, "page": 3,
                                         "score": 0.81, "text": "Code AURORA-731."}])
    assert "page 3" in context and sources[0]["page"] == 3

    from docx import Document
    doc = Document()
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Project"
    table.cell(0, 1).text = "Aurora"
    table.cell(1, 0).text = "Employees"
    table.cell(1, 1).text = "42"
    stream = io.BytesIO()
    doc.save(stream)
    assert "Employees | 42" in documents.extract_text(stream.getvalue(), "facts.docx")


def test_upload_failure_is_atomic_and_empty_file_is_rejected():
    real_model = rag._model
    rag._model = StableEmbed()
    try:
        cid = client.post("/api/v1/conversations").json()["conversation_id"]
        empty = client.post("/api/v1/documents", data={"conversation_id": cid},
                            files={"file": ("empty.txt", b"")})
        assert empty.status_code == 413
        bad = client.post("/api/v1/documents", data={"conversation_id": cid},
                          files={"file": ("empty.pdf", b"%PDF-not-readable")})
        assert bad.status_code == 422
        assert not rag.has_session(cid)
        class BrokenEmbed:
            def encode(self, *args, **kwargs): raise RuntimeError("embedding unavailable")
        rag._model = BrokenEmbed()
        failed = client.post("/api/v1/documents", data={"conversation_id": cid},
                             files={"file": ("facts.txt", b"Facts that should not be partially indexed.")})
        assert failed.status_code == 422
        assert not rag.has_session(cid)
    finally:
        rag._sessions.clear()
        rag._model = real_model


def test_document_sessions_are_isolated_and_fresh_upload_is_queryable():
    real_model, real_stream, real_key = rag._model, llm.stream_chat, settings.LLM_API_KEY
    rag._model = StableEmbed()
    settings.LLM_API_KEY = "test-key"
    llm.stream_chat = lambda messages, model=None: iter(["Aurora has 42 employees."])
    try:
        first = client.post("/api/v1/conversations").json()["conversation_id"]
        second = client.post("/api/v1/conversations").json()["conversation_id"]
        upload(first)
        upload(first, "borealis.txt", b"Project Borealis has 7 teams and is based in Pune.")
        hits = rag.query(first, "What is the internal project code?", top_k=2)
        assert hits["hits"][0]["document"] == "aurora.txt"
        assert not rag.has_session(second)
        other = post("What is the internal project code?", second)
        assert other[0]["route"] == "general"
        assert rag.has_session(first)
    finally:
        rag._sessions.clear()
        rag._model, llm.stream_chat, settings.LLM_API_KEY = real_model, real_stream, real_key
