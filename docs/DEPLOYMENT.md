# Deployment

## Current (what we submit/demo)

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.lock
venv/bin/python scripts/train.py   # builds models/intent_classifier.joblib
venv/bin/python app.py             # http://127.0.0.1:8000   (GAIA V2 default)
# Optional regression-only baseline:
venv/bin/python app.py --legacy    # http://127.0.0.1:5000
```

The default localhost page is the new V2 frontend. V2 additionally needs `.env` with `LLM_API_KEY`
(free Groq key) for the general/document/web routes; campus/translate work keyless.

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
docker run --rm -p 8000:8000 --env-file .env -v "$PWD/data:/app/data" language-agnostic-chatbot
```

The default image still uses SQLite and a single process. Move the database,
uploads and vector index to a deliberate multi-node design before horizontal
scaling.

## Before any real deployment, the minimum hardening list

1. Production server (gunicorn `app:app`) behind a proxy.
2. Restrict CORS/host binding; add request rate limiting.
3. Replace the local workspace cookie with authenticated account subjects and
   enforce authorization at the deployment boundary before exposing user data.
4. Move MT off free endpoints (quota + privacy) or self-host OPUS-MT.
5. Don't log raw user text (currently logged for the study — see app.py;
   add a LOG_USER_TEXT=off switch).
6. Serve via a process manager with restarts; keep `cache/` writable.
