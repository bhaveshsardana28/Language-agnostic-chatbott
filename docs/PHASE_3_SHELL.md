# Phase 3 — Common Ground application shell

**Completed 11 October 2026, ready for phase approval.** Entry:
`http://localhost:8000/static/v2/index.html`. The Phase 2 workbench remains at
`/static/v2/components.html` and the existing assistant remains at `/`.

## Delivered

- Full-height shell with a separately scrolling main workspace and a docked
  bottom composer. Safe-area padding and `100dvh` support are in the layout.
- 272px desktop sidebar, collapsible to a 76px icon rail. Its choice is restored
  before paint and saved as `sideCollapsed` in `gaia.redesign.v2`.
- Below 1024px the same sidebar DOM moves into a native modal drawer. There is
  no duplicate navigation tree or extra tab stops behind the scrim. Opening
  focuses New chat; Escape/backdrop/close return focus to the header toggle.
  Crossing the breakpoint closes the drawer and repairs focus/inert state.
- Header language presence is **Auto · per message**, not a claimed detected
  language. The header includes document and theme entry points.
- Common Ground editorial welcome, a desktop script notebook, and all seven
  greetings: Hello / नमस्ते / ਸਤ ਸ੍ਰੀ ਅਕਾਲ / Hola / Bonjour / Hallo / Ciao.
- Six starter categories: general explanation, coding, Hindi, translation,
  documents and current information. Selection populates and focuses the draft.
- Shared appearance dialog with Light/Dark/System and reduced motion.
- Truthful connection status, retained offline warning during retries, timeout
  recovery and protection against obsolete request results.
- Document and voice entry-point dialogs clearly identify their later-phase
  integration; no file picker, microphone or speech engine is activated.

The shell deliberately identifies itself as **Phase 3**. Send is disabled.
Enter/Shift+Enter edit the draft; no chat request, server conversation ID,
fabricated reply or mock chat is created. New chat resets the current in-tab
draft and focuses the composer. Drafts are not stored across reload. Conversation
restoration and automatic conversation titles remain open under F07, for
Phases 4/6. History, uploads and actual voice are not certified by this shell.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/index.html` | Semantic aside/nav/header/main/form/footer, welcome and named overlays |
| `static/v2/css/shell.css` | Responsive sidebar, inner scroll ownership, docked composer and welcome |
| `static/v2/config.js` | Public API origin and 8000ms health timeout |
| `static/v2/js/main.js` | Explicit ES-module boot |
| `static/v2/js/shell.js` | Sidebar placement/persistence, draft sizing, prompt and entry-point wiring |
| `static/v2/js/welcome.js` | Seven-state greeting cycle and motion/visibility lifecycle |
| `static/v2/js/api.js` | Live HTTP boundary; currently only `GET /api/v1/health` |
| `static/v2/js/connection.js` | Reachability state, retry, timeout, abort and request ownership |
| `static/v2/js/icons.js` | Shared original inline SVG sprite |
| `static/v2/js/appearance.js` | Shared appearance controls for both V2 pages |
| `static/v2/js/preferences.js`, `theme-init.js` | Validated preferences and pre-paint resolution |

No new runtime packages or build tools are used. Shared icon/appearance code was
extracted from the workbench instead of maintaining two divergent implementations.
The sprite contains only authored static artwork; user, stored and API text
is never interpolated into its markup.

### State and accessibility

- `sideCollapsed` joins `theme` and `reduceMotion` in the V2-only key. Malformed
  storage uses defaults; blocked storage keeps controls usable and reports that
  the change lasts for this visit. Legacy `gaia.store.v1` is never touched.
- The skip link focuses the main workspace. Icon controls keep accessible names
  when their desktop text labels disappear. Controls have 44px minimum height.
- Sidebar/settings/document transitions use Phase 2 native-dialog helpers.
  Opening an action from the mobile drawer closes navigation before opening the
  next dialog and returns focus to a visible control on exit.
- The greeting rotates on a 4800ms scheduling interval plus its short fades.
  Its visual text is `aria-hidden`; a stable screen-reader welcome avoids
  repeatedly announcing changing greetings. A labelled pause/resume control is
  provided. OS/app reduced motion stops the timer and all greeting animation.
- Visibility changes and open dialogs pause greeting work. A generation counter
  prevents a cancelled fade from applying a late language change.
- Short landscape geometry was checked at 768×450. Physical mobile keyboard,
  Safari/Firefox, screen-reader and zoom audits remain later-phase checks.

### Health contract and truthfulness

The only shell API call is `GET /api/v1/health`. It requires HTTP success,
`status: "ok"`, and a boolean `llm_ready`. It displays **API reachable** and
separately **Provider configured · reply generation not tested** or
**Provider not configured · general replies unavailable**. Configuration is
not treated as a successful LLM request.

Failed fetch, malformed JSON/schema, non-OK HTTP and timeout take the unavailable
path. `navigator.onLine` is used as a browser-offline hint, not proof the service
is working. Retry keeps the warning until success. Every check has its own
AbortController and sequence number; late results after timeout, offline,
visibility change or a newer request cannot overwrite the latest state. Hidden
tabs abort pending checks; foreground and online events recheck. No polling loop
is installed, and changing connectivity never erases the draft.

`API_BASE` uses the page origin when served by FastAPI. On port 5173 it targets
the same hostname on port 8000, using the backend's existing CORS allowlist.
This is public configuration; it contains no API credential. The legacy link
uses this origin so a separate static server still links to the original app.

## Actual verification

Environment: **macOS 27.0.1 ARM64; Python 3.12.7; Playwright 1.63.0;
Chromium 153.0.8010.12; Node 22.23.2**. The approved isolated test environment
was reused. Browser screenshots were visually reviewed at all four widths.

```text
python scripts/verify_shell.py --capture --live http://localhost:8000
31 shell check groups passed; 22 screenshots; live smoke: True.

