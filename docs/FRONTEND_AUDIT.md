# FRONTEND AUDIT — Phase 0

**Project**: Global Multilingual AI Assistant (formerly Language Agnostic Chatbot)
**Date**: 2026-10-02
**Auditor**: Phase 0 automated deep inspection
**Status**: READ-ONLY AUDIT — no code modified

---

## 1. Current Stack

| Layer          | Technology                          | Version        |
| -------------- | ----------------------------------- | -------------- |
| Backend (FYP)  | Flask                               | 3.1.3          |
| Backend (v2)   | FastAPI + Uvicorn                   | 0.142.2 / 0.54 |
| Frontend       | Vanilla HTML/CSS/JS (single file)   | N/A            |
| Templating     | Jinja2                              | 3.1.6          |
| Language Det.  | langdetect + custom heuristics      | 1.0.9          |
| Translation    | deep-translator (Google + MyMemory) | 1.11.4         |
| Intent Model   | scikit-learn TF-IDF + LogReg        | 1.9.1          |
| RAG Embeddings | sentence-transformers               | 6.1.0          |
| LLM Client     | Raw HTTP (requests/httpx)           | —              |
| PDF Parsing    | pypdf                               | 6.19.0         |
| DOCX Parsing   | python-docx                         | 1.2.0          |
| Web Scraping   | BeautifulSoup4                      | 4.15.0         |

### Frontend Build

There is **no build step** for the active frontend. The file `templates/index.html` is a self-contained 881-line vanilla HTML/CSS/JS SPA served by both Flask (port 5000) and FastAPI (port 8000) via Jinja2.

A separate `portfolio/` directory exists with a **blank Vite + React 19 starter template** (React 19.2.7, Vite 8.1.0). It contains zero chat/voice/API code — only the default Vite welcome page with a counter demo.

### Decision: Which Frontend Is Active?

**`templates/index.html`** is the active, functional frontend. The `portfolio/` directory is unused scaffolding.

---

## 2. Current Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Two Parallel Servers                    │
│                                                          │
│  ┌────────────────────┐   ┌────────────────────────────┐ │
│  │ Flask (app.py)     │   │ FastAPI (backend/main.py)  │ │
│  │ Port 5000          │   │ Port 8000                  │ │
│  │ FYP Baseline       │   │ GAIA v2 Portfolio Layer    │ │
│  │ POST /chat (sync)  │   │ POST /api/v1/chat (SSE)   │ │
│  └────────┬───────────┘   └───────────┬────────────────┘ │
│           │                           │                  │
│           ▼                           ▼                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │        src/ — Shared Core Pipeline                │    │
│  │  detection.py → translation.py → classifier.py   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │        backend/ — v2-only modules                 │    │
│  │  router.py · llm.py · memory.py · rag.py · web.py│    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

Both servers serve the **same** `templates/index.html`. However, the frontend's API calls target relative paths (`/api/v1/chat`, etc.), which means it functionally targets whichever server it's served from. The **v2 FastAPI** server is the intended frontend target (SSE streaming, LLM, RAG, documents, web search).

---

## 3. Current Folder Structure

```
language_agnostic_chatbot/
├── app.py                    # Flask FYP baseline server (port 5000)
├── config.py                 # Shared config (languages, thresholds, paths)
├── requirements.txt          # Python dependencies
├── .env.example              # v2 env template
├── .env                      # Active env (gitignored)
├── .gitignore
├── Makefile                  # make run / make run-v2
│
├── backend/                  # FastAPI v2 layer
│   ├── main.py               # FastAPI app, all endpoints
│   ├── router.py             # Deterministic request router
│   ├── llm.py                # LLM streaming client
│   ├── memory.py             # In-process conversation memory
│   ├── rag.py                # Document ingestion + retrieval
│   ├── documents.py          # PDF/DOCX/TXT extraction
│   ├── web.py                # DuckDuckGo web search
│   └── settings.py           # Env var loading
│
├── src/                      # Shared FYP pipeline
│   ├── detection.py          # Multi-layer language detection
│   ├── classifier.py         # TF-IDF + LogReg intent classifier
│   ├── translation.py        # Google/MyMemory translation with cache
│   └── pipeline.py           # Orchestrates detect → translate → classify → respond
│
├── templates/
│   └── index.html            # ★ ACTIVE FRONTEND (881 lines, vanilla JS)
│
├── portfolio/                # ★ UNUSED React 19 + Vite starter template
│   ├── package.json
│   ├── vite.config.js
│   └── src/                  # Default Vite welcome page only
│
├── data/
│   ├── intents_en.json       # 16 campus-specific intent training data
│   └── test_multilingual.json # 30 multilingual test queries
│
├── models/
│   └── intent_classifier.joblib
│
├── cache/
│   └── translations.json     # MT cache
│
├── tests/                    # pytest + playwright
├── scripts/                  # Training, evaluation, threshold tuning
├── docs/                     # Architecture, API, evaluation docs
├── archive/                  # Retired Streamlit "Aikya" prototype
├── results/                  # Evaluation outputs
└── logs/
    └── app.log
```

