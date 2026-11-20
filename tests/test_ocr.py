"""Offline-safe OCR and document-ingestion regressions.

The parser, page boundaries, persistence, duplicate protection and ownership
checks run without network access.  The live Tesseract assertion is skipped
only when the configured local OCR capability is genuinely unavailable; the
Docker image and the documented install provide it.
"""

from __future__ import annotations

import io
import os
import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import documents, memory, rag, settings, storage  # noqa: E402
from backend.main import app  # noqa: E402


def pdf_fixture(pages: list[str]) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + i * 3} 0 R".encode() for i in range(len(pages)))
        + f"] /Count {len(pages)} >>".encode(),
    ]
    for i, text in enumerate(pages):
        page_id, content_id, font_id = 3 + i * 3, 4 + i * 3, 5 + i * 3
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 700 Td ({safe}) Tj ET".encode()
        objects.extend([
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ])
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


class StableEmbed:
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        rows = []
        for text in texts:
            vector = np.zeros(32, dtype=np.float32)
            for token in text.lower().split():
                vector[hash(token) % len(vector)] += 1
            norm = np.linalg.norm(vector)
            rows.append(vector / norm if norm else vector)
        return np.asarray(rows, dtype=np.float32)


def text_image(text: str, *, background="white", foreground="black", angle: int = 0) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (3200, 900), background)
    draw = ImageDraw.Draw(image)
    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        if os.path.exists(path):
            font = ImageFont.truetype(path, 55)
            break
    draw.multiline_text((80, 100), text, fill=foreground, font=font, spacing=20)
    if angle:
        image = image.rotate(angle, expand=True)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_native_pdf_and_mixed_page_metadata(monkeypatch):
    native_pdf = pdf_fixture(["Native page: invoice number A-42.", "Native page: total 123.45."])
    report = documents.extract_document(native_pdf, "invoice.pdf")
    assert report.extraction_method == "native_text"
    assert report.pages[0].text.startswith("Native page")
    assert "[Page 2]" in report.full_text

    mixed_pdf = pdf_fixture(["Selectable heading.", ""])
    monkeypatch.setattr(
        documents, "_ocr_pdf_pages",
        lambda data, pages: {2: documents.OCRResult("Scanned total 99.00.", [], 91.0, "test")},
    )
    mixed = documents.extract_document(mixed_pdf, "mixed.pdf")
    assert mixed.extraction_method == "hybrid"
    assert mixed.pages[0].method == "native_text"
    assert mixed.pages[1].method == "ocr"
    assert documents.page_number("[Page 2]\nScanned total 99.00.") == 2
    assert "Scanned total 99.00." in mixed.full_text


def test_long_pages_keep_explicit_chunk_page_metadata():
    report = documents.ExtractionReport(
        "long.pdf", "pdf", "completed", "en", "native_text",
        [
            documents.ExtractionPage(1, "page one " * 400, "native_text"),
            documents.ExtractionPage(2, "page two " * 400, "native_text"),
        ],
        "",
    )
    chunks = documents.chunk_report(report, chunk_size=80, overlap=10)
    assert chunks and {page for _, page in chunks} == {1, 2}


def test_signature_validation_and_page_limit(monkeypatch):
    with pytest.raises(documents.UnsupportedFileType):
        documents.inspect_document(b"MZ\x00not a document", "invoice.pdf")
    monkeypatch.setattr(settings, "MAX_DOCUMENT_PAGES", 1)
    with pytest.raises(documents.TooManyPages):
        documents.inspect_document(pdf_fixture(["one", "two"]), "two-pages.pdf")


def test_keyword_fallback_does_not_ground_stopword_only_overlap():
    ranked = documents.score_chunks("Who is the CEO?", ["This is an unrelated note."], top_k=1)
    assert ranked[0][0] == 0.0


def test_live_local_image_ocr_if_configured(monkeypatch):
    if not documents.ocr_capabilities().get("available"):
        pytest.skip("local Tesseract OCR capability is not installed")
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1800, 500), "white")
    draw = ImageDraw.Draw(image)
    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        if os.path.exists(path):
            font = ImageFont.truetype(path, 96)
            break
    draw.text((80, 130), "INVOICE TOTAL 123.45", fill="black", font=font)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    monkeypatch.setattr(settings, "OCR_CONFIG", "--psm 6")
    report = documents.extract_document(stream.getvalue(), "invoice.png")
    normalized = " ".join(report.full_text.upper().split())
    assert "INVOICE" in normalized
    assert "123.45" in normalized or "12345" in normalized
    assert report.pages[0].ocr_confidence is not None


def test_rotated_and_low_contrast_images_if_configured():
    if not documents.ocr_capabilities().get("available"):
        pytest.skip("local Tesseract OCR capability is not installed")
    rotated = documents.extract_document(text_image(
        "THIS IS A ROTATED SYNTHETIC DOCUMENT WITH ENOUGH WORDS FOR ORIENTATION DETECTION TOTAL 77.00",
        angle=90,
    ), "rotated.png")
    assert "ROTATED" in rotated.full_text.upper()
    low_contrast = documents.extract_document(
        text_image("LOW CONTRAST TOTAL 88.00", background=(220, 220, 220), foreground=(160, 160, 160)),
        "low-contrast.png",
    )
    assert "LOW CONTRAST" in low_contrast.full_text.upper()


def test_live_scanned_pdf_if_configured():
    if not documents.ocr_capabilities().get("pdf_available"):
        pytest.skip("local PDF OCR capability is not installed")
    import fitz

    image_bytes = text_image("SCANNED PDF TOTAL 543.21")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(0, 0, 612, 792), stream=image_bytes)
    data = pdf.tobytes()
    pdf.close()
    report = documents.extract_document(data, "scanned.pdf")
    assert report.extraction_method == "ocr"
    assert "SCANNED PDF" in report.full_text.upper()


def test_duplicate_upload_report_preview_and_workspace_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GAIA_DB_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_DIR", str(tmp_path / "uploads"))
    storage.init_db()
    rag._read_index.cache_clear()
    original_model = rag._model
    rag._model = StableEmbed()
    first = TestClient(app, raise_server_exceptions=False)
    second = TestClient(app, raise_server_exceptions=False)
    try:
        cid = first.post("/api/v1/conversations").json()["conversation_id"]
        payload = {"conversation_id": cid}
        file_data = b"Invoice number A-42. Total amount is 123.45."
        one = first.post("/api/v1/documents", data=payload, files={"file": ("invoice.txt", file_data)})
        two = first.post("/api/v1/documents", data=payload, files={"file": ("invoice-again.txt", file_data)})
        assert one.status_code == 200, one.text
        assert two.status_code == 200, two.text
        assert one.json()["document_id"] == two.json()["document_id"]
        assert two.json()["duplicate"] is True
        listed = first.get(f"/api/v1/documents/{cid}").json()["documents"]
        assert len(listed) == 1 and listed[0]["status"] == "completed"
        document_id = one.json()["document_id"]
        report = first.get(f"/api/v1/documents/{cid}/{document_id}")
        assert report.status_code == 200 and "123.45" in report.json()["full_text"]
        denied = second.get(f"/api/v1/documents/{cid}/{document_id}")
        assert denied.status_code == 403
    finally:
        rag._model = original_model
        rag._read_index.cache_clear()