python scripts/verify_design_system.py
35 check groups passed; 72 token contrast pairs; 2 rendered contrast states; 0 screenshots.

python -m pytest -q
21 passed, 1 warning in 1.89s

python tests/test_code_switching.py
28 PASS
ALL CODE-SWITCHING TESTS PASSED
```

The warning remains Starlette's existing TestClient/httpx deprecation. No package
was added to suppress it. New/changed JS syntax checks and `git diff --check`
also passed. The full machine-readable result is [shell-checks.json](shell-checks.json).

### Coverage

- Light/dark at **360×800, 768×900, 1024×900, 1440×1000**: geometry, sidebar
  behavior, labelled/min-height controls, prompt editing, docked composer,
  long draft sizing, modal focus, New chat and document/voice entry points.
- Skip-link focus, sidebar Escape/backdrop focus return, dialog Tab/Shift+Tab,
  desktop→mobile and mobile→desktop focus cleanup, landscape geometry.
- Sidebar state survives reload and theme changes. OS/in-app reduced motion,
  user greeting pause, all seven greeting states and malformed/blocked storage.
- Explicit health fixtures: unconfigured provider, invalid schema, pending
  request, timeout, late success, failed fetch, retry recovery, offline/online,
  visibility-event cancellation and foreground recovery.
- Network observation in the normal shell fixtures: static GETs and health GETs
  only, no console/page/asset errors, no microphone/speech calls, unchanged legacy
  storage sentinel.
- **Separately labelled real smoke:** actual FastAPI health returned 200,
  `status: ok`, `llm_ready: true`; the rendered shell matched. No chat was sent.
- An additional live browser smoke served `static/` on `127.0.0.1:5173`, opened
  `/v2/`, observed its real GET to `127.0.0.1:8000/api/v1/health` through existing
  CORS, and checked that the legacy link targeted port 8000. That temporary
  static server was closed afterward.

Failure-state screenshots and most browser assertions use explicit Playwright
health-response fixtures. They are not measurements of real backend failure
rates. Hidden-tab checks dispatch a controlled visibility fixture to verify the
event contract; they do not certify mobile OS lifecycle behavior.

### Issues caught during verification

1. CSS can hide the desktop sidebar before `matchMedia` delivers its breakpoint
   event, moving focus to body. Tracking the last focused control now allows the
   shell to return focus to the visible toggle after that transition.
2. Initial spacing left lower desktop prompts below the first view. The welcome
   and empty composer were tightened while preserving normal inner scrolling.
3. Intermittent test startup failures were traced with a repeated boot probe to
   `ERR_CONNECTION_RESET` on a module load, with zero mounted SVG symbols. The
   temporary Python server's default connection backlog of 5 was too small for
   the routed browser's parallel asset burst. The shared test-only
   `PreviewServer` now uses 64. Assertions, timeouts and the application/backend
   were not weakened to mask the failure. Both browser batteries passed after
   the infrastructure fix.

### Existing browser runner

The unmodified `python tests/test_browser.py` still produces:

```text
PASS welcome screen visible on fresh load
tests/test_browser.py:40
Page.wait_for_selector: Timeout 30000ms exceeded.
waiting for locator(".msg.assistant .bubble") to be visible
```

The retained legacy startup failure is documented in
[STARTUP_FAILURE.md](STARTUP_FAILURE.md). This run aborts after its first chat
assertion; it is not a passing legacy suite. The new shell battery does not
replace it or claim chat parity. No old assertions/selectors/timeouts changed.

## Parity gate updates and selector mapping

F01–F06 are complete for their shell scope, backed by `verify_shell.py`, the JSON
report and screenshots. F07 is partial (New chat/draft reset only). F08–F10
require the Phase 4 composer/send lifecycle. F11 and F38–F48 still require the
later document/history/settings integrations. F61/F64 remain release-wide gates.

| Legacy intent | New target | Evidence |
|---|---|---|
| Sidebar collapse/drawer | `#sidebar-toggle`, `#app-sidebar`, `#navigation-drawer` | Persistence, trap, resize and close behavior |
| Welcome greeting (`#greet` in old tests) | `#greeting`, `#greeting-script` | All seven states and pause lifecycle |
| Prompt cards (`#cards .card` in old tests) | `#starter-prompts [data-prompt]` | Exactly six; each populates/focuses draft |
| Composer (`#input`) | `#message-input`, `#compose-region` | Geometry and editable draft only |
| Offline/retry | `#service-status`, `#offline-banner`, `#health-retry` | Failure/recovery and real health smoke |
| Existing default route | `/` | Protected files match `a0a7185`; no route promotion |