---

## 4. API Integration

The frontend communicates exclusively with the FastAPI v2 backend via relative URLs. All API calls are centralized in a single `api` object (lines 398–432 of `templates/index.html`).

### API Client Architecture

```javascript
const api = {
  health:           () => fetch('/api/v1/health'),
  newConversation:  () => fetch('/api/v1/conversations', {method:'POST'}),
  deleteConversation: id => fetch(`/api/v1/chat/${id}`, {method:'DELETE'}),
  listDocuments:    id => fetch(`/api/v1/documents/${id}`),
  clearDocuments:   id => fetch(`/api/v1/documents/${id}`, {method:'DELETE'}),
  uploadDocument:   (id, file) => /* FormData POST */,
  chat:             (message, cid, handlers, signal) => /* SSE stream reader */
};
```

**Good**: All API calls are in one place, not scattered across components.

---

## 5. Actual Endpoints (FastAPI v2)

### `GET /`

Serves `templates/index.html` via Jinja2.

### `GET /api/v1/health`

**Response:**
```json
{
  "status": "ok",
  "llm_provider": "groq",
  "llm_model": "qwen/qwen3.8-27b",
  "llm_ready": true,
  "llm_note": "",
  "languages": 7
}
```

### `POST /api/v1/conversations`

**Response:**
```json
{ "conversation_id": "uuid-string" }
```

### `DELETE /api/v1/chat/{conversation_id}`

**Response:**
```json
{ "deleted": true, "documents_deleted": false }
```

### `POST /api/v1/documents`

**Body:** Multipart form — `file` (UploadFile) + `conversation_id` (string)
**Allowed**: `.pdf`, `.docx`, `.txt`, `.md` — max 10 MB
**Response:**
```json
{
  "conversation_id": "...",
  "document": "filename.pdf",
  "chars": 12000,
  "chunks": 10,
  "chunk_size": 1200,
  "overlap": 150,
  "embeddings": true
}
```

### `GET /api/v1/documents/{conversation_id}`

**Response:**
```json
{
  "conversation_id": "...",
  "documents": [{"document": "file.pdf", "chunks": 10}]
}
```

### `DELETE /api/v1/documents/{conversation_id}`

**Response:**
```json
{ "deleted": true }
```

### `POST /api/v1/chat` ★ Primary endpoint

**Body:**
```json
{ "message": "string", "conversation_id": "string (optional)" }
```

**Response:** SSE stream (`text/event-stream`)

---

## 6. Request Formats

The chat endpoint accepts JSON with `Content-Type: application/json`. The document upload uses `multipart/form-data`. All other endpoints use standard GET/DELETE with no body.

---

## 7. Response Formats — SSE Streaming Frames

The chat endpoint streams four types of SSE frames:

### `meta` frame (always first)

```json
{
  "type": "meta",
  "conversation_id": "abc123",
  "language_meta": {
    "language": "hi",
    "primary_language": "hi",
    "language_name": "Hindi",
    "secondary_languages": [],
    "code_switched": false,
    "mixed_script": false,
    "scripts": {"Devanagari": 1.0},
    "script": "Devanagari",
    "confidence": 0.95,
    "detection_reason": "langdetect primary"
  },
  "route": "general",
  "reason": "no special trigger",
  "response_lang": "hi"
}
```

