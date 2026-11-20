# GAIA V2 – A Language-Agnostic, General-Purpose AI Chatbot

GAIA V2 is a multilingual AI assistant for everyday questions, learning, writing, programming, research and document-based conversations. People can switch languages within a chat or request a particular reply language.

## Quick start

Use Python 3.12 and configure a hosted provider or local Ollama model in `.env`. The default workspace opens at http://127.0.0.1:8000.

```bash
cp -n .env.example .env
make install
make test
make run
```

The optional Flask compatibility UI runs with `make run-legacy` on port 5000. FastAPI also serves the compatibility page at `/legacy`.

## Request routing

| Route | Behavior |
|---|---|
| General | Sends the original message, response-language instruction and recent conversation context to the configured LLM. Educational questions use this same path. |
| Translate | Explicit translation requests use the existing machine translation services and local cache. |
| Document | Retrieves excerpts from the conversation’s uploaded files and asks the configured model for a grounded answer. |
| Web | Searches for time-sensitive information and supplies returned sources to the model. |

The Language Agnostic Chatbot frontend makes the language-agnostic workflow visible without
claiming unsupported capabilities: per-message language detection,
language-switch instructions ("answer in Hindi"), bounded conversation memory,
SSE streaming, dark/light/system themes,
welcome screen with suggestions, markdown + code blocks with copy buttons,
per-conversation sidebar (search/rename/delete/export, grouped by date),
message actions (copy/regenerate/edit), document chips, sources,
professional debug panel, settings, offline banner, mobile drawer,
**voice input** (browser SpeechRecognition, BCP-47 language selection, editable
no-auto-send transcript). Completed replies offer Listen when browser speech synthesis is available. Playback uses a matching installed local voice and stops on a conversation switch or microphone start. Physical-device voice testing is pending. See docs/VOICE_TEST_MATRIX.md.
Tested with real-browser Playwright smoke plus mocked V2 voice checks:
`make test-browser` and `make test-v2-voice`.
The offline test suite also covers code-switching detection.
APIs: `/api/v1/{chat,conversations,documents,languages,intents,health}` —
see docs/API.md. Real-device voice results remain untested.

### Frontend workspace

GAIA V2 opens in dark mode with a collapsible history sidebar and an anchored composer.
Use the language control in the header to add an editable reply-language instruction to a draft.
Open Reply details to inspect the current response. The panel shows service-reported detected and response language, route, returned sources, model,
and measured server latency. Conversation history and search are browser-local
because the current API does not expose account authentication or conversation
listing.

The knowledge base dialog uses the live document endpoints for upload, status,
report preview, per-document deletion, and clearing the current conversation's
sources. The frontend deliberately does not expose account controls, fake
retrieval progress, invented source language, or unsupported response-language
persistence.

See [docs/FRONTEND_REDESIGN.md](docs/FRONTEND_REDESIGN.md) for the audit,
architecture, capability boundaries, and verification report.

Run the offline test suite: `make test`. It covers the core app, V2 RAG,
SQLite restart/ownership boundaries, OCR parser behavior, synthetic image/PDF
fixtures when the local OCR capability is installed, and code switching.

### OCR and document intelligence

The V2 upload path validates file signatures, stores the original upload under a
generated hash, extracts native text first, and OCRs only pages that need it.
The local OCR stack is PyMuPDF + Pillow + pytesseract + Tesseract; it does not
send private documents to a third-party OCR API. Supported inputs are text and
mixed/scanned PDFs, DOCX (including embedded images when OCR is available), TXT,
Markdown/CSV/JSON/code text, PNG/JPEG/TIFF/BMP/WebP, and HEIC/HEIF only when the
installed Pillow build can decode them. See `docs/OCR.md` for configuration,
language packs, structured reports, and measured fixture results.

For a reproducible local setup:

```bash
cp -n .env.example .env
make install
make test
./venv/bin/python scripts/eval_ocr.py --json
make run                         # http://localhost:8000
```

The release checks are intentionally small and repeatable:

```bash
make lint
make test                         # offline regression suite
```

### Providers, privacy and deployment

Set `LLM_PROVIDER` to `groq`, `openrouter`, `openai` or `ollama`, and choose a model available on that provider. Cloud providers need `LLM_API_KEY`. Ollama needs a running local service and an installed model. Use `OPENAI_COMPAT_BASE_URL` only for an intentional endpoint override. Health reports configuration and OCR capabilities. A successful chat verifies model access.

General chat sends recent conversation turns to the configured provider. Document chat also sends retrieved excerpts. Explicit translation requests can send the source text to Google and MyMemory. General multilingual chat goes directly to the configured chat provider. Web search sends the query to DuckDuckGo. SQLite stores bounded chat context, extracted text and vectors. Original uploads and the machine translation cache are separate files. Browser history is stored on the device. Configure access and retention for all four locations before handling sensitive data.

Browser QA uses an optional development dependency and a browser installation.

```bash
./venv/bin/python -m pip install playwright==1.63.0
./venv/bin/python -m playwright install chromium
make test-browser                     # with make run in another terminal
make test-v2-voice                    # synthetic speech engine
```

For deployment prerequisites, measured results and open release gates, see [deployment notes](docs/DEPLOYMENT.md), [final audit](FINAL_AUDIT_REPORT.md), [historical test results](TEST_RESULTS.md) and [feature matrix](FEATURE_MATRIX.md).

## Project origins

Final-year project — B.Tech CSE (AI/ML), The NorthCap University, Gurugram.

| | |
|---|---|
| **Team** | Bhavesh Sardana (23csu070) · Dakksh Sharma (23csu081) · Avi (23csu061) |
| **Supervisor** | Ms. Meghna Sharma |

The original project report, evaluation data and authorship records are preserved for historical reference. The historical intent-classifier experiments are outside the application startup, deployment image and request path. Current model documentation is in [docs/MODELS.md](docs/MODELS.md).
