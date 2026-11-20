# API

Two apps live in this repo:

- **Compatibility interface** — Flask, port 5000
- **GAIA v2 layer** — FastAPI, port 8000 (this section's SSE/chat/document API)

Base (dev): `http://localhost:8000`. V2 uses an `HttpOnly` `gaia_workspace`
cookie to scope conversations and document uploads to a local browser
workspace. This is an ownership boundary, not account authentication (see
LIMITATIONS.md before deploying anywhere).

## v2 — FastAPI (backend/main.py)

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | chat UI (dark/light theme, debug mode, doc upload) |
| `/api/v1/chat` | POST | SSE stream: meta → deltas → done (see below) |
| `/api/v1/conversations` | POST | create a conversation (for pre-chat doc upload) |
| `/api/v1/documents` | POST | multipart upload (validated PDF/DOCX/TXT/Markdown/image ≤ 10 MiB, max 100 PDF pages), per-conversation scope |
| `/api/v1/documents/{cid}` | GET | list this chat's documents, status, pages, method and chunk counts |
| `/api/v1/documents/{cid}/{document_id}` | GET | structured page-aware extraction report and extracted-text preview |
| `/api/v1/documents/{cid}/{document_id}` | DELETE | remove one authorized document and its indexed chunks |
| `/api/v1/documents/{cid}` | DELETE | drop this chat's document store |
| `/api/v1/chat/{cid}` | DELETE | delete conversation memory AND its documents |
| `/api/v1/health` | GET | status, provider, model, llm_ready, storage and OCR capability |
| `/api/v1/languages` | GET | supported languages |
| `/api/v1/intents` | GET | active routes and the empty legacy `campus_kb` array |

`POST /api/v1/chat` body: `{"message": "...", "conversation_id": "..."}`.
SSE frames (`data: {json}`):
- `meta`: `conversation_id`, `language_meta {language, language_name, script, confidence}`, `route` (general/translate/document/web), `response_lang`, `reason`
- `delta` ×N: `text`
- `error` (optional): localized safe message, never a stack trace
- `done`: `latency_ms`, `model`, `sources[]` (document: name+document_id+chunk+optional page+score+retrieved excerpt; web: title+url)

The upload response includes `document_id`, `status`, `page_count`,
`detected_language`, `extraction_method`, per-page warning/quality summaries,
and an idempotency `duplicate` flag. Full `text`, `blocks`, `tables`, page
boundaries and `quality.ocr_confidence` are returned only by the report endpoint.
Confidence is the Tesseract token mean when supplied by the engine; it is not a
calibrated document-level probability.

Language rules: detection per message; reply in the latest message's language
unless the user instructs otherwise ("answer in Hindi", "hindi mein", "auf Deutsch").

## Stateless JSON compatibility interface

Flask’s `GET /api/v1/health` returns `status`, the configured generator’s `model` name and the number of supported `languages`. Its languages endpoint returns the language map. Its intents endpoint returns an empty JSON array. FastAPI keeps the original object shape on its intents endpoint, with `campus_kb: []` and the four active routes.

Flask and FastAPI both accept `POST /chat` with a string `message` and an optional supported `language`. The result includes the detected `lang`, `language_meta`, `response_language`, provider-generated `reply`, `degraded`, and measured `timings`. For compatibility, `intent` is null and top-level `confidence` is 0.0. Language detection confidence remains available in `language_meta.confidence`. The `english` field contains the input for English messages and an empty string otherwise. No English pivot is required for generation. Provider failures return a degraded reply. V2 streaming errors use the existing SSE error event.

Errors: `400 {"error": "empty message"}` on blank input, `403` when a
conversation belongs to another workspace, `413` for oversized uploads or
page limits, `415` for unsupported/corrupt signatures, and `422` for readable
but empty/failed extraction. The error payload includes a stable `code`.

### Request and streaming limits

Chat accepts a JSON object with a string message and an optional conversation ID.
Malformed JSON, invalid Unicode and invalid field types receive HTTP 400. Oversized chat bodies receive 413. The local worker admits up to 16 simultaneous V2 chat requests and two uploads. At capacity it returns 429 with Retry-After. The file limit defaults to 10 MiB, with an additional 64 KiB allowance for the multipart envelope. On a stream error the client receives an error event followed by completion metadata. Failed provider output is excluded from subsequent model context.

The FastAPI compatibility page at `/legacy` uses the same JSON `POST /chat` contract as Flask. In that contract `lang` identifies the input, `language` in the request selects the reply language, and `response_language` in the response identifies the delivered language.

A successful V2 completion can carry a numeric `reply_id`. To regenerate the last answer, send its ID as `replace_reply` together with the same question and conversation ID. The server excludes that turn from generation context, then replaces it atomically on success. A stale revision receives HTTP 409 if already stale at admission or a stream error if it changes during generation.
