# Redesign v2 — Phase 0: verified frontend audit

**Audit date:** 10 October 2026. **Deadline:** 21 November 2026.

**Verdict: the audit is complete; the current frontend is not a green baseline.**
Both application servers start. Python/API tests pass. The existing Playwright
runner passes its first check, then aborts. A syntax error in the pre-existing
working-tree frontend prevents chat initialization and sending. These failures
are recorded rather than repaired because this phase explicitly permits no
application-code changes. A successful health response is not frontend readiness.

This audit supersedes the earlier recommendations preserved in the appendix.
Phase 1 must be **three distinct static design directions**, followed by the
user's choice—not an in-place refactor or a design-system implementation.

## 1. Scope, provenance and protected work

- Project: **Global Multilingual AI Assistant / Language Agnostic Chatbot**,
  B.Tech final-year project, The NorthCap University, Gurugram.
- Team: Bhavesh Sardana, Dakksh Sharma, Avi. Supervisor: Ms. Meghna Sharma.
- Starting branch: `feature/frontend-v2`; starting commit: `ddd30f0`.
- Created requested branch: `feature/redesign-v2`.
- Already modified on arrival: `backend/main.py`, `templates/index.html`, and
  this audit. `static/` already existed as untracked work. No staged files.
- The pre-existing backend diff adds `StaticFiles` and `/static`; it was not
  introduced or approved by this audit. It is not included in the audit commit.
- This phase changes this documentation only. `app.py`, backend/API, templates,
  existing static assets, tests, requirements, models and datasets are preserved.
  No files are deleted. Existing audit prose is preserved below, with its claims
  explicitly superseded. Runtime logs/caches can be produced by existing tests.
- Evidence refers to the **working tree**, not a clean checkout of `ddd30f0`.
  The committed template was also inspected using `git show` to identify
  behavior lost in the unfinished modular split. It was not restored or served
  in place of the user's current files.

Evidence labels used here:

| Label | Meaning |
|---|---|
| **LIVE** | Observed from the running server or Chromium during this phase |
| **TEST** | An existing test actually ran and passed; scope/mock restrictions still apply |
| **CODE** | Implementation inspected, without a successful end-to-end verification |
| **BROKEN** | Runtime failure observed, or a specific code-path defect identified |
| **GAP** | Requested behavior absent; must be implemented in the new frontend |
| **UNVERIFIED** | Historical claim or device/provider behavior not established here |

## 2. Actual stack and entry points

| Area | Actual working-tree implementation |
|---|---|
| FastAPI frontend | `GET /` → Jinja `templates/index.html` (198 lines) |
| Assets | Four CSS files and twelve JavaScript files under `static/css/`, `static/js/`; ordinary scripts/IIFEs using `window.GAIA_*`, **not ES modules** |
| Backend | `backend/main.py` (291 lines), FastAPI/SSE, port 8000 |
| Baseline | `app.py` (69 lines), Flask pivot-translation API, port 5000 |
| Language detector | `src/detection.py` (280 lines), langdetect + script/segment analysis + greeting/word heuristics |
| Frontend runtime dependencies | None; no application bundler or package.json |
| Separate portfolio | `portfolio/package.json` is an unrelated React/Vite project; no test script there |
| Test entry points | `tests/test_core.py`, `test_v2.py`, `test_code_switching.py`, `test_browser.py`; `Makefile` provides `test` and `test-browser` |

**Important baseline boundary:** Flask and FastAPI both render the same
`templates/index.html`. The present browser client calls FastAPI paths, while
Flask chat is `POST /chat`. Calling `/api/v1/chat` on Flask returned **404**;
calling `/chat` directly returned **200**. Therefore the baseline API is usable
for evaluation, but the shared browser page is not a verified Flask comparison
UI. Rewriting that shared template would affect both applications.

## 3. Execution evidence — actual output, not historical totals

### Environment and commands executed

Sandbox: Linux ARM64. The copied `venv/bin/python` points to an unavailable
macOS interpreter and returned:

```text
/usr/bin/bash: line 1: ./venv/bin/python: No such file or directory
```

The user explicitly approved an isolated test setup. Installed existing
`requirements.txt` plus pytest and Playwright **outside the repository**:

```bash
uv venv --python 3.12 /tmp/omnirush/redesign-phase0-venv
uv pip install --python /tmp/omnirush/redesign-phase0-venv/bin/python -r requirements.txt pytest playwright
/tmp/omnirush/redesign-phase0-venv/bin/python -m playwright install chromium
/tmp/omnirush/redesign-phase0-venv/bin/python -m playwright install-deps chromium
```

Versions: Python **3.12.15**, pytest **9.1.1**, Playwright **1.63.0**,
Chromium **153.0.8010.12**, Node **22.22.3** for the JS syntax check.
Declared Python requirements resolved without changing their pins. The first
package installation timed out during downloads; retry completed. Chromium
initially lacked `libglib-2.0.so.0`; `install-deps chromium` resolved that
sandbox-only prerequisite. No frontend dependency or build step was added.

An additional environment-integrity check found a platform issue in the Linux
GPU dependency selected by the existing Torch pin:

```text
uv pip check --python /tmp/omnirush/redesign-phase0-venv/bin/python
Checked 98 packages in 8ms
Found 1 incompatibility
The package `nvidia-cusparselt-cu13` was built for a different platform
```

The uv-created venv does not contain pip itself, so an initial `python -m pip
check` attempt reported `No module named pip`; the check above uses uv's
installed-package validator. A targeted smoke check still succeeded:
`torch: 2.14.1+cu130`, `CPU tensor: 6` for `torch.tensor([1,2,3]).sum()`.
The installed Linux wheel is CUDA-enabled despite the requirements comment
describing CPU inference. This is an unresolved environment-integrity warning,
not a test assertion failure and not evidence of real embedding retrieval
working. No pin was changed. A reproducible CPU-only environment should be
resolved before real RAG evaluation; macOS uses different platform wheels.

Servers started and left running for inspection:

```bash
/tmp/omnirush/redesign-phase0-venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
/tmp/omnirush/redesign-phase0-venv/bin/python -m flask --app app run --host 0.0.0.0 --port 5000
```

Tests were run using the isolated interpreter in place of the broken copied
venv. Both the pytest collection and the standalone entry points were executed:

```bash
/tmp/omnirush/redesign-phase0-venv/bin/python -m pytest -q tests
/tmp/omnirush/redesign-phase0-venv/bin/python tests/test_core.py
/tmp/omnirush/redesign-phase0-venv/bin/python tests/test_v2.py
/tmp/omnirush/redesign-phase0-venv/bin/python tests/test_code_switching.py
/tmp/omnirush/redesign-phase0-venv/bin/python tests/test_browser.py
/tmp/omnirush/redesign-phase0-venv/bin/python scripts/validate_data.py
node --check static/js/markdown.js
```

### Results

| Execution | Actual result | What it proves |
|---|---|---|
| `pytest -q tests` | **21 passed, 1 warning in 2.97s** | 10 core + 11 FastAPI test functions |
| `test_core.py` | **ALL TESTS PASSED** (10 functions) | Same core tests via standalone entry point; do not count twice |
| `test_v2.py` | **ALL V2 TESTS PASSED** (11 functions) | Same FastAPI tests via standalone entry point; do not count twice |
| `test_code_switching.py` | **28 PASS lines**, **ALL CODE-SWITCHING TESTS PASSED** | 27 nonempty examples + empty input; this runner is not collected as pytest test functions |
| `test_browser.py` | **1 check passed, then exception/exit 1** | Welcome visibility only; later checks were not executed |
| `validate_data.py` | **VALIDATION PASSED**, warning: Italian has 0 texts | Structural validity, not linguistic quality or independence from tuning |
| `node --check static/js/markdown.js` | **SyntaxError: Unexpected end of input**, exit 1 | Parse failure in the current shipped JS |

Actual pytest output:

```text
.....................                                                    [100%]
=============================== warnings summary ===============================
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
21 passed, 1 warning in 2.97s
```

The warning was reported, not silenced or addressed through an unapproved
dependency change. Expected mocked error-path logs in the v2 runner included
missing LLM configuration and `web tool failed, degrading to general: down`.

Actual Playwright failure (relevant traceback frames):

```text
PASS                                                                 welcome screen visible on fresh load
File "tests/test_browser.py", line 40, in run
    page.wait_for_selector(".msg.assistant .bubble", timeout=30000)
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
Call log:
  - waiting for locator(".msg.assistant .bubble") to be visible
```

