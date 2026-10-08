# Frontend Audit

Basis: actual files inspected in this session + live WebKit/Chromium probes
against the running app (`http://127.0.0.1:8000`). No claims from memory.

## 1. Current Stack
- **Frontend:** one server-rendered Jinja2 template — `templates/index.html`
  (1,248 lines) with vanilla JS/CSS. **Zero** runtime frontend dependencies,
  no bundler, no framework, no `package.json` for the app (the `portfolio/`
  folder has one but is an unrelated Vite site).
- **Backend (source of truth, not modified):** FastAPI — `backend/main.py`
  (289 lines) on port 8000; separate graded FYP Flask app — `app.py` (69
  lines) on port 5000, untouched.
- **Package manager:** none for the frontend (no build step). Python venv
  for the backend (`requirements.txt`).

## 2. Repository Structure
Frontend-relevant tree (verified via `find`):
```
templates/index.html        <- entire frontend (HTML+CSS+JS)
backend/main.py              FastAPI app + routes + SSE
backend/{router,llm,rag,memory,documents,web,settings}.py
src/{detection,classifier,pipeline,translation}.py   FYP NLP layer
tests/test_browser.py        Playwright UI suite (496 lines)
tests/{test_v2,test_core,test_code_switching}.py    API/FYP/detection suites
docs/                        existing documentation set
data/, scripts/, models/, cache/                    data + training artifacts
```

## 3. Application Entry Point
- `backend/main.py:53` — `GET /` renders `templates/index.html`
  (`templates.TemplateResponse(request, "index.html", ...)`).
- Run: `venv/bin/python -m uvicorn backend.main:app --port 8000`
  (or `make run-v2`); FYP baseline: `venv/bin/python app.py` (:5000).

## 4. Routing
No frontend router. Single page; "views" are DOM states inside
`templates/index.html`: welcome screen (`#welcome`), chat feed (`#feed`),
drawer sidebar (`#sidebar.open`), modals (`#overlay-m`). Backend routes:
`backend/main.py` lines 53–118 (health, languages, intents, conversations,
documents CRUD, `POST /api/v1/chat`).

## 5. Layout Architecture
Verified in code (`templates/index.html:51-56,133,343-408`) and live WebKit:
```
.app    display:grid; grid-template-columns:280px 1fr; height:100vh/100dvh
  aside.sidebar        column 1 (flex column, min-height:0)
  #scrim (hidden)      mobile drawer backdrop only
  main.main            column 2: flex column; min-width:0; min-height:0
    header.topbar  → #doc-strip → #offline → #chat (flex:1; min-height:0;
    overflow-y:auto; overscroll-behavior:contain) → .composer-wrap
```
This matches the intended AppShell (Sidebar | Main[Header, Content,
Composer]). Live geometry @1440 WebKit: `main=[x:280,w:1160]`,
`composer bottom y+h=900` — composer inside MAIN, not sidebar. PASS.

## 6. Sidebar
`templates/index.html:345-366` (markup) + `renderSidebar()` (~line 823):
brand, New chat, search (`#search`), conversation list grouped
Today/Yesterday/Previous-7-days/Older, per-row actions (export/rename/
delete with confirm), Settings button, Delete-all-data, local-storage
privacy note. `#conv-list{flex:1;min-height:0;overflow-y:auto}` (line 72)
scrolls independently. Mobile: fixed drawer + `#scrim`, hamburger `#menu-btn`
under `@media(max-width:900px)` (line 324).

## 7. Main Chat
`#chat` (line 398, `role="log" aria-live="polite"`) with `.chat-inner`
max-width 780px centered; `#welcome` (line 393-404) with cycling
multilingual greeting + 6 suggestion cards; document strip `#doc-strip`;
offline banner `#offline`. Scroll engine (~line 587):
`isNearBottom(120px)` gate, rAF-throttled `scheduleFollow()` (never
force-scrolls a reading user), jump pill `#jump`, single batched
`scrollBottom()` on conversation open.

## 8. Composer
`.composer-wrap` (line 408) — always the LAST flex child of `main`, after
`#chat`; CSS at lines 251-270: mic button, attach button, auto-growing
`textarea#input` (Enter=send / Shift+Enter=newline, 4,000-char guard),
send/stop morph (`#send`/`#stop`), safe-area padding
(`env(safe-area-inset-bottom)`). Never inside the sidebar — verified
structurally and by live geometry.

## 9. Message Rendering
`paintMsg()` (~line 700): user bubbles right/`accent-strong`, assistant
bubbles left with `md()` renderer (line 527) — escape-first
(numeric entities, `esc()` line 437; XSS regression-tested), headings,
lists, tables, blockquotes, links (`rel="noopener"`), fenced code blocks
with language label + copy button + dependency-free `hl()` tokenizer
(line 512). Per-message: timestamps, actions (copy / regenerate / retry /
edit / Listen), language chip (NATIVE map, `--lang` accent), debug card
(body.debug), day separators.