### `delta` frame (one or more, streamed)

```json
{
  "type": "delta",
  "text": "chunk of text"
}
```

For campus_kb route, delta also includes:
```json
{
  "type": "delta",
  "text": "full response",
  "intent": "hostel",
  "confidence": 0.87,
  "degraded": false
}
```

### `error` frame (if something went wrong)

```json
{
  "type": "error",
  "message": "Localized error message"
}
```

### `done` frame (always last)

```json
{
  "type": "done",
  "latency_ms": 1234.5,
  "model": "groq:qwen/qwen3.8-27b",
  "sources": [
    {"document": "file.pdf", "chunk": 3, "score": 0.82},
    {"title": "Web Result", "url": "https://example.com"}
  ]
}
```

---

## 8. Streaming Architecture

- **Protocol**: Server-Sent Events (SSE) over HTTP POST
- **Frontend parsing**: Manual `ReadableStream` reader with `TextDecoder` (lines 416–431)
- **Buffering**: Frame-based parsing with `\n\n` delimiter, `data:` prefix stripping
- **Cancellation**: `AbortController` signal passed to `fetch()`
- **Stop button**: Calls `aborter.abort()` — the `AbortError` is caught and the partial response is preserved
- **Scroll during stream**: Uses `requestAnimationFrame` + `isNearBottom()` check — only auto-scrolls if user is near the bottom

**Assessment**: Streaming architecture is well-implemented. The SSE parsing is correct and handles partial buffers properly.

---

## 9. Current State Management

All state is managed via a single `store` object backed by `localStorage`:

```javascript
const KEY = 'gaia.store.v1';
store.data = {
  conversations: [{
    id: "string",
    title: "string",
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: [{
      role: "user" | "assistant",
      content: "string",
      content_md: "html string (assistant only)",
      ts: timestamp,
      meta: { language_meta, route, reason, response_lang },
      sources: [],
      model: "string",
      latency: number,
      intent: "string",
      confidence: number,
      error: boolean,
      debug_error: "string",
      stopped: boolean
    }]
  }],
  currentId: "string | null",
  theme: "dark" | "light" | "system",
  enterSend: true,
  debug: false
}
```

**Runtime state** (not persisted):
- `streaming` (boolean) — is a response currently being streamed
- `aborter` (AbortController | null) — active stream cancellation handle
- `uploading` (boolean) — document upload in progress

**Assessment**: State management is clean and minimal. No unnecessary global state. The `store` is a simple object with `load()` and `save()`. No race conditions observed in the state model itself.

---

## 10. Current Chat Behavior

1. User types message → `send()` called
2. If no active conversation, one is created client-side with `uid()`
3. User message painted immediately
4. `run()` creates an assistant message placeholder with "Generating…" pulse
5. SSE stream begins:
   - `meta` frame → stored on message object
   - `delta` frames → appended to `am.content`, `textContent` updated live
   - `error` frame → error state set, user-friendly message shown
   - `done` frame → latency, model, sources stored
6. On completion: live element removed, final message re-painted with full markdown + actions
7. Store saved to localStorage

**Copy, Regenerate, Edit**: All implemented.
- **Copy**: `navigator.clipboard.writeText()` with fallback
- **Regenerate**: Drops trailing assistant messages, resends last user message
- **Edit**: Splices messages from edit point, puts text back in composer

**Assessment**: Chat machine is well-structured. The repaint-on-done approach (remove live element, repaint with markdown) is clean.

---

## 11. Current Multilingual Behavior

### Backend