Actual syntax-check output:

```text
static/js/markdown.js:244
else initCopyHandler();
SyntaxError: Unexpected end of input
```

These are **not** “all browser tests failed” or “79 passed.” The monolithic
runner stopped before it could produce a final assertion total. No selectors,
assertions, timeouts, or test inputs were modified.

### Live API and browser observations

- Both `/` and `/api/v1/health` returned **200** on ports 8000 and 5000.
  `/.env` returned **404** on both. No credential contents were inspected or
  printed. `/static/js/markdown.js` returned 200, so this is a parse defect,
  not an asset 404.
- FastAPI health returned `status: ok`, `llm_provider: groq`,
  `llm_model: qwen/qwen3.8-27b`, `llm_ready: true`, `languages: 7`.
  `llm_ready` checks configuration presence, not provider health or language
  quality (`backend/settings.py:38–44`).
- Real `when are my exams` request: `meta → delta → done`, route
  `campus_kb`, intent `exam_schedule`, confidence `0.8644`, model
  `tfidf+logreg (pivot)`, sources `[]`. Reply: “Check the Examination section
  of the ERP portal for the official date sheet of mid-semester and
  end-semester exams.” `done.latency_ms` was **8.9** for this one request.
- A real general request, **“Explain quantum computing in one sentence.”**,
  streamed successfully but exposed a mismatch: detected `fr`, confidence
  **0.5714**, `response_lang: fr`, actual English answer beginning “Quantum
  computing leverages the principles of quantum mechanics…”. Model:
  `groq:qwen/qwen3.8-27b`; `done.latency_ms: 2703.4`. This is a single observed
  detection/response-language inconsistency, **not a performance average,
  accuracy estimate, or French answer-quality result**.
- A server-created diagnostic conversation was deleted afterwards; response
  `{deleted: true, documents_deleted: false}`. Direct Flask `/chat` returned
  the expected English campus reply and timings.
- Chromium fresh contexts at **360, 768, 1024, 1440 × 900** each reported:
  horizontal page overflow **0 px**, composer bottom **900 px**,
  messages **0**, suggestions **0**, `typeof window.md === 'undefined'`,
  page error **“Unexpected end of input”**, and **no chat POST after Enter**.
  Desktop main x=280; smaller widths x=0. Geometry passes do not prove chat
  works or a real mobile keyboard is handled.
- Theme button changed dark → light. Settings opened and closed after its
  transition. Immediate visibility during a closing transition was not
  mistaken for an Escape failure; a follow-up with 350 ms wait confirmed it.
- New chat raised `Cannot set properties of undefined (setting 'innerHTML')`.
- Mobile drawer: sidebar z-index **35**, scrim **36**; hit-testing the New
  chat position returned `scrim`. The backdrop covers the drawer controls.
- Voice mode click set `hidden: false`, class `dialog-overlay show`, but
  computed `visibility: hidden` and `opacity: 0`—CSS expects `.open`.
- A **fake recognition/fake media-track diagnostic**, without opening a real
  mic, entered `aria-pressed: true`, language `en-IN`. Waveform remained
  `display: none`, canvas width **0**. Escape invoked recognition stop once
  but media-track stop **0** times. This demonstrates cleanup/visibility
  defects; it is not evidence of English recognition working.

Raw session logs remain at `/tmp/omnirush/phase0-{pytest,core,v2,code-switching,browser,probe,details,data-validation}.log`;
server logs at `phase0-fastapi.log` and `phase0-flask.log` in that directory.
Temporary diagnostics and a desktop screenshot also live there, outside the
project. This document contains the durable results; `/tmp` is not a release
artifact. No axe or Lighthouse run was performed in this phase; no new scores
or zero-violation claim is made.

## 4. Complete feature inventory and parity checklist

At the Phase 0 audit every checkbox was intentionally open: each is a **new-UI
acceptance gate**, not a statement that the old UI passed. Phase 3 closes F01–F06
for the shell with the evidence in [PHASE_3_SHELL.md](PHASE_3_SHELL.md), and
Phase 4 closes the transport/rendering gates documented in
[PHASE_4_CHAT.md](PHASE_4_CHAT.md), the V2 multilingual metadata slice closes
F24–F28 with the evidence in [PHASE_5_LANGUAGES.md](PHASE_5_LANGUAGES.md), and
the local conversation lifecycle, document/source slice and V2 voice-input slice
are documented in [PHASE_6_HISTORY.md](PHASE_6_HISTORY.md),
[PHASE_6_DOCUMENTS.md](PHASE_6_DOCUMENTS.md) and
[PHASE_7_VOICE_INPUT.md](PHASE_7_VOICE_INPUT.md).
The original findings remain in the table. Preserve implemented behavior and intended
behavior covered by existing tests, even where the present split broke it.
Each row must eventually receive a test/screenshot/manual-evidence reference
before Phase 11 sign-off. Shared startup blocker B1 applies to chat-dependent
rows. Paths below are relative to `static/js/` unless stated otherwise.

### Shell, welcome and composer

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F01 | Responsive sidebar + main + fixed-bottom composer; `templates/index.html`, `static/css/layout.css` | Original: LIVE old-shell geometry. Phase 3: V2 geometry + screenshots at 360/768/1024/1440; composer stays docked while main scrolls | 3 |
| [x] F02 | Desktop sidebar collapse, persisted `sideCollapsed`; `sidebar.js:131–159` | Original: CODE. Phase 3: 272px sidebar/76px rail, collapse survives reload and theme changes | 3 |
| [x] F03 | Mobile drawer, backdrop close, Escape, focus to New chat/composer; `sidebar.js:125–157` | Original: broken scrim/no trap. Phase 3: native modal, trap, backdrop/Escape, opener return, New chat→composer, resize cleanup; broader a11y audit remains Phase 10 | 3, 10 |
| [x] F04 | Backend status, offline banner and Retry health check; `main.js:15–27,63–72` | Phase 3: live health + failure/timeout/offline/retry/stale-response fixtures; reports API reachability separately from provider configuration | 3, 4 |
| [x] F05 | Multilingual greeting cycle (Hello, नमस्ते, ਸਤ ਸ੍ਰੀ ਅਕਾਲ, Hola, Bonjour, Hallo, Ciao); `chat.js:91–101` | Original: blocked. Phase 3: seven states in order, script labels, explicit pause, reduced motion/visibility handling | 3 |
| [x] F06 | Six prompts: general, coding, Hindi, translation, documents, current info; `chat.js:34–41,77–88` | Original: zero cards. Phase 3: six selectable prompts populate/focus editable draft; actual sending remains Phase 4 | 3 |
| [x] F07 | New chat, restore current conversation, heading auto-title; `chat.js:104–125,287–299` | Phase 6: New chat preserves saved records; reload/row selection restores the current conversation and the first user message supplies an 80-character title | 3, 4, 6 |
| [ ] F08 | Textarea auto-grow to 200 px, `dir=auto`, Enter send / Shift+Enter newline, Enter-send preference; `chat.js:366–375,462–465` | Phase 4: auto-grow, direction, Enter send and Shift+Enter are live; a persisted Enter-send preference remains later work | 4 |
| [x] F09 | Empty-input ignore, 4,000-character guard, count above 3,200, warning above 3,600, disable over limit | Phase 4: 4,000-character counter/guard and empty-input handling are covered by the mock browser battery | 4 |
| [x] F10 | Send/Stop state and AbortController cancellation retaining partial answer; `chat.js:304–347` | Phase 4: Stop/Escape cancellation retains partial text and blocks late deltas | 4 |
| [x] F11 | Attach entry points in header and composer, restricted file picker; `documents.js:42–63`, template line 155 | Phase 6: V2 entry points open the document panel with a PDF/DOCX/TXT/MD picker and client-side size/type guards | 6 |

