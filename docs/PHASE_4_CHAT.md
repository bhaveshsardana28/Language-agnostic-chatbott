# Phase 4 — Chat transport and conversation turn

**Completed 12 October 2026.** Entry: `http://localhost:8000/` (direct asset path:
`/static/v2/index.html`).
The Phase 3 shell remains the layout foundation; this phase connects its composer to
the existing FastAPI SSE contract without changing the original `/` assistant.

## Delivered

- Enter sends a non-empty draft; Shift+Enter keeps a newline. The draft is capped at
  4,000 characters, warns after 3,600, and exposes a live character count.
- The composer changes to Stop while a turn is active. Escape and Stop abort the
  request. A partial streamed reply is retained with a clear stopped marker, while
  stale deltas are ignored after cancellation or New chat.
- User and assistant turns render in the conversation view with timestamps,
  language/script metadata, route metadata, busy state, copy, Edit, Retry and code
  block copy actions.
- Live chat uses `POST /api/v1/chat` and parses `meta`, `delta`, `error` and `done`
  SSE frames. The server-issued conversation ID is carried into the next turn.
- `?mock=1` provides a labelled, delayed fixture stream. It never calls the backend
  and exercises code, Markdown, cancellation and route metadata in an isolated
  browser run.
- Assistant Markdown uses an escape-first renderer supporting headings, emphasis,
  inline code, fenced code, lists, quotes, tables, rules and HTTPS links. Unsafe
  protocols and raw HTML are rejected before insertion.
- HTTP failures, malformed streams, missing `done`, empty replies and stream
  cancellation become recoverable assistant states with safe user-facing text.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/index.html` | Conversation view, message log, character status and Phase 4 composer copy |
| `static/v2/css/chat.css` | Turn layout, Markdown content, code blocks, actions, pending state and responsive rules |
| `static/v2/js/chat.js` | Composer lifecycle, SSE ownership, cancellation, message actions and rendering |
| `static/v2/js/markdown.js` | Escape-first Markdown subset and clipboard plain-text extraction |
| `static/v2/js/mock.js` | Deterministic delayed stream used only with `?mock=1` |
| `static/v2/js/api.js` | FastAPI health and conversation API boundary |
| `scripts/verify_chat.py` | Mock, renderer, error-stream and optional live campus browser checks |

## Transport contract

The browser sends:

```json
{"message": "...", "conversation_id": "..."}
```

The first turn may omit `conversation_id`; the backend creates one and returns it in
the `meta` frame. Subsequent turns send that ID. A normal stream is:

```text
data: {"type":"meta", ...}

data: {"type":"delta","text":"..."}

data: {"type":"done", ...}
```

No server text, raw SSE payload or exception detail is interpolated into the page.

## Verification

Environment: **macOS 27.0.1 ARM64; Python 3.12.7; Playwright 1.63.0; Chromium 153.0.8010.12**.

```text
./venv/bin/python scripts/verify_chat.py --capture --live http://127.0.0.1:8000
8 Phase 4 check groups passed; 3 screenshots; live: True.

./venv/bin/python tests/test_code_switching.py
ALL CODE-SWITCHING TESTS PASSED

git diff --check
clean
```

The check groups cover:

- labelled mock mode, delayed streaming, 4,000-character guard, code rendering,
  route metadata, copy actions and no chat POST;
- Escape cancellation, ownership-safe New chat and stale-delta prevention;
- Retry replacement of the failed assistant answer without duplicating the user turn;
- hostile HTML/protocol filtering and plain-text extraction;
- HTTP 413, empty `meta`-only streams and malformed SSE recovery; and
- two live keyless campus replies, including the server conversation ID on turn two.

Screenshots are stored in `docs/screenshots/phase4/`; the machine-readable result is
`docs/chat-checks.json`. The optional live check only uses the keyless campus route;
general/document/web routes still require their configured integrations.

## Remaining parity work

Conversation history and restoration, document upload, source presentation, voice,
near-bottom scroll preservation and settings integrations remain later phases. The
existing app route and `gaia.store.v1` storage are untouched.