- **Language detection**: Multi-layered — greeting maps → script analysis → `langdetect` with heuristics for romanized Hindi/Punjabi and European languages
- **Supported languages**: 7 — English, Hindi, Punjabi, Spanish, French, German, Italian (+ Japanese in router's `LANG_NAME_TO_CODE`)
- **Same-language reply**: The router sets `response_lang` from the detected language; the LLM system prompt instructs it to reply in that language
- **Language switching**: If user says "answer in Hindi", the router detects the instruction and overrides `response_lang`
- **Code-switching**: Detection recognizes mixed-script and code-switched messages; metadata includes `code_switched`, `mixed_script`, `secondary_languages`
- **Translation route**: Explicit "translate X to Y" commands are routed to the MT engine

### Frontend

- **Language metadata display**: Behind the debug toggle only (`body.debug .debug-card`). Shows language, confidence, secondary languages, code-switching, scripts, detection reason, router decision, intent, model, latency.
- **No visible language indicator on messages by default**: The language chip is only in the debug card.
- **No language switch divider**: Not implemented.
- **`dir="auto"` not used**: Messages do not set `dir` attribute for RTL scripts.

---

## 12. Current RAG Behavior

- **Upload**: Via file input → `POST /api/v1/documents` (multipart)
- **Display**: Document chips in `#doc-strip` show filename, chunk count, status
- **Clear**: "Clear documents" button → `DELETE /api/v1/documents/{cid}`
- **Routing**: If session has documents, router returns `route: "document"`. But the backend has a **retrieval gate** — if document excerpts don't match the query (low similarity), it returns a "not found in documents" response with `model: "retrieval-gate"` and does NOT fall through to general chat.
- **Citations**: Document sources shown in `done` frame, rendered as "document — chunk N"

**Assessment**: RAG behavior is correctly implemented. The retrieval gate prevents hallucination. However, when documents are uploaded, ALL queries go through the document route — there's no way for the user to ask a general question while documents are uploaded (see router.py line 122–123: `if has_docs: return Route("document", ...)`).

---

## 13. Current Web-Search Behavior

- **Trigger**: Recency keywords ("latest", "today", "current", "news", "price of", "who won", "right now", "2026")
- **Engine**: DuckDuckGo Lite (keyless, scraped with BeautifulSoup)
- **Results**: Up to 4 hits injected into LLM system prompt with citation instructions
- **Frontend**: Web sources rendered as clickable links in the sources section
- **Degradation**: If web search fails, degrades silently to general chat

**Assessment**: Well-implemented with proper degradation. No fake sources generated.

---

## 14. Current Voice Behavior

### Voice Input

**NOT IMPLEMENTED** in the current active frontend (`templates/index.html`). There is no microphone button, no Web Speech API usage, no voice input of any kind.

The `archive/voice.py` contains an older Streamlit-based voice implementation using `speech_recognition` (server-side), but it is not connected to any active code.

### Voice Output

**NOT IMPLEMENTED**. No SpeechSynthesis usage, no "Listen" buttons, no voice output.

---

## 15. Existing Bugs

### BUG-01: Campus-specific content in "About" section

**File**: `templates/index.html` line 851
**Issue**: The About text says "campus knowledge base" — this is university-specific terminology that contradicts the "general-purpose AI assistant" branding.
**Severity**: Low (cosmetic)

### BUG-02: No CORS configured on FastAPI

**File**: `backend/main.py`
**Issue**: No CORS middleware is configured. If the frontend is ever served from a different origin (e.g., during development with Vite on a different port), all API calls will fail.
**Severity**: Medium (blocks development workflow with separate frontend server)

### BUG-03: Conversation ID mismatch — client vs server

**File**: `templates/index.html` line 555 vs `backend/main.py` line 77
**Issue**: The frontend creates conversation IDs client-side (`uid()` = `Math.random().toString(36).slice(2,10)`) and never calls `POST /api/v1/conversations` to get a server-side ID. The `POST /api/v1/conversations` endpoint exists but is not used. The backend's `memory.create()` returns a UUID. When the frontend sends its client-generated 8-char ID as `conversation_id`, the backend accepts it (it just creates memory for whatever ID it receives), but:
  - The IDs are 8 chars vs UUIDs — inconsistent
  - Server-side `DELETE /api/v1/chat/{cid}` may fail to clean up properly if IDs don't match what the backend created via `memory.create()`

**Severity**: Low (functionally works because backend accepts arbitrary IDs, but architecturally messy)

### BUG-04: Document route locks out general conversation

**File**: `backend/router.py` lines 122–123
**Issue**: When `has_docs` is true, ALL messages route to "document" — even general questions unrelated to the documents. The user cannot have a general conversation while documents are uploaded.
**Severity**: Medium (UX issue, documented in prompt requirements section 15)

### BUG-05: `streaming` flag set in `textContent` not `innerHTML`

**File**: `templates/index.html` line 654
**Issue**: During streaming, `bubble.textContent = am.content` — this correctly prevents XSS during streaming (no markdown rendering while streaming), but it means long responses with markdown appear as raw text during streaming. Only after completion is markdown rendered.
**Severity**: Low (functional, just not as polished as progressive markdown rendering)

### BUG-06: No character limit enforcement on frontend

**File**: `templates/index.html`
**Issue**: The backend enforces `MAX_MESSAGE_CHARS` (default 4000), but the frontend has no character counter or validation. Users see a generic error if they exceed the limit.
**Severity**: Low

### BUG-07: `friendly()` has campus-specific error message

**File**: `templates/index.html` line 549
**Issue**: Error message says "Campus and translation features still work" — campus-specific language.
**Severity**: Low (cosmetic)

---

## 16. Console Errors

**Not testable in audit phase** — requires running the application. Will be tested in Phase 1.

---

## 17. Network Errors

**Not testable in audit phase** — requires running the application. Will be tested in Phase 1.

---

## 18. Responsive Problems

### Code Inspection Findings

- **Breakpoints**: 900px (mobile drawer) and 430px (compact)
- **Mobile drawer**: Sidebar transforms to fixed overlay with scrim — properly implemented
- **`100dvh` used**: Line 35 uses `height:100dvh` as progressive enhancement over `100vh` — good
- **`env(safe-area-inset-bottom)` used**: Composer padding accounts for iOS safe area — good
- **Horizontal overflow**: Code blocks have `overflow-x:auto` — good
- **Max-width on chat**: `max-width:780px` on `.chat-inner` — good

### Potential Issues

- **No 768px breakpoint**: Jumps from 900px to 430px. Tablets may have layout issues.
- **No 360px breakpoint**: Narrowest tested width is 430px. Very small phones not explicitly handled.
- **`overflow:hidden` on body**: Line 25 — `body{overflow:hidden}` prevents any fallback scrolling. If layout breaks, content is simply clipped with no recovery.

**Severity**: Low-Medium. Needs real-device testing in Phase 1.

---

## 19. Accessibility Problems

### Good

- `aria-label` on all icon-only buttons
- `aria-pressed` on debug toggle
- `role="log"` and `aria-live="polite"` on chat area
- `role="alert"` on offline banner
- `role="dialog"` and `aria-modal="true"` on overlay
- `:focus-visible` styled (line 28)
- `aria-hidden="true"` on decorative SVGs

### Missing / Issues

- **No skip-to-content link**
- **No focus trapping in modals**: The settings modal and confirm dialog don't trap focus
- **Keyboard navigation incomplete**: Can't navigate conversation list with arrow keys
- **No screen-reader announcements for streaming**: `aria-live="polite"` is on the container, but streaming updates `textContent` rapidly — screen readers may spam read
- **No ARIA labels on conversation list items**: Buttons have title but no explicit role
- **Color-only status indicator**: The online/offline dot relies on green/red color alone (line 85–86)
- **`prefers-reduced-motion` implemented**: Line 29 — disables all transitions/animations. Good.

**Severity**: Medium. Core accessibility is present but incomplete.

---

## 20. Performance Problems

- **Single 881-line HTML file**: No code splitting, no lazy loading. However, since it's vanilla JS with zero dependencies, the total payload is ~48 KB uncompressed — extremely lightweight.
- **No minification**: Served as-is by Jinja2.
- **Markdown re-render on completion**: The entire message is re-rendered when streaming completes (remove live element → repaint). For very long messages, this causes a brief layout shift.
- **No virtual scrolling**: All messages are in the DOM. For very long conversations (100+ messages), this could degrade scroll performance.
- **`sentence-transformers` + `torch` in backend**: These are heavy dependencies (torch 2.14.1). First document upload will be slow if the model needs loading. Not a frontend issue per se, but affects perceived performance.

**Severity**: Low. The frontend is very lightweight. Backend embedding model load time is the main performance concern.

---

## 21. Security Problems

### Good

- **XSS prevention**: `esc()` function (line 376) escapes all HTML entities before markdown parsing. Markdown is rendered via custom parser that escapes first, then applies formatting. This is XSS-safe by construction.
- **Code blocks escaped**: Code content is escaped before insertion.
- **Links have `rel="noopener"`**: Line 455.
- **No `dangerouslySetInnerHTML`** (it's vanilla JS, but the equivalent `innerHTML` is only used with escaped content).
- **No API keys in frontend**.
- **`.env` is gitignored**.

### Issues

- **`.env` file exists in repo root**: While gitignored, it contains `LLM_API_KEY`. If git tracking was initialized before `.gitignore`, it might have been committed.
- **No CSP headers**: No Content-Security-Policy configured on the server.
- **No rate limiting**: Backend has no rate limiting on any endpoint.
- **`rel="noopener"` but missing `noreferrer`**: Line 455 uses `rel="noopener"` but not `rel="noopener noreferrer"`.
- **Confirm dialogs use custom modal, not `window.confirm`**: Good for UX, but the custom confirm doesn't prevent interaction with the background (no `inert` attribute on main content).

**Severity**: Low-Medium. Core security is solid. CSP and rate limiting are nice-to-haves for a demo.

---

## 22. Technical Debt

1. **Two parallel servers**: Flask (port 5000) and FastAPI (port 8000) serve the same frontend. The Flask server is the FYP graded baseline; FastAPI is the portfolio layer. For the final product, only FastAPI is needed.

2. **Monolithic HTML file**: 881 lines of HTML + CSS + JS in one file. While functional, this makes iteration difficult. The `portfolio/` React scaffold was presumably intended to replace this.

3. **No TypeScript**: Vanilla JS with no type checking.

4. **No component reuse**: Everything is procedural. No componentization.

5. **No tests for frontend**: All tests (`tests/`) are Python backend tests. No frontend unit tests or component tests exist.

6. **Client-side conversation IDs**: Created with `Math.random()` — not cryptographically random, but acceptable for local demo.

7. **Backend memory is ephemeral**: `memory.py` uses in-process `deque` — all conversation context is lost on server restart. Only localStorage persists chat history.

8. **Campus KB intents baked into model**: The 16 intents in `data/intents_en.json` are entirely campus-specific (exams, hostel, ERP, placements, etc.). The intent classifier will always classify general queries through this campus lens.

---

## 23. Dependencies

### Backend (requirements.txt)

| Package              | Version | Purpose                           |
| -------------------- | ------- | --------------------------------- |
| Flask                | 3.1.3   | FYP baseline server               |
| scikit-learn         | 1.9.1   | Intent classification             |
| langdetect           | 1.0.9   | Language detection                 |
| deep-translator      | 1.11.4  | Google/MyMemory translation        |
| matplotlib           | 3.11.2  | Evaluation plots (not runtime)     |
| fastapi              | 0.142.2 | v2 API server                      |
| uvicorn              | 0.54.0  | ASGI server                        |
| jinja2               | 3.1.6   | HTML templating                    |
| python-multipart     | 0.0.32  | File upload parsing                |
| httpx                | 0.28.1  | HTTP client (LLM calls)           |
| beautifulsoup4       | 4.15.0  | Web search HTML parsing            |
| pypdf                | 6.19.0  | PDF text extraction                |
| python-docx          | 1.2.0   | DOCX text extraction               |
| sentence-transformers| 6.1.0   | RAG embeddings                     |
| torch                | 2.14.1  | ML framework (for embeddings)      |

### Frontend

**Zero dependencies.** The active frontend is vanilla HTML/CSS/JS.

The unused `portfolio/` has: `react` 19.2.7, `react-dom` 19.2.7, `@vitejs/plugin-react` (dev), `vite` 8.1.0 (dev), `oxlint` 1.69.0 (dev).

---

## 24. Recommended Architecture

### Decision: Build on `portfolio/` (React 19 + Vite) or improve `templates/index.html`?

**Recommendation: Build the new frontend in `portfolio/` (React 19 + Vite).**

Rationale:
1. The current vanilla JS frontend is functional but monolithic — 881 lines in one file with no componentization makes it difficult to add voice, accessibility, tests, and animations systematically.
2. React 19 + Vite is already scaffolded and ready.
3. Component-based architecture enables proper testing (Vitest + React Testing Library).
4. CSS Modules or a design token system is straightforward in Vite.
5. The existing vanilla frontend serves as an excellent **reference implementation** — we know exactly what works and can replicate the API integration precisely.
6. No framework migration is needed since the React app is blank — we're building, not migrating.

### Recommended React Architecture

```
portfolio/src/
├── app/
│   └── App.jsx                 # Root component, layout
├── components/
│   ├── chat/
│   │   ├── ChatArea.jsx        # Message list + scroll engine
│   │   ├── Message.jsx         # Single message bubble
│   │   ├── WelcomeScreen.jsx   # Initial greeting + suggestions
│   │   └── LanguageChip.jsx    # Language indicator
│   ├── composer/
│   │   ├── Composer.jsx        # Input + send/stop + attach
│   │   └── CharCounter.jsx     # Character limit display
│   ├── sidebar/
│   │   ├── Sidebar.jsx         # Conversation list + search
│   │   └── ConversationItem.jsx
│   ├── voice/
│   │   ├── VoiceInput.jsx      # Microphone + recognition
│   │   ├── VoiceOutput.jsx     # Per-message listen button
│   │   └── VoiceMode.jsx       # Full-screen voice mode
│   ├── settings/
│   │   ├── SettingsModal.jsx
│   │   └── ConfirmDialog.jsx
│   ├── debug/
│   │   └── DebugCard.jsx       # Language/route metadata
│   └── ui/
│       ├── IconButton.jsx
│       ├── Toast.jsx
│       ├── Modal.jsx
│       └── OfflineBanner.jsx
├── hooks/
│   ├── useChat.js              # Chat state + streaming logic
│   ├── useStore.js             # localStorage persistence
│   ├── useScroll.js            # Smart auto-scroll
│   ├── useVoiceInput.js        # Speech recognition
│   ├── useVoiceOutput.js       # Speech synthesis
│   └── useTheme.js             # Dark/light/system
├── lib/
│   ├── api.js                  # Centralized API client (port from vanilla)
│   ├── markdown.js             # Markdown renderer (port or use library)
│   ├── speech.js               # Speech API configuration
│   └── storage.js              # localStorage wrapper
├── store/
│   └── chatStore.js            # Zustand or useReducer store
├── types/
│   └── index.js                # JSDoc type definitions
├── config/
│   ├── languages.js            # BCP-47 codes, display names
│   └── constants.js            # Thresholds, limits
└── styles/
    ├── tokens.css              # Design tokens (CSS custom properties)
    ├── global.css              # Reset, typography, base
    └── components/             # Per-component CSS modules
```

---

## 25. Recommended Frontend Stack

| Concern            | Recommendation                    | Justification                                    |
| ------------------ | --------------------------------- | ------------------------------------------------ |
| Framework          | React 19 (already scaffolded)     | Already in `portfolio/`, no migration needed      |
| Build              | Vite 8 (already scaffolded)       | Already configured, fast HMR                     |
| Styling            | CSS Modules + design tokens       | Zero added deps, scoped styles, tokens in `:root` |
| State              | React hooks (useState/useReducer) | Simple enough for this app, no extra dependency   |
| Markdown           | Custom (port existing) or `marked`| Existing parser works; `marked` adds sanitization |
| Syntax highlight   | `highlight.js` (lazy-loaded)      | Standard, supports 100+ languages                |
| Testing            | Vitest + React Testing Library    | Vite-native, fast                                |
| E2E                | Playwright (already in project)   | Already used for backend tests                   |
| Linting            | oxlint (already configured)       | Already in portfolio/package.json                |

### Dependencies to Add

- None mandatory — the existing zero-dependency approach for the core is excellent
- Optional: `marked` + `DOMPurify` for markdown (safer than custom parser)
- Optional: `highlight.js` for syntax highlighting in code blocks
- Vitest + @testing-library/react for tests

---

## 26. Risks

### High Risk

1. **Building React frontend from scratch**: The `portfolio/` app has zero code. Everything must be built. This is a significant effort, but the existing vanilla frontend provides a complete reference.

2. **Backend document route locks out general chat**: When documents are uploaded, all queries go to the document route. This needs a frontend or backend fix.

### Medium Risk

3. **Voice features are entirely new**: No voice code exists anywhere in the active codebase. Browser Speech API support varies significantly across browsers and languages.

4. **Campus intents in the classifier**: The intent classifier only knows 16 campus-specific intents. For a "general-purpose AI assistant", the campus_kb route should work but not dominate. The router already handles this well — campus routing requires BOTH keyword evidence AND classifier confidence above threshold.

5. **No CORS**: Developing with Vite (port 5173) and FastAPI (port 8000) will require CORS configuration.

6. **Ephemeral server memory**: Server restarts lose all conversation context. Only localStorage persists.

### Low Risk

7. **`sentence-transformers` cold start**: First document upload loads a ~100 MB model. Subsequent uploads are fast.

8. **DuckDuckGo rate limiting**: Web search may be throttled under heavy use.

---

## 27. What Must Remain Unchanged

1. **All backend API endpoints**: Request/response formats must be preserved exactly.
2. **Backend routing logic**: The `router.py` decision tree is well-designed and must not be modified.
3. **Language detection pipeline**: `src/detection.py` is well-tested and working.
4. **Translation pipeline**: `src/translation.py` with Google/MyMemory fallback and caching.
5. **Intent classifier**: `src/classifier.py` + trained model in `models/`.
6. **LLM integration**: `backend/llm.py` streaming client.
7. **RAG pipeline**: `backend/rag.py` + `backend/documents.py`.
8. **Web search**: `backend/web.py`.
9. **Memory management**: `backend/memory.py`.
10. **Configuration**: `config.py` + `backend/settings.py` + `.env` format.
11. **Flask baseline**: `app.py` must remain as-is (FYP graded artifact).
12. **Tests**: All existing tests must continue to pass.
13. **Data files**: `data/intents_en.json`, `data/test_multilingual.json`.
14. **Archive**: `archive/` directory preserved as historical reference.
15. **Documentation**: Existing docs preserved and extended, not replaced.

---

## Summary

| Area                 | Status          | Notes                                          |
| -------------------- | --------------- | ---------------------------------------------- |
| Backend              | ✅ Complete      | Well-designed, all features functional          |
| API Design           | ✅ Complete      | Clean SSE streaming, proper error handling      |
| Active Frontend      | ⚠️ Functional   | 881-line monolith, no voice, no tests           |
| React Frontend       | ❌ Empty         | Blank Vite starter, everything must be built    |
| Streaming            | ✅ Working       | Proper SSE parsing + abort support              |
| Language Detection   | ✅ Working       | 7 languages + code-switching + mixed-script     |
| RAG                  | ✅ Working       | Upload, chunk, embed, retrieve, cite            |
| Web Search           | ✅ Working       | DuckDuckGo with graceful degradation            |
| Voice Input          | ❌ Not Built     | No implementation exists                        |
| Voice Output         | ❌ Not Built     | No implementation exists                        |
| Chat History         | ✅ Working       | localStorage-based with search/rename/delete    |
| Dark/Light Theme     | ✅ Working       | Dark, light, and system modes                   |
| Accessibility        | ⚠️ Partial      | Core ARIA present, focus trap/keyboard missing   |
| Responsive           | ⚠️ Partial      | Mobile drawer works, mid-range untested          |
| Security             | ✅ Solid         | XSS-safe markdown, escaped output, no key leak  |
| Tests                | ⚠️ Backend Only  | No frontend tests                               |
| Documentation        | ✅ Extensive     | Architecture, API, evaluation docs exist         |

---

**PHASE 0 COMPLETE.**

**No application code has been modified.**

**Awaiting "continue" to proceed to Phase 1 — Stability and Bug Fix.**