### Conversation, rendering and errors

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F12 | SSE meta/delta/error/done, textContent while streaming, final markdown; `api.js:102–164`, `chat.js:304–347` | Phase 4: live stream frames are parsed and rendered with safe error recovery | 4 |
| [ ] F13 | Generating placeholder in committed template; skeleton rows in current `paintMsg()`; streaming caret CSS | Phase 4: assistant skeleton, `aria-busy` and streamed replacement are live; streaming caret styling remains later work | 4 |
| [x] F14 | Conversation switch abort + ownership guard against cross-paint | Phase 4: request ownership guards New chat, cancellation and late stream frames | 4 |
| [x] F15 | Escape-first markdown: headings 1–3, bold/italic, inline code, lists, quotes, tables, rule, HTTP(S) links | Phase 4: audited renderer is covered against hostile HTML and unsafe link protocols | 4 |
| [ ] F16 | Fenced/unclosed code, language label, syntax token colors, code copy, long-code scroll | Phase 4: fenced/unclosed code, language labels, escaped code and per-block copy are live; syntax highlighting remains a later visual enhancement | 4 |
| [ ] F17 | Distinct user/assistant bubbles, assistant timestamps and full-date tooltip, day separators | Phase 4: distinct turns, timestamps and actions are live; day separators, full-date tooltip and avatars remain later work | 4 |
| [x] F18 | Copy assistant text with clipboard fallback + toast | Phase 4: copy action and clipboard-unavailable fallback are covered | 4 |
| [x] F19 | Regenerate / Retry replaces last assistant answer | Phase 4: Retry targets its own user turn and replaces the failed assistant answer without duplicating the user turn | 4 |
| [x] F20 | Edit and resend helper exists in both committed/current frontend | Phase 4: user Edit returns the text to the composer for review and resend | 4 |
| [ ] F21 | Near-bottom-only rAF streaming follow, jump-to-latest button, restored history scroll | CODE; finalization unconditionally scrolls bottom, so “never force-scroll” is too strong | 4 |
| [x] F22 | Empty reply becomes error + Retry; interrupted stream, network, rate-limit, missing-key friendly text | Phase 4: empty, HTTP, malformed, timeout and missing-done paths become safe recoverable states | 4 |
| [x] F23 | Toast feedback and storage-full notice | Phase 6: existing copy/error toasts are joined by a non-blocking browser-history storage/quota notice, covered by the blocked-storage browser check | 4, 6, 10 |

### Languages and explainability

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F24 | Detection per message, explicit response-language instruction, mixed-script/Hinglish metadata | Phase 5: V2 preserves server `language_meta` and `response_lang` per turn, including mixed-script and code-switch fields | 5 |
| [x] F25 | Native + English language chips and confidence <0.5 dashed hint | Phase 5: user detection and assistant response chips use native + English labels; low-confidence detection gets a dashed, titled hint | 5 |
| [x] F26 | Language-switch divider between changed assistant languages | Phase 5: one divider is inserted only when the nearest completed assistant response changes language | 5 |
| [x] F27 | `dir=auto` messages/composer, Noto Indic names in font stack | Phase 5: turns and message bodies use `dir=auto`; script labels and existing Indic/RTL font fallbacks are surfaced in the turn header | 2, 5 |
| [x] F28 | Debug toggle (default off, persisted), per-reply inline cards | Phase 5: persisted Settings toggle reveals safe inline Insights with language, confidence, scripts, routing, intent, model, latency and technical state | 5 |
| [x] F29 | Sources displayed from real `done.sources`; `chat.js:199–208` | Phase 6: V2 renders safe document, web and note source cards, displays one-based chunks and preserves source metadata in history | 5, 6 |

### Documents, retrieval and web

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F30 | Upload PDF/DOCX/TXT/MD into active conversation, Processing/Ready/Failed chips | Phase 6: V2 uploads into the active server conversation and covers Processing, Ready and Failed states | 6 |
| [x] F31 | Per-chat document list, chunk counts, ready count/status | Phase 6: V2 lists the active server session's filenames/chunks and ready count on dialog open and after upload | 6 |
| [x] F32 | Clear all documents for one conversation | Phase 6: confirmed Clear all documents calls the active server-session endpoint and empties the panel | 6 |
| [x] F33 | Delete chat deletes its server document session | Phase 6: conversation deletion already uses the persisted server ID; document-source browser coverage confirms the same ID boundary | 6 |
| [x] F34 | File types, empty/oversize/parse errors, 10 MiB backend limit | Phase 6: frontend allowlist/empty/size guards align with backend 415/413/422 handling; failed upload leaves no stale Ready row | 6 |
| [ ] F35 | Document answers, cross-language retrieval path, grounding gate/not-found response, fallback note | TEST uses fake embeddings/lowered gate; real retrieval quality and PDF ingestion not newly tested | 6, 12 |
| [ ] F36 | Web route and source title/URL, empty citations on search-tool failure | TEST with mocked search/LLM; no live web success claimed | 6, 12 |
| [ ] F37 | Contextual memory follow-ups and context translation | API TEST with server-created ID; present UI's generated local IDs never create memory | 4, 11 |

### History, settings and storage

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F38 | Local history persists `{id,title,createdAt,updatedAt,messages}` and current ID in `gaia.store.v1` | Phase 6: V2-owned `gaia.history.v2` persists validated records, current ID and server ID; malformed and storage-failure paths are browser-tested; server restart remains an honest memory boundary | 6 |
| [x] F39 | Recency order; Today/Yesterday/Previous 7 days/Older groups | Phase 6: saved records sort by `updatedAt` and render under Today, Yesterday, Previous 7 days or Older group headings | 6 |
| [x] F40 | Title + message search, content-match snippets, no-results/no-history text | Phase 6: V2 sidebar search filters titles/messages, highlights matches and exposes a no-results state | 6 |
| [x] F41 | Accessible-name conversation rows, mouse/Enter/Space navigation | Phase 6: rows are buttons with separate labeled rename/export/delete controls; mobile navigation uses the existing focus-managed drawer | 6, 10 |
| [x] F42 | Rename dialog, trim, max 80 chars, Enter save, header sync | Phase 6: accessible rename dialog validates blank input, trims/caps titles and updates the active header and storage | 6 |
| [x] F43 | Per-chat Markdown export with roles, timestamps, language markers, sanitized filename | Phase 6: selected local record downloads a bounded sanitized Markdown transcript without a network request | 6 |
| [x] F44 | Delete confirmation, remove selected history, reset/open remaining chat | Phase 6: cancel is a no-op; confirmation removes local history, restores the next record or empty state, and attempts server cleanup by server ID | 6 |
| [ ] F45 | Settings from sidebar/header: dark/light/system + OS updates, Enter-send, reduce motion | LIVE opens/closes/theme button; preference controls CODE | 2, 6 |
| [x] F46 | Speech language Auto + seven locales, auto-read off by default, rate 0.75/1/1.25/1.5 | Phase 7: V2 persists Auto plus seven recognition locales; speech output/rate controls remain Phase 8 | 7, 8 |
| [ ] F47 | Privacy/about with provider/model/readiness from health | CODE; “conversations only in browser” omits server memory; “tested languages” overstates support | 6 |
| [ ] F48 | Delete all local data, reset preferences/debug, delete server data | BROKEN confirmation; code deletes only current server chat, not every known conversation; mock flag separate key remains | 6 |
| [ ] F49 | Pre-paint theme, OS and app reduced-motion preferences | CODE; body CSS disables animations, but timers/cleanup/hidden-tab behavior incomplete | 2, 10 |

### Voice and input alternatives

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [x] F50 | SpeechRecognition feature detection and unsupported mic tooltip/disabled control | Phase 7: V2 detects SpeechRecognition and disables the control with an actionable explanation when unavailable | 7 |
| [x] F51 | Tap mic, requesting permission until onstart, listening indicator/aria-pressed/placeholder | Phase 7: mocked-engine browser check covers requesting→listening, live status and aria-pressed | 7 |
| [x] F52 | Editable interim/final transcript, no auto-send, language Auto using last chat language | Phase 7: interim/final text stays editable, never auto-sends, and Auto selects the latest detected V2 user language | 7 |
| [x] F53 | Permission denied/OS block/no mic/no speech/network messages | Phase 7: mocked error state maps permission/service/audio/no-speech/network failures to actionable status | 7 |
| [x] F54 | Cmd/Ctrl+Shift+M toggles mic; Escape stops recognition | Phase 7: keyboard toggle, Escape, submit, New chat, conversation changes and hidden-tab cleanup stop recognition | 7 |
| [ ] F55 | Real AnalyserNode waveform implementation attempt | BROKEN hidden zero-width canvas; fake track never stopped; no silence timer/hold-to-talk | 7 |
| [ ] F56 | Per-reply Listen/play/pause/resume, matching voice, honest missing-voice note | CODE; two independent speech engines in chat.js and voiceOutput.js; per-message Listen uses input detection language | 8 |
| [ ] F57 | Stream-aware auto-read, clean text/skip code/read link label, configured rate | CODE; splits/queues incomplete first fragments, can skip later sentence additions; unclosed fences unsafe for speech | 8 |
| [ ] F58 | Barge-in on send/mic; Escape stops speaking in committed template | Current split loses Escape speech stop and has inconsistent queue cancellation | 7, 8 |
| [ ] F59 | Full-screen voice overlay markup, orb, transcript, End, Escape/Space handling | BROKEN invisible overlay; `vmSend()` not called; restart loop, state names and speech completion wiring incomplete | 9 |
| [ ] F60 | Visible mic privacy state; no raw audio persisted | CODE no MediaRecorder/audio storage; separate getUserMedia tracks leak and no background stop | 7, 9, 10 |