## 10. Streaming
`api.chat()` in `templates/index.html` (~line 481): `fetch` POST
`/api/v1/chat`, reads `response.body.getReader()`, parses SSE frames
(`data: {json}`) into `meta → delta* → error? → done`. States:
idle/sending/streaming/completed/error/cancelled; AbortController stop
preserves partial content; conversation-switch aborts in-flight streams;
final repaint only into the owning conversation. Backend emits these exact
frame types (`backend/main.py:141-187`).

## 11. API Integration
Centralized `api` object (~line 466) — the only place fetch is used:
health, conversations, documents CRUD, SSE chat. All backend fields
consumed are real (`backend/main.py:141-191`): `language_meta`
(language, language_name, script, confidence, code_switched, mixed_script,
scripts, detection_reason), `route`, `reason`, `intent`, `confidence`,
`sources` (title+url web / document+chunk+score), `latency_ms`, `model`,
`conversation_id`. No invented fields. No frontend API keys; provider key
lives in backend `.env` (gitignored, verified 404 when fetched).

## 12. State Management
`store` (~line 457): single `localStorage['gaia.store.v1']` object —
`{conversations[], currentId, theme, enterSend, debug, speechLang,
lastLang, noMotion, autoRead, speakRate}`; in-memory module singletons for
streaming/scroll/speech. One source of truth; sidebar/history render from it.

## 13. Chat History
Per-conversation `{id,title,createdAt,updatedAt,messages[]}`; grouped list,
rename (prompt), delete + delete-all (custom confirm dialogs, Escape
closes), content-match search with snippets, markdown export (Blob
download), quota-failure toast. Delete-all also clears the debug body class
and server-side conversation via `DELETE /api/v1/chat/{id}`.

## 14. Multilingual Handling
Backend `src/detection.py` (280 lines, segment+lexicon code-switching
detector, 26-case suite `tests/test_code_switching.py`) returns full
`language_meta` per message. Frontend: per-message language chip
(`हिन्दी · Hindi`), "Language switched: English → हिन्दी" divider only on
actual change, `dir="auto"` bubbles, Noto Devanagari/Gurmukhi in the font
stack, welcome greeting cycles the 7 tested languages. No language is
claimed that isn't backend-tested (7 documented in `docs/MODELS.md`).

## 15. RAG / Documents
Backend: `backend/rag.py` (session-scoped chunk store, multilingual
MiniLM embeddings, 0.45 grounding gate), routes at
`backend/main.py:89-116`. Frontend: attach button + `#doc-strip` chips
(Processing→Ready/Failed with chunk counts), upload validated client+server
(pdf/docx/txt/md ≤10 MB), sources rendered only from real `done.sources`
(document+chunk+score), honest "not found in the uploaded documents" flow
(`_not_found_in_docs`, `backend/main.py`). No per-document removal — backend
only supports clear-all; UI does not fake it. RAG activates only on backend
routing, never assumed for every message.

## 16. Web Search
Backend `backend/web.py` (keyless DuckDuckGo). Router sends
recency-queries to `web` route; frontend renders source chips
(title+URL, `rel="noopener"`) only when `done.sources` is non-empty; tool
failure degrades to general answer with empty sources — no fake browsing
indicators, no fabricated citations.

## 17. Voice
- **Input** (`templates/index.html` ~line 1085): browser SpeechRecognition
  (dynamic lookup), states idle/listening with pulse + "Listening…"
  placeholder, interim/final transcript into composer (no auto-send),
  BCP-47 language setting (Auto = last chat language), error map with
  fix instructions (permission denied/no mic/no speech/network/unsupported),
  Escape stops, Cmd/Ctrl+Shift+M toggles. No backend STT — browser only.
- **Output** (~line 1024): SpeechSynthesis per-message Listen,
  language-matched voices with honest "No voice available for X on this
  device" toast, auto-read setting with sentence-queued stream-aware speech
  (`feedSpeech`), markdown stripped, "Code block skipped.", rate select,
  barge-in on send/mic. No voice mode (orb) — deliberately cut per priority
  rules; documented in `docs/TESTING.md`.
- Engine state machines are regression-tested via mocks
  (`tests/test_browser.py`); real-device mic/speaker passes are NOT done —
  tracked in `docs/VOICE_TEST_MATRIX.md` (all rows honestly NOT TESTED).

## 18. Responsive Design
`@media(max-width:900px)` (line 324): drawer sidebar + scrim + hamburger;
`@media(max-width:430px)` refinements. Live-verified this session in
WebKit + Chromium at 1440/1280/1024/768/390/360: zero horizontal overflow,
composer visible, drawer opens/closes. `100vh` fallback before `100dvh`
(line 51). Regression checks for all six widths exist in the audit
session's probes; 62-check suite covers 375/1280.