The tests live in `scripts/verify_shell.py` so they can run without a backend and
can own a temporary static server. Live smoke is an explicit optional argument.

## Exact Mac instructions

From Terminal 1:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000/static/v2/index.html**. If the correct FastAPI server
is already running, reuse it. The original assistant remains
**http://localhost:8000/**; the component workbench is
**http://localhost:8000/static/v2/components.html**.

Terminal 2, with the previously approved Playwright/Chromium tools available:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python scripts/verify_shell.py --capture --live http://localhost:8000
python scripts/verify_design_system.py
python -m pytest -q
python tests/test_code_switching.py
git diff --check
```

For a backend-off fixture-only run, omit `--live`:

```bash
python scripts/verify_shell.py
```

For the separate static origin described in Phase 0, use an additional Terminal:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python -m http.server 5173 --bind 127.0.0.1 --directory static
```

Open **http://127.0.0.1:5173/v2/** with FastAPI on port 8000. This serves only
`static/`. Check port ownership with `lsof -nP -iTCP:5173 -sTCP:LISTEN` or
`lsof -nP -iTCP:8000 -sTCP:LISTEN` before starting duplicate servers.

Manual review: collapse/reload the desktop sidebar; narrow the window and open
navigation; select each starter; switch themes; enable Reduce motion; inspect
the document/voice notices; use Check service and observe an unavailable state
with the backend stopped. The draft should remain editable throughout.

**Stop after Phase 3 approval review. Phase 4 chat/API/mock implementation has
not begun.**