### Accessibility, security and baseline integrity

| Gate | Existing behavior and evidence | Current finding | Redesign phase |
|---|---|---|---|
| [ ] F61 | Semantic main/aside/nav/form, labelled controls, live chat log, focus styling, Escape overlays | CODE/LIVE partial; no focus trapping; role=tab controls lack full keyboard pattern; speech/live announcements incomplete | 2–10 |
| [ ] F62 | Escape-first rendering, safe external links, no frontend keys | Parser broken; raw stored `content_md` bypasses renderer; source URLs lack protocol validation and noreferrer | 4, 10 |
| [ ] F63 | Local data erasure, per-chat server cleanup, no raw audio retention | See F48/F60; no universal “all data deleted” claim until failures handled honestly | 6–10 |
| [ ] F64 | Old default frontend, Flask baseline and FastAPI API retained during side-by-side rebuild | Protected; current pre-existing failures documented; default switch requires explicit Phase 11 sign-off | All |

The committed template also contains hidden `#palette` quick-switch markup,
but no opening/search/keyboard implementation was found. It is **not** counted
as a working command palette. Avatar/Menu/Tooltip helpers and CSS likewise do
not establish used, functional components. No unused component must be ported
solely because a class/helper exists.

## 5. Real API contract and data-availability rules

Source: `backend/main.py:55–248`, `backend/rag.py`, `backend/memory.py`.
All current frontend fetch calls are located in `static/js/api.js`. Its
`API_BASE` constant is unused; URLs are hard-coded same-origin. Its
`newConversation()` exists but is never called by the current chat UI.

| Method/path | Request | Actual response / important semantics |
|---|---|---|
| `GET /api/v1/health` | None | `status`, `llm_provider`, `llm_model`, `llm_ready`, `llm_note`, `languages` (configured count, not tested support) |
| `GET /api/v1/languages` | None | Configured code→name mapping; not used by present browser |
| `GET /api/v1/intents` | None | `{campus_kb: [...], routes: [...]}`; not used by present browser |
| `POST /api/v1/conversations` | No body required | `{conversation_id}`; creates in-process memory deque |
| `POST /api/v1/chat` | JSON `{message, conversation_id}` | SSE below; creates ID only if absent/falsy; arbitrary supplied ID is not registered in memory |
| `POST /api/v1/documents` | Multipart `file`, `conversation_id` | `{conversation_id, document, chars, chunks, chunk_size, overlap, embeddings}`; additional report fields omitted in earlier audit |
| `GET /api/v1/documents/{cid}` | Path ID | `{conversation_id, documents: [{document, chunks}]}`; no excerpt/file-size field |
| `DELETE /api/v1/documents/{cid}` | Path ID | `{deleted: boolean}`; clears entire document session |
| `DELETE /api/v1/chat/{cid}` | Path ID | `{deleted: boolean, documents_deleted: boolean}`; no count |

Chat validation: whitespace-only message → **400**, message above configured
`MAX_MESSAGE_CHARS` (default 4,000) → **413**. Upload: extension outside
`.pdf/.docx/.txt/.md` → **415**; empty/over **10 × 1024 × 1024 bytes** → **413**;
processing failure → **422**. No upload-progress events, token usage, account,
history fetch, rename, edit, regenerate, individual-document deletion, STT or
TTS endpoint exists. History/rename/export/edit UI are frontend concerns.

SSE is UTF-8, `data: {JSON}\n\n`, with the event kind in `type` (not named
`event:` frames):

```text
meta:  type, conversation_id, language_meta, route, reason, response_lang
delta: type, text; campus_kb also intent, confidence, degraded
error: type, message (localized safe error; optional)
done:  type, latency_ms, model, sources
```

- Normal: meta → delta(s) → done. Failure: meta → optional delta(s) → error
  → done. `intent`, intent confidence and `degraded` are not general-LLM
  fields. Do not show placeholder confidence/intent values on those replies.
- `language_meta` really has all eleven listed fields: `language`,
  `primary_language`, `language_name`, `secondary_languages`, `code_switched`,
  `mixed_script`, `scripts`, `script`, `confidence`, `detection_reason`.
  `scripts` is a mapping of script names to shares, not an array.
- Detection confidence includes heuristic scores (`src/detection.py:234–246`)
  and script share × detection probability. Do not label it answer confidence,
  calibrated accuracy or answer quality. The displayed language name may be a
  code for a language outside the seven configured names.
- Document source: `{document, chunk, score}`. Web source: `{title, url}`.
  Fallback source may be `{note}`. **Neither source shape includes excerpts.**
  Do not fabricate excerpt expansion, web scores, page numbers, author, date,
  or source previews. Hide unavailable subcomponents.
- Upload returns an `embeddings` boolean; use it if appropriate. The list
  endpoint does not return it. An uploaded-file byte size can be labelled
  explicitly as local `File.size`, not as backend metadata. Network transfer
  progress, if implemented using XHR in the API module, must be distinguished
  from unknown server processing progress; never simulate a live percentage.
- `latency_ms` is measured inside the SSE generator. Detection occurs before
  it; it is not browser end-to-end latency or TTFT. Client timestamps are local
  message timestamps, not server message creation times.
- Route order in executable code is **translation → recency/web → campus →
  documents → general** (`router.py:104–125`). Campus/recency can bypass an
  uploaded document. Search failure keeps route `web` but returns no sources;
  route alone does not certify successful live browsing.
- **Translation metadata defect:** `router.decide()` returns the detected
  user language as `response_lang` for a translation, while generation uses
  `translate_target`. “Translate … into French” may therefore have English
  metadata but French text. Record this limitation; fixing the backend field
  needs separate, specific approval. Do not silently fabricate an output
  language or advertise verified language-correct speech for this case.
- Server memory and documents are in-process and vanish on restart. Browser
  history persists but does not reconstruct server context through this API.
  This affects live-demo follow-ups after restart and must be explained.

## 6. Root-cause register and phase ownership

| ID | Finding / evidence | Required handling |
|---|---|---|
| B1 | `markdown.js` outer `highlight()` starts at line 24 and is left unclosed, with duplicated nested implementation. Parser rejects the entire script. `chat.js` waits forever for md/esc/speechText, so send/card handlers never bind. | New Phase 4 renderer must parse, load and execute; preserve escape-first approach and test XSS/code/quotes/copy. Any repair to old frontend requires lifting Phase 0's no-code boundary. |
| B2 | Chat uses unbound `renderSidebar`, `refreshDocs`, `closeDrawer`, `setOffline`; sidebar deletion uses unbound `api`/`feed`/`welcome`; docs/input exports missing. | Explicit ES-module imports/exports in new app; boot smoke test and no console errors. A brace-only fix would be insufficient. |
| B3 | UI generates local IDs, never calls conversation creation; `memory.append()` accepts only registered IDs. | New API/store lifecycle must use server-issued IDs. Test real multi-turn context and honest server-restart behavior. |
| B4 | Settings/sidebar confirm handler calls `m.close()` (resolves false through onClose), then resolves true too late. Delete all only targets current server ID. | Functional confirmation and all-known-chat cleanup, with visible partial-failure state; do not clear IDs before cleanup is accounted for. |
| B5 | Current language divider passes over identical nearest language; `store.lastLang = l` does not update `store.data.lastLang`. | Consecutive-language semantics and persisted last-detected input; deterministic EN→HI→HI regression. |
| B6 | Two speech queues; incomplete sentence queued; Escape speech handler lost; response_lang ignored for per-message Listen. | One speech output controller, tested streaming boundaries, response language and cancellation. |
| B7 | Separate media tracks neither retained nor stopped; permission-request cancellation and tab-hidden shutdown absent; waveform display:none. | One lifecycle owner with track.stop(), pending-request races, fake-stream tests and real Mac verification. |
| B8 | Voice overlay `.show` versus `.open`; phase names listening/thinking/speaking differ from CSS listen/think/speak; `vmSend` unused; 30-second timeout substitutes for completion. | Phase 9 is new functional work; no claim of an existing end-to-end voice loop. |
| B9 | Scrim above drawer; history actions hidden on touch; no focus traps; toasts lack status role and rely on animationend; `.tab-hidden` has no pause rule. | New accessible shell/components and motion lifecycle. |
| B10 | Regex quote matching runs after escaping; source URL protocols unvalidated; local stored HTML rendered directly; no EOF/done or request timeout discipline. | Phase 4/10 security and streaming hardening without weakening coverage. |
| B11 | English→French live detection mismatch and translation response_lang inconsistency. | Carry into limitations and evaluation; detector/backend changes need specific approval. |
| B12 | Shared Flask template assumes FastAPI paths; baseline `/chat` is healthy but shared UI not baseline-compatible. | Preserve baseline source and evaluate via its real API. Do not claim frontend baseline parity. |