## 19. Accessibility
axe-core 4.10.2 run this session (real results, in `docs/TESTING.md`):
**0 violations** across welcome, active chat, and settings modal after
root-cause fixes — AA solid-button token `--accent-strong:#2563eb`
(4.54:1), `aria-labelledby` named dialogs, focus lands in modal, Escape
closes, scroll region `tabindex="0"`, heading order h1→h2→h3. All
icon-only buttons labelled; `aria-live` chat log; `aria-pressed` on
mic/debug; `prefers-reduced-motion` + in-app Reduce-motion both honored.

## 20. Security
No secrets in `templates/index.html` (grep-verified; the only "API_KEY"
hit is an error-classification regex). `.env` not served (404 verified).
Markdown renderer is escape-first (XSS regression in suite). External
links `rel="noopener"`. Upload types/size gated. localStorage stores only
conversation text/settings. `.env` gitignored; `.env.example` has
placeholders only.

## 21. Performance
Measured (headless Chromium, `docs/TESTING.md`): single request, ~92 KB
uncompressed HTML; DCL ~120 ms local; 408 DOM nodes with 120-message
conversation; streaming via `textContent` (no re-render framework);
rAF-throttled scroll follow. Lighthouse NOT run — no scores claimed.

## 22. Current Bugs
Live-verified now:
1. **The reported layout bug (blank main / composer under sidebar) is
   FIXED in the current working tree** — live WebKit probes at 1440 and 390
   both PASS (scrim `display:none`; main at x=280 w=1160 desktop;
   composer bottom-of-main y+h=900). See §23.
2. Real-device Safari/Chrome mic+speaker untested (`docs/VOICE_TEST_MATRIX.md`).
3. Rename uses `prompt()` (functional, not custom-styled) — minor UX debt.
4. Theme paint-flash: pre-paint resolver exists; sub-100 ms timing not
   assertable headless — PARTIAL.
5. Uncommitted working tree (see git status) incl. unrelated `portfolio/`
   noise and `cache/translations.json` tracked — should not be committed.

## 23. Root Causes
The layout bug, from actual code history: the drawer backdrop `#scrim`'s
only `display:none` rule lived INSIDE `@media(max-width:900px)`, and the
`hidden` attribute had been removed from its markup. On desktop the scrim
was therefore a live `display:block` grid CHILD of `.app`
(`grid-template-columns:280px 1fr`) — auto-placement gave it row-1/col-2
(the main column), wrapping `main` to row-2/col-1: a 280px strip under the
sidebar = blank main area, composer below sidebar. **Fix in current code
(verified):** base rule `#scrim{display:none;...}` at
`templates/index.html:319` (outside the media query) + `hidden` attribute
restored at line 365; permanent regression check
("desktop shell: scrim inert, main beside sidebar, composer in main") in
`tests/test_browser.py`.

## 24. Technical Debt
- Single 1,248-line template — organized in labelled sections but due for
  a `static/` split (CSS + JS modules) once the FYP freeze lifts.
- Voice mode (orb) intentionally unbuilt (cut-first rule) — documented.
- Lighthouse / production-build checks not run (no build step exists).
- `git status` shows unrelated modifications (portfolio/, cache/) needing
  a clean commit boundary.

## 25. Dependencies
Frontend runtime: **none**. Dev/test: Playwright (+ Chromium & WebKit
binaries, local cache), pytest-less assert-style suites, backend venv
pinned in `requirements.txt` (Flask, FastAPI, scikit-learn, langdetect,
deep-translator, sentence-transformers, torch CPU, etc.).

## 26. Recommended Architecture
Keep the vanilla single-page frontend (per rule: no migration without
proven need) with its internal modules (`api · store · markdown · scroll ·
chat machine · sidebar · documents · settings · voice`), backed by the
untouched FastAPI backend. Post-FYP: split into `static/css` +
`static/js` modules served by FastAPI StaticFiles; component tests stay
Playwright-based.

## 27. Recommended Stack
Current stack (Jinja + vanilla JS/CSS + FastAPI) is the safest through
FYP freeze — zero build toolchain, already at axe-clean 0 violations and
62 green browser checks. Do NOT migrate to Next.js/React now (risk with no
measured pain). If the project grows post-FYP: Vite + Preact/Svelte only
if multi-view routing is ever needed.

## 28. Phase 1 Plan
Phase 0 found the shell already stable, so Phase 1 (stabilization) is a
**verification + hygiene pass**, not new construction:
1. Run all four suites (`make test`, `make test-browser`) and record
   actual results.
2. Clean the working tree: commit the layout-fix + suite changes on
   `feature/frontend-v2` with a single focused commit; leave
   `portfolio/` and `cache/` noise out.
3. One manual Safari + one Chrome pass on the real machine (scroll,
   drawer, keyboard-open composer) — headless can't prove this.
4. Replace `prompt()` rename with the existing modal system (small).
5. Only then proceed to Phase 2 (design tokens are already 90% in place;
   verify AA + reduce-motion, no rewrite).
