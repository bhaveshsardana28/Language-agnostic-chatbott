# Deployment

## Current (what we submit/demo)

```bash
make install                       # Python 3.12 dependencies
venv/bin/python app.py             # http://127.0.0.1:8000   (GAIA V2 default)
# Optional compatibility interface:
venv/bin/python app.py --legacy    # http://127.0.0.1:5000
```

General chat, web answers and document generation require a configured cloud model or running Ollama service. Explicit machine translation uses its existing services independently.

V2 conversation messages and document chunks/embeddings are persisted in SQLite
at `data/gaia.db` by default (override with `GAIA_DB_PATH`). The database is
local runtime state and is intentionally ignored by git. Browser clients receive
an `HttpOnly` `gaia_workspace` cookie; it provides local workspace ownership
boundaries for conversations and uploads, but is not account authentication.

OCR is local by default. `requirements.lock` installs PyMuPDF, Pillow and
pytesseract; the host must also provide Tesseract and the requested language
packs. Set `OCR_ENABLED=1` (the default), configure `OCR_LANG=eng` or an
installed combination such as `eng+hin`, and verify `/api/v1/health` before
accepting uploads. Without PDF OCR capability, native text and mixed PDFs still
work; image-only pages fail explicitly instead of being indexed as empty text.
`/api/v1/health` reports `ocr_available` plus `ocr.languages`,
`ocr.pdf_available`, and any missing requested language.

The deterministic multilingual retrieval benchmark does not call an LLM:

```bash
python scripts/eval_rag_multilingual.py --json
```

## Docker

`Dockerfile` installs Python 3.12, the local Tesseract engine and English,
Hindi, Punjabi, Spanish, French, German and Italian packs. Build and run it
with:

```bash
docker build -t language-agnostic-chatbot .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env -v gaia-data:/app/data language-agnostic-chatbot
```

The default image still uses SQLite and a single process. Move the database,
uploads and vector index to a deliberate multi-node design before horizontal
scaling.

## Before any real deployment, the minimum hardening list

1. Run `venv/bin/python -m uvicorn backend.main:app` behind a TLS reverse proxy. Use one worker with the local SQLite and translation cache configuration. The Flask entry point serves the stateless compatibility interface.
2. Authenticate users at a trusted boundary, bind conversation and document ownership to those identities, configure allowed origins and enforce per-user rate, byte and storage quotas. Worker concurrency limits protect capacity during requests. Public multi-tenant release remains gated.
3. Set `WORKSPACE_COOKIE_SECURE=1` under HTTPS. Keep provider credentials in runtime secrets. Review provider retention for chat, translation, web queries and document excerpts.
4. The image uses UID 10001. Mount a writable data volume for the database and uploads. Back up SQLite using a consistent snapshot and back up original files with it. Test restoration on isolated storage. Define retention for browser history, uploads, logs and the translation cache.
5. Install the embedding model and required OCR language packs before offline use. Check the health response and run a known-answer document query. Test provider authentication, quotas and availability separately.
6. Build and smoke-test the container on the intended Linux platform before release. This audit verified native startup. The local Docker daemon was unavailable.
