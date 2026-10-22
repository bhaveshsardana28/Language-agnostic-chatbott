# API

Two apps live in this repo:

- **FYP pivot system** — Flask, port 5000 (below; the graded baseline)
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
| `/api/v1/documents/{cid}` | DELETE | drop this chat's document store |
| `/api/v1/chat/{cid}` | DELETE | delete conversation memory AND its documents |
| `/api/v1/health` | GET | status, provider, model, llm_ready, storage and OCR capability |
| `/api/v1/languages` | GET | supported languages |
| `/api/v1/intents` | GET | campus KB intents + router routes |

`POST /api/v1/chat` body: `{"message": "...", "conversation_id": "..."}`.
SSE frames (`data: {json}`):
- `meta`: `conversation_id`, `language_meta {language, language_name, script, confidence}`, `route` (general/campus_kb/translate/document/web), `response_lang`, `reason`
- `delta` ×N: `text` (+ `intent`/`confidence` on campus route)
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

## FYP — Flask (app.py, port 5000)

## GET `/api/v1/health`
```json
{"status": "ok", "model": "models/intent_classifier.joblib", "languages": 7}
```

## GET `/api/v1/languages`
```json
{"en": "English", "hi": "Hindi", "pa": "Punjabi", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian"}
```

## GET `/api/v1/intents`
```json
["admission_info", "attendance", ..., "identity", ..., "transport"]
```

## POST `/chat`
Request:
```json
{"message": "Wann sind die Prüfungen?"}
```
Response (all fields real and measured; nothing fabricated):
```json
{
  "lang": "de",
  "language_meta": {"language": "de", "language_name": "German", "script": "Latn", "confidence": 1.0},
  "english": "Wann sind die Prüfungen? (translated)",
  "intent": "exam_schedule",
  "confidence": 0.5411,
  "reply": "...German reply...",
  "degraded": false,
  "timings": {"detect_ms": 2.0, "translate_in_ms": 980.5, "classify_ms": 1.4, "respond_ms": 890.2, "total_ms": 2590.9}
}
```
Notes:
- `intent` is `"fallback"` (with localized polite reply) when confidence < 0.30,
  and `null` + `degraded: true` when detection/MT failed.
- On outbound-MT failure the reply degrades to English with `degraded: true`.
- `timings` cover every pipeline stage; `respond_ms` includes outbound MT.
- `GET /` serves the chat UI. History is client-side (localStorage) only.

Errors: `400 {"error": "empty message"}` on blank input, `403` when a
conversation belongs to another workspace, `413` for oversized uploads or
page limits, `415` for unsupported/corrupt signatures, and `422` for readable
but empty/failed extraction. The error payload includes a stable `code`.