## 7. Earlier audit: verified versus claimed

The appendix is the **pre-existing working-tree audit**, not newly approved
design advice. `docs/TESTING.md`, `README.md` and `docs/PROJECT_AUDIT.md` contain
additional historical claims. Their statements do not override current runs.

| Earlier statement | Status now | Evidence / correction |
|---|---|---|
| Single 1,502-line template; API client inline | **Stale** | 198-line template loads CSS and JS files; API already split into `api.js` |
| 108 total = 21 pytest + 79 browser + 26 code-switching; all green | **Contradicted** | Arithmetic itself is inconsistent; 21 pytest pass, 28 detection checks pass, browser aborts after 1 pass |
| Six breakpoints/browser layout verified | **Partially rechecked** | Four required widths measured in Chromium; no WebKit/real Safari/mobile-keyboard pass here |
| Stable, performant, 92 KB/one request/120 ms DCL | **Not current evidence** | Current page loads 16 external CSS/JS assets; no equivalent fresh performance benchmark |
| WCAG AA tokens / zero axe violations in both themes | **Not established; token claim contradicted** | No current axe run. WCAG luminance calculations below fail 4.5:1 for small text |
| Multilingual works in seven languages | **Overbroad** | Specific detection regression samples pass; one live mismatch observed; answer quality/voice remain unverified |
| Code-switch indicator exists | **Partial** | Only debug-card text; no normal per-reply code-switch indicator |
| Debug slide-over shows all metadata | **Incorrect** | Inline debug cards; omits full language object, response_lang, source scores |
| Upload client and server validate ≤10 MB | **Partial** | Server validates; browser only accept filter, no size/type preflight; no drag/drop/progress |
| Sources have chunk scores in UI | **Incorrect** | Backend includes score; present source renderer omits it |
| Memory follow-ups work in UI | **Incorrect by lifecycle inspection** | Client IDs are not registered server conversations |
| Complete stream-aware speech output | **Unverified/defective** | Partial sentence queue, duplicate controllers and incorrect language selection identified |
| Voice mode implemented, needs polish | **Incorrect** | Markup/controller attempt exists; invisible and no send-loop connection |
| No waveform implementation | **Stale** | Code exists, but canvas hidden and track cleanup broken |
| Avatar/component library absent | **Partial** | Helpers/CSS now exist, largely unused by rendered app; no coherent accessible component system |
| No voice device testing | **Still true** | No real Mac microphone/speaker run; mock events cannot certify voice support |
| All local data deletion works | **Incorrect** | Confirmation resolution bug and incomplete server cleanup |
| Framer Motion / VITE_MOCK_API recommended | **Superseded** | CSS + WAAPI, `?mock=1`, no runtime dependencies or build step |
| Refactor old UI in place over 11 phases | **Superseded** | Ground-up side-by-side redesign, user's phases 0–13 and stops govern |
| Old project audit says no LLM/RAG/versioned API/metadata | **Historical baseline snapshot** | Those capabilities now exist in FastAPI; do not treat snapshot as current architecture |

Contrast spot checks from actual `static/css/tokens.css`, calculated with
WCAG relative luminance and `(Llighter + .05)/(Ldarker + .05)`:

| Foreground / background | Ratio | Normal-size AA (4.5:1) |
|---|---|---|
| Dark subtle `#6b7383` / surface `#13151a` | **3.83:1** | Fail |
| Light subtle `#7a8290` / white | **3.87:1** | Fail |
| Light success `#16a34a` / white | **3.30:1** | Fail |
| Light warning `#ca8a04` / white | **2.94:1** | Fail |

These are formula-based token checks, not an axe report or a full contrast
table. Phase 2 must calculate the new design's actual foreground/background
pairings, including chips, hover/focus and disabled explanatory text.

### Honest language and evaluation status

- English, Hindi, Punjabi, German, Spanish, French and Italian each have at
  least one passing detection example in the current regression runner.
  This verifies those examples only. The runner includes selected Hinglish,
  mixed-script and technical-word cases, not a held-out accuracy evaluation.
- Punjabi detection samples pass. **Punjabi answer quality, microphone
  recognition and installed speech voices were not tested on a real device**;
  do not infer them from Gurmukhi rendering or the locale selector.
- Existing `data/test_multilingual.json` declares AI-drafted non-English
  columns awaiting fluent-speaker review. `_verified`: English true,
  Hindi/Punjabi/Spanish/French/German false. Italian has no evaluation rows.
- Data validation reported **16 intents / 320 training examples** and
  **30 queries / 180 texts across six languages**, with the Italian warning.
  These counts are not answer-quality or general-assistant coverage.
- Existing detection/e2e/threshold scripts and historical results are not
  freshly rerun evaluation metrics. `eval_e2e.py --baseline` is the documented
  **no-pivot ablation**, not the requested original Flask versus FastAPI
  assistant comparison. Phase 12 needs that distinct comparison.
- Native/fluent authorship cannot be claimed for an AI-written test set.
  Phase 12 must obtain and record actual speaker authorship/review, separate
  held-out data from tuning, define human quality/groundedness rubrics, and
  save real per-language/error/latency/RAG measurements.
- `docs/MODELS.md` and `docs/DATA.md` list some sources/licences but mix old
  baseline statements with current models. LLM/embedding model revision and
  licence, and dataset provenance/licensing still need explicit verification.
- The current voice matrix contains “NOT TESTED” and speculative notes rather
  than the requested empty seven-language × Safari/Chrome form. Preserve it
  now; Phase 13 will supply an empty fillable matrix with no inferred results.

## 8. Stack decision and proposed side-by-side structure

**Recommendation for approval: modern vanilla HTML/CSS and native JavaScript
ES modules; CSS + Web Animations API; zero frontend runtime dependencies;
no bundler.** This matches the user's default. The observed problems are
specific parsing/lifecycle/interface bugs in an unfinished split, not evidence
that adding a framework reduces delivery risk. Native imports make missing
module interfaces explicit; one API module and separate input/output state
controllers make the critical streaming/voice paths testable.

- Added application dependencies: **none**. Build step: **none**.
- Test-only pytest/Playwright/Chromium environment was separately approved
  and installed for this phase. Future axe-core/Lighthouse tooling needs a
  stated purpose and approval before addition; no runtime inclusion.
- Typography/font licensing and actual font files will be selected after the
  visual-direction choice; named fallbacks alone do not guarantee glyphs.
- Preserve the existing escape-first Markdown approach, but do not copy the
  broken split or claim it is safe without executable security tests.
- Do not import anything from the unrelated `portfolio/` dependency tree.

Proposed structure (not created in Phase 0):

