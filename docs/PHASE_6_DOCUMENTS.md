# Phase 6 — Documents and source cards

**Implemented 13 October 2026.** The default entry point is
`http://localhost:8000/`; the direct V2 asset path remains
`/static/v2/index.html`.

This slice adds document context to the Phase 6 local conversation lifecycle. It
uses the existing FastAPI document/RAG endpoints; document text, metadata and
embeddings now survive a backend restart through the SQLite store.

## Delivered

- The Documents dialog accepts PDF, DOCX, TXT, Markdown/CSV and common image
  files, and performs client-side empty/10 MiB checks before upload.
- Uploads show Processing, Ready and Failed states. The synchronous backend call is
  treated honestly as the processing interval; there is no invented polling API.
- Uploading before the first chat creates a server conversation ID, stores it on the
  local V2 record, and uses that same ID for upload, document listing and later chat.
- The dialog lists per-conversation filenames and chunk counts, shows ready counts,
  and can clear all documents for the active server conversation after confirmation.
- Switching or restoring conversations refreshes the document list and guards
  against stale list/upload responses painting into another conversation.
- Narrow screens stack the document toolbar and document status rows below 448px,
  avoiding the cramped picker/status overlap that can occur on very small phones.
- Assistant `done.sources` now renders visible source cards for document chunks,
  validated HTTP(S) web links and text-only retrieval notes. Document chunk indexes
  are displayed to people as one-based values while preserving backend values in
  stored metadata.
- Persisted conversations restore their source cards. Unsafe source protocols are
  never turned into links.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/js/documents.js` | Upload/list/clear controller, statuses, validation and stale-response guards |
| `static/v2/js/api.js` | Multipart upload, list and clear API boundary with status-aware errors |
| `static/v2/js/chat.js` | Server-ID bridge and source-card rendering/restoration |
| `static/v2/js/main.js` | Initializes documents after the chat controller |
| `static/v2/index.html` | File picker, document list/status/clear controls |
| `static/v2/css/shell.css` | Document panel, rows and status chips |
| `static/v2/css/chat.css` | Source-card presentation |
| `scripts/verify_documents.py` | Deterministic upload, source, restore, clear and failure browser checks |

## Verification

```text
./venv/bin/python scripts/verify_documents.py --capture
7 Phase 6 document check groups passed; 1 screenshot.

./venv/bin/python scripts/verify_history.py --capture
10 Phase 6 history check groups passed; 1 screenshot.

make test
core, V2, and code-switching tests passed

node --check static/v2/js/chat.js
node --check static/v2/js/documents.js
node --check static/v2/js/api.js
node --check static/v2/js/main.js

git diff --check
clean
```

Evidence is recorded in `docs/document-checks.json` and
`docs/screenshots/phase6/light-1440-documents.png`.

## Honest boundaries

- The backend returns a synchronous ingestion report, not a durable job/status ID.
- SQLite is durable for a single local node, while the NumPy retrieval matrix is
  rebuilt lazily after restart. It is not yet a managed multi-instance vector
  service.
- Scanned PDFs and images require the local PyMuPDF/Pillow/Tesseract capability;
  otherwise image-only uploads fail explicitly rather than being indexed as
  empty text. Health reports the exact engine and language-pack availability.
- Source cards show only fields emitted by the API: document/chunk/score, title/URL
  or note. They do not invent excerpts, pages or dates.
- OCR details, page-level text preview and retry are available in the document
  panel. The composer is disabled while synchronous ingestion is processing.
- Account authentication, rate limiting and full multi-instance deployment
  hardening remain separate work. A deterministic 10-case multilingual retrieval
  benchmark is available at `scripts/eval_rag_multilingual.py`.
