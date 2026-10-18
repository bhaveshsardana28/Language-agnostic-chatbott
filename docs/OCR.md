# OCR and document intelligence

## Confirmed original failure

The existing document route was not failing in the LLM prompt or vector
retriever first. Its primary failure was earlier: raw images were rejected by
both allow-lists, and scanned PDFs produced no text through `pypdf`. The
optional fallback depended on PyMuPDF and pytesseract, neither of which was
installed in the development environment. That exception was converted into
an empty extraction, so ingestion returned 422 before chunking, embedding or
retrieval. The default OCR language was also only `eng`.

The fix keeps the existing FastAPI → SQLite chunks → multilingual embeddings →
retrieval → grounded LLM flow and replaces the optional, whole-document OCR
fallback with page-aware extraction.

## Selected engine

The default engine is local Tesseract through `pytesseract`, with PyMuPDF for
bounded PDF rendering and Pillow for image validation/preprocessing. This is
the smallest compatible local stack for the current Python application:

* It preserves privacy and works without a hosted OCR account.
* Tesseract provides installed-language selection, token confidence and word
  bounding boxes.
* PyMuPDF renders only pages with insufficient native text.
* Pillow covers PNG/JPEG/TIFF/BMP/WebP and optional HEIC/HEIF support when the
  local build can decode those formats.
* OpenCV and PaddleOCR were not added: they would increase the install/runtime
  footprint without being required by the current RAG architecture. The
  preprocessing uses EXIF orientation, best-effort Tesseract orientation,
  scaling, grayscale, autocontrast, median denoising and contrast enhancement.

External OCR APIs are not implemented and are not silently used.

## Processing flow

1. The API reads at most `MAX_UPLOAD_BYTES + 1` bytes and rejects empty or
   oversized bodies.
2. `backend.documents.detect_file_type` validates signatures rather than
   trusting the filename extension. PDFs are parsed to enforce
   `MAX_DOCUMENT_PAGES`; image containers are verified by Pillow; DOCX files
   must contain the Office ZIP markers; text files must be valid UTF-8.
3. Native PDF text is extracted page by page. Pages with at least
   `OCR_MIN_TEXT_CHARS` visible characters remain native; only other pages are
   rendered for OCR. Mixed PDFs therefore retain both sources.
4. Image uploads and DOCX embedded images use the same local OCR path.
5. Reports retain page boundaries, blocks/bounding boxes, warnings, tables from
   DOCX as structured rows, and the Tesseract token-mean confidence with its
   source label. Confidence is not presented as a calibrated probability.
6. A completed report is chunked, embedded and persisted atomically with its
   source hash, metadata and original upload. Empty/failed extraction is never
   indexed. Re-uploading identical bytes in one conversation is idempotent.
7. Retrieval keeps document, document ID, chunk and page metadata. Overview
   prompts sample chunks across long documents; precise questions use the
   grounding gate. The existing LLM receives excerpts in the user turn and
   emits page-aware source metadata without fabricated citations.

## Structured report

`GET /api/v1/documents/{conversation_id}/{document_id}` returns the stable
report shape:

```json
{
  "schema_version": 1,
  "document_id": 7,
  "filename": "invoice.pdf",
  "status": "completed",
  "detected_language": "en",
  "extraction_method": "hybrid",
  "page_count": 2,
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "blocks": [],
      "tables": [],
      "warnings": [],
      "quality": {"ocr_confidence": null, "needs_review": false},
      "extraction_method": "native_text"
    }
  ],
  "full_text": "...",
  "warnings": [],
  "char_count": 1234
}
```

## Languages and formats

The code accepts Tesseract combinations such as `eng+hin`; the actual usable
languages are reported by `/api/v1/health` and `scripts/eval_ocr.py --json`.
The Docker image installs `eng`, `hin`, `pan`, `spa`, `fra`, `deu` and `ita`
plus orientation data, matching the languages claimed by the existing chatbot.
The current development Mac had only `eng`, `osd` and `snum` installed when
the local measurement was recorded. Missing packs are reported rather than
silently transliterated or treated as universal support.

Supported file families:

* PDF: native text, scanned pages, mixed pages and multi-page documents.
* Images: PNG, JPEG/JPG, TIFF, BMP, WebP; HEIC/HEIF when Pillow supports the
  installed decoder.
* DOCX, including paragraph/table extraction and embedded-image OCR.
* UTF-8 TXT, Markdown, CSV, JSON, Python and JavaScript text files.

The current limits default to 10 MiB and 100 PDF pages. Override them in `.env`
only with an operational memory/time budget.

## Measurements

Run:

```bash
./venv/bin/python scripts/eval_ocr.py --json
```

The checked local run used synthetic, non-sensitive rendered text and reported:

| Fixture | CER | WER |
|---|---:|---:|
| clean image | 0.0000 | 0.0000 |
| rotated image | 0.0000 | 0.0000 |
| low-contrast image | 0.0000 | 0.0000 |
| scanned PDF | 0.0000 | 0.0000 |

These are fixture measurements, not a universal accuracy claim. Handwriting,
severe perspective distortion, dense tables, unusual fonts and uninstalled
scripts need a separate labeled evaluation. CER/WER and downstream retrieval
Recall@k/MRR should be measured on representative, consented data before a
production accuracy target is chosen.

## Operational/security notes

The original upload is written under `DOCUMENT_STORAGE_DIR` with a generated
SHA-256 filename and mode 0600; the user filename is display metadata only.
Temporary files are created in that controlled directory and removed on
failure. Deleting a conversation removes its chunks and source unless another
conversation still references the same content hash. The API never exposes a
source path or public file URL, and logs record error types rather than document
contents. The workspace cookie is still a local ownership boundary, not real
account authentication; deploy behind authenticated subjects before exposing
private documents.