```text
templates/index.html                  existing frontend, preserved
static/css/, static/js/                existing frontend assets, preserved
backend/, app.py                       existing servers, preserved
docs/design-explorations/
  direction-a.html                     self-contained: welcome/chat/voice
  direction-b.html                     self-contained: welcome/chat/voice
  direction-c.html                     self-contained: welcome/chat/voice
static/v2/
  index.html                          new standalone screen/shell
  components.html                     only components actually used by app
  config.js                           public API URL and one speech-locale map
  css/{tokens,base,components,layout,motion}.css
  js/
    main.js                           explicit module boot
    api.js                            only live HTTP/SSE/upload calls
    mock.js                           delayed deterministic SSE fixtures
    store.js                          versioned state/storage lifecycle
    markdown.js                       escape-first renderer/tokenizer
    chat.js                           stream ownership, actions, scrolling
    history.js, documents.js, settings.js, insights.js
    speech/{input,output,text,voice-mode}.js
    ui/                               used dialog/drawer/toast/menu helpers
  assets/{icons,fonts,brand}/            SVG sprite/font files/licence notices
tests/test_redesign_v2_browser.py       new UI equivalent coverage + new flows
tests/frontend_v2/                    meaningful speech/helper unit tests
docs/{DESIGN_SYSTEM,LIMITATIONS,DEMO_SCRIPT,VOICE_TEST_MATRIX}.md
docs/screenshots/                     release evidence, both themes/sizes
evaluation/                           Phase 12 harness + held-out speaker data
```

**Route plan without a backend edit:** serve `static/` with Python's built-in
HTTP server on the already CORS-allowed port **5173**; new route
`http://localhost:5173/v2/`, public API config `http://localhost:8000`.
The new V2 application is now the FastAPI root at `http://localhost:8000/`;
the old application is comparison-only at `/legacy`, and Flask remains :5000
only when explicitly started in legacy mode.
Only the public static directory is served by this preview command. The FastAPI
server also exposes the same V2 page at `/` and keeps `/static/v2/index.html`
as its direct asset entry point.

`?mock=1` will select deterministic, delayed **clearly labelled simulated**
frames in `api.js` and work with the backend off. Mock results must never be
presented as language/voice/evaluation evidence. Current mock mode exists but
has loose `?mock` detection, random document counts, constant conversation ID,
an abort path that can leave a reader pending, and no reliable visible banner.
Those defects are not an approved mock contract.

New storage key: `gaia.redesign.v2`; preserve `gaia.store.v1` while comparing.
Any import must copy legacy data without mutating it, discard cached HTML,
validate structure and explain server-memory limitations. “Delete all my data”
must specify and actually clean its scope, attempt cleanup for every known
server ID, and report failures rather than silently promising completion.

## 9. New requirements not yet provided by the current product

The inventory covers old behavior; these are additional required outcomes:

| Area | Required addition / validation | Phase |
|---|---|---|
| Design choice | Three named, genuinely different directions, each with welcome, switched-language chat and voice screen; palette, pairing, shape/motion rationale | 1 |
| Design system | Deliberate light/dark, measured AA, tokens, one icon family, brand assets; only used components | 2 |
| Shell/welcome | Purpose-designed tablet/mobile, language presence, language/script visual identity, hidden-tab pause | 3 |
| Chat | Real thinking/streaming transitions, avatars, usable user actions, timeout/incomplete-stream handling | 4 |
| Multilingual | Normal code-switch chip, header language transition, script labels, RTL/Indic rendering, full last-reply Insights | 5 |
| Documents/history | Drag/drop, truthful transfer/processing state, score display, search highlighting, reliable data deletion | 6 |
| Listen | Pending-permission cancellation, processing/error states, final+interim text, silence cutoff, mobile hold, optional auto-send off | 7 |
| Speak | One controller; response_lang selection subject to documented backend limitation, voice/pitch settings, per-message equalizer, complete-sentence queues, robust barge-in | 8 |
| Voice mode | Actual listen→send→stream→speak→listen loop, audio-driven visual, language presence, accessible End, reduced-motion state label | 9 (first cut if needed) |
| A11y/motion/security | Focus traps, keyboard parity, polite announcements, transformed/opacity-only choreography, real 60 fps review, axe all five views × both themes, Lighthouse real scores | 10 |
| Release parity | All F01–F64 checked with evidence; screenshots key screens × 360/1440 × both themes; user signs off before default switch | 11 |
| Evaluation | Speaker-authored/reviewed held-out test set; detection, consistency, quality, RAG, performance, baseline comparison, error analysis | 12 |
| Final documentation | Mac README/architecture/setup/limits, exact model/dataset provenance/licences, empty voice matrix, 3-minute rehearsed demo and offline failure | 13 |

Follow the user's 0–13 phase sequence and stop after each phase. Each is capped
at roughly two working days; split large work within its numbered phase before
starting, rather than silently borrowing time. Phase 4, 7, 8, 10 and 12 are the
likely split candidates (e.g. speech capture/lifecycle then rendering/errors/
tests; evaluation harness then actual speaker review/results). No completion
date is guaranteed by multiplying unverified estimates. Cut order remains
Phase 9, then extra Phase 10 choreography. Core includes Phase 12.

## 10. Test migration policy and release gates

- Retain old suite for the old route; introduce an equivalent suite targeting
  the new route. Record each selector migration in the phase that implements
  the corresponding screen. Current examples of stale selectors:
  `.msg.assistant .bubble` versus `.msg--assistant .msg__bubble`, `#greet`
  versus `#welcome-greeting`, `#cards .card` versus `.welcome__card`, and
  `.modal/.show` versus `.dialog/.open`. **Selector replacement alone does
  not fix the startup failure.** No changes were made to tests in Phase 0.
- Replace reliance on old globals (`S`, `openConv`, `streaming`) with behavior
  through accessible controls or explicit injected test adapters. Preserve
  history restoration, switch-abort, Retry replacement, scroll ownership,
  XSS, language, document and speech assertions.
- Existing browser suite calls a live LLM for a code block despite describing
  itself as deterministic. Add controlled SSE coverage alongside live smoke
  tests, not a silent mock substitute for provider behavior.
- The existing “mic unsupported” else branch records PASS without exercising
  that path; the “final transcript” check includes a tautological `count >= 0`;
  the empty-reply test mutates an error state itself. Preserve intended
  requirements and strengthen these checks; do not report those paths as
  newly verified when execution never reached them.
- Existing v2 RAG test uses `_FakeEmbed` and lowers the gate to 0.05. It checks
  plumbing/isolation, not genuine cross-language embedding quality. Its
  German path only asserts routing. Also, some v2 non-English routing can
  consult the MT cache/network even though the suite calls itself “offline.”
- New tests: deterministic chunks/TTFT state/cancellation/EOF/timeouts,
  language-switch/no-repeat/code-switch/RTL, four required widths, history,
  themes, offline, reduced motion, real fake-media lifecycle, permission/no
  speech/interim/final, stream-safe Markdown speech, correct/missing voice,
  barge-in, voice-loop shutdown and no background microphone.
- axe: welcome, chat, settings, Insights, voice mode in both themes. Screenshots:
  every key screen at 360 and 1440 in both themes. Lighthouse on a production-
  like no-debug run; report environment and real scores, not targets as results.
- Real Chrome/Safari MacBook Air voice verification remains human work with
  empty result cells until tested. Linux Chromium/headless mocks cannot
  certify macOS voice availability, speech accuracy, Safari or mobile keyboard.
- The demo's PDF/web/memory/voice/safety/offline steps need an actual timed
  rehearsal. No live harmful-request result, PDF grounding quality, complete
  seven-language answer-quality pass or three-minute timing is claimed here.

## 11. macOS: exact run and verification instructions

Run these in **Terminal on the MacBook Air**, not in `portfolio/`.

