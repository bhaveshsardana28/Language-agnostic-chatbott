# Phase 5 — Multilingual metadata and explainability

**Completed 13 October 2026.** Entry: `http://localhost:8000/` (direct asset path:
`/static/v2/index.html`).
This slice extends the Phase 4 conversation without changing the FastAPI SSE contract
or the original `/` assistant.

## Delivered

- Each V2 user turn receives the detected language metadata from the `meta` frame.
  The assistant turn receives the server-selected `response_lang` rather than
  assuming that the input language is the output language.
- Language chips show native and English names together. A detection confidence below
  0.5 gets a dashed visual hint, an accessible label and a verification tooltip.
- Turns and message bodies use `dir="auto"`; the header also names the detected script
  so Devanagari, Gurmukhi, Arabic and mixed-script replies have visible context.
- A language-switch divider is inserted once, before an assistant reply, only when
  its response language differs from the nearest prior completed assistant reply.
- Settings now includes **Show reply insights**, off by default and persisted in the
  redesign preference record. When enabled, each completed assistant reply exposes an
  inline `Insights` disclosure with safe text for detected/response language,
  confidence, secondary languages, code switching, scripts, detection reason,
  route/reason, intent/confidence, model, latency and technical state.
- Mock mode includes a low-confidence mixed-script fixture so the boundary is tested
  without needing a provider key.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/js/chat.js` | Language labels, direction/script metadata, switch dividers and Insights rendering |
| `static/v2/js/preferences.js` | Persisted `debug` preference and `data-debug` state |
| `static/v2/js/appearance.js` | Settings synchronization for the Insights toggle |
| `static/v2/index.html` | Accessible Insights setting copy |
| `static/v2/css/chat.css` | Confidence hint, switch divider, script and Insights presentation |
| `static/v2/js/mock.js` | Deterministic mixed-script low-confidence fixture |
| `scripts/verify_languages.py` | Browser checks for metadata, settings, switching and confidence behavior |

## Verification

```text
./venv/bin/python scripts/verify_languages.py
4 Phase 5 check groups passed; 0 screenshots.

./venv/bin/python scripts/verify_languages.py --capture
4 Phase 5 check groups passed; 1 screenshot.

node --check static/v2/js/chat.js
node --check static/v2/js/mock.js
node --check static/v2/js/appearance.js
node --check static/v2/js/preferences.js

git diff --check
clean
```

The browser battery covers native/English labels, script labels, `dir="auto"`,
default-off Insights, persisted toggle behavior, real metadata fields, a single
English-to-Hindi divider and the low-confidence dashed hint. The captured result is
recorded in `docs/language-checks.json`, with the screenshot in
`docs/screenshots/phase5/`.

## Remaining parity work

Source cards from `done.sources` remain a later document/web presentation slice.
History, document upload, full-date timestamps, syntax highlighting, voice and
durable conversation settings remain unchanged from the Phase 4 handoff.