### Start the existing assistant

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
pwd
source venv/bin/activate
python --version
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000/**. At this Phase 0 snapshot, expect the existing
sidebar, Hello welcome and composer; missing prompt cards/nonfunctional chat
are documented B1, not a redesign preview. Theme and settings still operate.
Open **http://localhost:8000/api/v1/health** to verify backend readiness fields.
The redesign route does not exist yet.

### Run the baseline (second Terminal)

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python app.py
```

Baseline URL: **http://localhost:5000/**. Its shared frontend limitation is
documented above. Verify the actual comparison API explicitly:

```bash
curl -sS http://localhost:5000/chat \
  -H 'Content-Type: application/json' \
  --data '{"message":"when are my exams"}'
```

### Run tests (third Terminal, keep FastAPI running)

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python -m pytest -q tests
python tests/test_core.py
python tests/test_v2.py
python tests/test_code_switching.py
python tests/test_browser.py
python scripts/validate_data.py
```

The standalone scripts also match `make test` / `make test-browser` when
`venv/bin/python` is valid. The Python and detector runs should be compared
with the actual output above; the current browser run is expected to stop at
the documented failure. Provider availability can change live checks.

### Common failures

| Problem | Exact action |
|---|---|
| Wrong folder / cannot import backend / model or data missing | `cd /Users/bhaveshsardana/language_agnostic_chatbot`, then `pwd`; `ls backend templates static data models` must show this project |
| Venv not active | `source /Users/bhaveshsardana/language_agnostic_chatbot/venv/bin/activate`; or use `./venv/bin/python` explicitly from the root |
| Existing venv is broken even on Mac | Preserve it. From the project root: `python3.12 -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt`; use the `python ...` commands above, not Makefile's old venv path. Verify a Python 3.12 interpreter is installed first |
| Missing application package | With the chosen venv active: `python -m pip install -r requirements.txt` |
| Missing approved test tooling/browser | `python -m pip install pytest==9.1.1 playwright==1.63.0`, then `python -m playwright install chromium`. Linux `install-deps` is not a macOS command |
| Port 8000 already in use | `lsof -nP -iTCP:8000 -sTCP:LISTEN`; reuse a correct running instance or Ctrl+C its owning Terminal. Do not kill an unknown process. Preview fallback: `python -m uvicorn backend.main:app --port 8001` → http://localhost:8001/; existing browser runner still hard-codes 8000 |
| Port 5000 already in use | `lsof -nP -iTCP:5000 -sTCP:LISTEN`; identify the owner (macOS AirPlay can use it), stop your prior server or resolve that conflict before baseline evaluation |
| LLM not configured | Check health `llm_ready`/`llm_note`; configure existing `.env` locally using the documented variables in `.env.example`. Do not paste keys into frontend code or overwrite an existing `.env` |
| Missing model artifact on another checkout | Confirm `models/intent_classifier.joblib` exists; it is ignored by Git. Preserve supplied artifacts. Training is a separate, intentional step (`python scripts/train.py`), not an automatic audit “fix” |
| Mic unavailable or permission denied | Use **localhost or HTTPS**, Chrome/Safari site microphone permissions and macOS Privacy & Security → Microphone. A browser API/locale option is not proof that a language works; fill the real-device matrix later |

Read this audit with:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
open docs/FRONTEND_AUDIT.md
```

**Approval gate:** review the vanilla/no-bundler stack, separate preview-route
plan, parity inventory and red baseline findings. Reply **continue** to start
Phase 1's three static visual directions. Choosing a design and authorizing a
default-route switch remain separate later decisions. Backend/detector
defects are recorded for specific approval; this phase makes no such changes.

---

<details>
<summary>Earlier working-tree audit — preserved historical text, superseded by the verified audit above</summary>

## Phase 0 — Frontend Audit & Upgrade Recommendation (earlier draft)

**Date:** 10 Oct 2026
**Project:** Global Multilingual AI Assistant (GAIA)
**Goal:** Upgrade to a premium, modern AI chat product with excellent UI/UX, great animations, and voice (listen + speak)
**Deadline:** 21 Nov 2026 (3-minute live demo)
**Backend:** FastAPI `backend/main.py` on :8000 — **DO NOT MODIFY**

---

## 1. Current Stack (Verified)

| Layer | Technology | Location |
|-------|------------|----------|
| **Frontend** | Single Jinja2 template `templates/index.html` (1,502 lines) — vanilla JS/CSS, zero runtime deps, no bundler | Served by FastAPI at `GET /` |
| **Backend** | FastAPI `backend/main.py` (289 lines) — SSE chat, RAG, documents, memory | Port 8000 |
| **FYP Baseline** | Flask `app.py` — pivot MT + intent classifier | Port 5000 (untouched) |
| **NLP** | `src/detection.py` (280 lines) — segment+lexicon code-switching detector; 26-case suite | 7 tested languages |
| **Tests** | 108 total: 21 pytest + 79 Playwright + 26 code-switching | All green |
| **Accessibility** | axe-core 4.10.2 — **0 violations** (welcome, chat, settings) | Both themes |
| **Design System** | CSS variables in `index.html:15-44` — spacing, type, motion, z-index, AA-audited tokens | Dark + Light |

---

## 2. What Already Works (No Rework Needed)

| Feature | Status | Evidence |
|---------|--------|----------|
| **Layout** | ✅ Fixed & verified | Grid shell, sidebar drawer, mobile responsive at 6 breakpoints |
| **Chat streaming** | ✅ SSE + textContent updates | No layout jump, AbortController stop, conversation-switch abort |
| **Markdown** | ✅ Escape-first, XSS-safe | Headings, lists, tables, code blocks w/ copy, custom `hl()` tokenizer |
| **Auto-scroll** | ✅ Smart (stops when user scrolls up) | rAF-throttled, jump pill |
| **Multilingual UX** | ✅ Language chip + switch divider | 7 tested langs, `dir="auto"`, Noto fallbacks, low-confidence hint |
| **RAG/Documents** | ✅ Upload, sources, honest not-found | Per-conversation, 10 MB limit, chunk scores |
| **History** | ✅ localStorage, search, rename, delete, export | Grouped by day, content-match snippets |
| **Settings** | ✅ Theme (dark/light/system), Enter-send, Reduce motion, Speech lang, Auto-read, Rate | Persisted |
| **Voice Input** | ✅ Browser SpeechRecognition | States: idle/requesting/listening, interim transcript, BCP-47 selector, error map |
| **Voice Output** | ✅ Browser SpeechSynthesis | Language-matched voices, sentence-queued stream-aware, pause/resume, barge-in, honest no-voice fallback |
| **Debug drawer** | ✅ Slide-over, shows all backend metadata | language_meta, route, intent, latency, model, sources |
| **Offline/Error states** | ✅ Banner + retry, friendly error messages | Rate limit, API key missing, network, empty response |

---

## 3. Gaps vs. Target Spec (Premium Upgrade)

| Target Feature | Current | Gap | Effort |
|----------------|---------|-----|--------|
| **Avatar on bubbles** | ❌ | Add user/assistant avatars | Low |
| **Timestamp on hover** | ✅ (message-level) | Move to bubble hover, finer format | Low |
| **Thinking skeleton/shimmer** | ⚠️ (pulse only) | Full skeleton before first token | Medium |
| **Send/Stop morph** | ✅ (scale morph) | Polish spring, better icon swap | Low |
| **Welcome greeting animation** | ✅ (crossfade) | Add prompt-card stagger (done) | ✅ |
| **Subtle animated background** | ❌ | Canvas/WebGL or CSS gradient mesh | Medium |
| **Dialog/toast scale-fade** | ✅ (pop + fade) | Verify spring timing | Low |
| **Voice Mode (full-screen orb)** | ✅ **IMPLEMENTED** (lines 362-383, 1401-1476) | **Already done** — needs polish & audio-level-driven orb | Medium |
| **Mic waveform (Web Audio)** | ❌ | Real-time AnalyserNode bars in composer + voice mode | Medium |
| **Speaker equalizer on message** | ⚠️ (orb only) | Per-message equalizer on Listen button | Medium |
| **Flash-free theme transition** | ✅ (pre-paint script) | Verify sub-100ms | Low |
| **Component library** | ❌ | Reusable Button, Input, Dialog, Drawer, Tooltip, Chip, Skeleton, Avatar, DropdownMenu, Tabs | High |
| **API client file** | ✅ (inline `api` object) | Extract to `static/js/api.js` + mock mode | Medium |
| **Lighthouse scores** | ❌ Not run | Run on production build | Low |
| **Voice test matrix** | ❌ All NOT TESTED | Fill via manual 15-min protocol | Manual |

---

## 4. API Contract (Backend — Source of Truth)

**Endpoints used by frontend:**

| Method | Path | Request | Response (SSE frames) |
|--------|------|---------|----------------------|
| GET | `/api/v1/health` | — | `{status, llm_provider, llm_model, llm_ready, llm_note, languages}` |
| POST | `/api/v1/conversations` | — | `{conversation_id}` |
| POST | `/api/v1/chat` | `{message, conversation_id}` | `meta` → `delta*` → `error?` → `done` |
| POST | `/api/v1/documents` | `multipart: file, conversation_id` | `{conversation_id, chunks, document}` |
| GET | `/api/v1/documents/{cid}` | — | `{conversation_id, documents[{document, chunks}]}` |
| DELETE | `/api/v1/documents/{cid}` | — | `{deleted}` |
| DELETE | `/api/v1/chat/{cid}` | — | `{deleted, documents_deleted}` |

**SSE Frame Types (from `backend/main.py:138-233`):**

```json
// meta (first frame)
{ "type": "meta", "conversation_id": "abc", "language_meta": {...}, "route": "general|campus_kb|translate|document|web", "reason": "...", "response_lang": "en" }

// delta (repeated)
{ "type": "delta", "text": "chunk", "intent": "exam_schedule", "confidence": 0.54 }

// error (optional)
{ "type": "error", "message": "localized safe message" }

// done (last)
{ "type": "done", "latency_ms": 1234.5, "model": "groq:qwen/qwen3.8-27b", "sources": [...] }
```

**language_meta object (from `src/detection.py:268-279`):**

```json
{
  "language": "hi",
  "primary_language": "hi",
  "language_name": "Hindi",
  "secondary_languages": ["en"],
  "code_switched": true,
  "mixed_script": true,
  "scripts": {"Deva": 0.65, "Latn": 0.35},
  "script": "Deva",
  "confidence": 0.78,
  "detection_reason": "segment: Deva share=0.65 prob=0.89 + romanized-indic markers [...]"
}
```

---

## 5. Voice Capability Reality Check

| Feature | Implementation | Browser API | Backend Needed? |
|---------|----------------|-------------|-----------------|
| **Speech Input** | ✅ Done | `SpeechRecognition` / `webkitSpeechRecognition` | No — browser only |
| **Speech Output** | ✅ Done | `SpeechSynthesis` | No — browser only |
| **Live waveform** | ❌ | `AudioContext` + `AnalyserNode` | No |
| **Auto-language detection (voice)** | ❌ | Not supported by browser API | No — use last chat language |
| **Voice Mode orb** | ✅ Done (basic) | CSS animations + JS state machine | No |

**Optional backend endpoint that would improve voice:**
`POST /api/v1/stt` — server-side STT (Whisper/faster-whisper) for better accuracy, especially for Hindi/Punjabi. Currently browser STT quality varies by OS/locale.

---

## 6. Recommended Upgrade Architecture

### 6.1 Stack Decision: **Stay Vanilla + Modular Split**

**Rationale:**
- Current codebase is **stable, tested, accessible, and performant** (92 KB, 120ms DCL, 0 axe violations)
- Migration to Next.js/React adds **build toolchain, bundle size, hydration complexity, and regression risk** with **zero measured pain** in current stack
- Deadline is 6 weeks — **refactor in place** is safer than rewrite
- Post-FYP: Vite + Preact/Svelte only if multi-view routing becomes necessary

### 6.2 Structure After Phase 1 (Design Tokens + Component Split)

```
/language_agnostic_chatbot
├── backend/main.py              # UNCHANGED
├── templates/index.html         # Thin shell — loads CSS/JS modules
├── static/
│   ├── css/
│   │   ├── tokens.css           # Design tokens (CSS variables)
│   │   ├── components.css       # Reusable component styles
│   │   ├── layout.css           # App shell, sidebar, chat, composer
│   │   └── motion.css           # Keyframes, transitions, reduced-motion
│   ├── js/
│   │   ├── api.js               # Single API client + mock mode (env flag)
│   │   ├── store.js             # localStorage wrapper
│   │   ├── markdown.js          # md() + hl() (escape-first)
│   │   ├── chat.js              # Chat machine: streaming, scroll, actions
│   │   ├── sidebar.js           # History, search, CRUD
│   │   ├── voice.js             # Input + Output engines
│   │   ├── voiceMode.js         # Full-screen orb overlay
│   │   ├── settings.js          # Settings modal + persistence
│   │   ├── components/          # Reusable UI components
│   │   │   ├── Button.js
│   │   │   ├── IconButton.js
│   │   │   ├── Input.js
│   │   │   ├── Textarea.js
│   │   │   ├── Dialog.js
│   │   │   ├── Drawer.js
│   │   │   ├── Tooltip.js
│   │   │   ├── Toast.js
│   │   │   ├── Chip.js
│   │   │   ├── Skeleton.js
│   │   │   ├── Avatar.js
│   │   │   ├── DropdownMenu.js
│   │   │   └── Tabs.js
│   │   └── main.js              # Boot: theme, shell, event wiring
│   └── icons/                   # Inline SVG sprite or individual files
├── tests/
│   ├── test_browser.py          # Playwright E2E (extend for new features)
│   └── test_components/         # Component unit tests (mock speech APIs)
├── docs/
│   ├── FRONTEND_AUDIT.md        # This file
│   ├── DESIGN_SYSTEM.md         # Token inventory + contrast tables
│   ├── VOICE_TEST_MATRIX.md     # Manual checklist (fill with real results)
│   └── DEMO_SCRIPT.md           # 3-minute demo flow
└── requirements.txt             # Python deps only
```

---

## 7. Phase Plan (11 Phases — Stop After Each)

| Phase | Focus | Deliverable | Approx. Time |
|-------|-------|-------------|--------------|
| **0** | Audit & Recommendation | `docs/FRONTEND_AUDIT.md` (this) | ✅ Done |
| **1** | Design Tokens + Base Components + API Client + Component Gallery | `static/css/tokens.css`, `static/js/api.js` + mock mode, `gallery.html` | 3 days |
| **2** | App Shell: Layout, Sidebar, Header, Theme Toggle, Welcome Screen | Responsive shell, greeting animation, prompt cards | 3 days |
| **3** | Chat Core: Composer, Message List, Streaming, Markdown, Code, Actions | Smooth streaming, thinking skeleton, copy/regen/edit/stop, auto-scroll | 4 days |
| **4** | Multilingual UX: Language Chip, Switch Divider, Script Fonts, RTL, Debug Drawer | Chip pop-in, divider animation, Noto fallbacks, spring drawer | 3 days |
| **5** | History & Settings: localStorage, Rename, Delete, Search, Settings Panel | Full CRUD, theme sync, speech settings, delete-all | 2 days |
| **6** | Voice Input: Mic Button, States, Waveform, Interim Transcript, Speech-Lang Selector | Mic pulse + waveform, live transcript in composer, all error states | 3 days |
| **7** | Voice Output: Speaker Buttons, Auto-Read, Language-Matched Voices, Sentence Queue | Listen button, global toggle, missing-voice toast, barge-in, controls | 3 days |
| **8** | Voice Mode Overlay: Animated Orb (Listen→Think→Speak), Live Transcript | Orb driven by real audio levels, reduced-motion fallback | 3 days |
| **9** | Motion Polish: Timings, Micro-interactions, 60 fps Verify | Tuned easings, spring drawers, hover/press states, reduced-motion | 2 days |
| **10** | A11y + Error States + Performance + Security Review | axe-clean, Lighthouse, error state coverage, sanitization audit | 2 days |
| **11** | Tests + Lighthouse + README + Voice Matrix + Demo Script | All suites green, scores recorded, 3-min demo rehearsed | 2 days |

**Total:** ~30 working days (6 weeks) — fits 21 Nov deadline with 1-week buffer.

**Cut order if time runs short:** Phase 8 → Phase 9 extra animations → Phase 1 gallery.
**Core phases that must ship:** 3, 4, 6, 7.

---

## 8. Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| **CSS** | CSS variables + modular files (no Tailwind) | Already 90% tokenized; Tailwind adds build step |
| **Animation** | CSS transitions/keyframes + Framer Motion only for complex orchestration (orb) | 95% doable in CSS; Framer only for spring-physics orb |
| **Markdown** | Keep custom `md()` + `hl()` (escape-first, zero deps) | Already XSS-safe, tested, handles fenced blocks |
| **State** | Module singletons + localStorage (no Zustand) | Current store is simple, typed, persisted |
| **Icons** | Inline SVG (current) → SVG sprite in Phase 1 | Zero dep, tree-shakeable, styleable via CSS |
| **Mock Mode** | `VITE_MOCK_API=1` → `api.js` returns delayed fake SSE | UI works offline for design/dev; one env flag |
| **Fonts** | System stack + Noto Sans Devanagari/Gurmukhi (current) | Already verified for Indic scripts; add Arabic/CJK/Cyrillic fallbacks |

---

## 9. Questions for Approval

1. **Stack confirmation:** Proceed with vanilla modular split (no Next.js/React)?
2. **Voice Mode priority:** Keep Phase 8 (orb) or cut to save time?
3. **Mock mode:** Add `VITE_MOCK_API` env flag for offline UI development?
4. **Component gallery:** Build a `gallery.html` for visual regression / component docs?
5. **Fonts:** Add Noto Sans Arabic, CJK, Cyrillic to the stack for full script coverage?

---

**Awaiting your "continue" to begin Phase 1.**

</details>
