# GAIA V2 frontend redesign

## Result

The default `/` route serves the production-facing V2 workspace under the
**GAIA V2** brand. The frontend remains dependency-free
vanilla HTML, CSS, and native ES modules so it can use the existing FastAPI
static mount without changing the backend architecture.

## Audit findings

- The existing frontend is a static ES-module application, not React or Next.js.
- FastAPI provides SSE chat, server-issued conversation IDs, local-workspace
  cookies, document upload/report/delete, health, languages, and intents.
- Browser history, search, rename, export, and settings are frontend-local.
- There is no account authentication, conversation-list endpoint, upload-progress
  event, persisted response-language preference, or voice-output endpoint.
- SSE metadata includes detected language, response language, route, reason,
  streamed text, model, server latency, and real document/web source references.

## Frontend structure

- `static/v2/index.html` — application shell, welcome state, composer, dialogs,
  and Intelligence Panel.
- `static/v2/css/tokens.css` — dark-first GAIA palette, typography, spacing,
  focus, and motion tokens with an accessible light theme fallback.
- `static/v2/css/shell.css` — responsive sidebar/workspace/Intelligence Panel
  layout and mobile/tablet drawers.
- `static/v2/js/chat.js` — conversation lifecycle, SSE ownership, markdown
  rendering, persistence, sources, retry, copy, edit, and export.
- `static/v2/js/intelligence.js` — renders only backend-reported language,
  route, source, model, latency, and generation state metadata.
- `static/v2/js/documents.js` — live upload, processing/error states, source
  listing, extracted-text report preview, and deletion.

## Truthful capability boundaries

The Intelligence Panel never fabricates percentages, progress, source language,
retrieval stages, or processing time. Retrieval is shown as a service-reported
route and returned source set because the current SSE contract does not emit
retrieval-progress events. Document excerpts appear only when returned by the
backend; otherwise the source viewer requests the real report endpoint.

The sidebar labels the current session as a local workspace. It does not present
an account profile or logout control because the backend currently uses an
HttpOnly workspace cookie rather than user authentication.

## Design and implementation

The original welcome view repeated navigation and explanatory copy, kept an empty metadata panel open on wide displays, and hid voice feedback on phones. The redesigned shell gives the conversation, starter prompts and composer a shared reading column. A local orbital illustration and matching mark identify GAIA. The light theme uses pale surfaces around the same dark illustration. The sidebar becomes a drawer below 64rem. Reply details dock at 80rem, and the welcome grid adapts to the remaining column width. [Desktop dark](screenshots/gaia-v2/desktop-dark.webp) · [Mobile light](screenshots/gaia-v2/mobile-light.webp)

- **Shell and artwork.** `index.html`, `css/tokens.css`, `css/shell.css`, `assets/brand/`, `js/icons.js` and `js/welcome.js` define the responsive layout, sidebar, six editable starters, greeting and brand. The illustration is a static WebP. The greeting pauses when hidden, while a dialog is open, or when motion is reduced.
- **Chat and language.** `js/shell.js` and `js/chat.js` implement the per-draft language dialog, immediate focus restoration, accessible generation announcements and buffered streaming updates. The selector inserts a visible instruction through the existing chat contract. Automatic removes that instruction. Speech input locale remains a separate saved preference.
- **Reading and evidence.** `css/chat.css`, `js/markdown.js` and `js/intelligence.js` handle responsive Markdown, literal inline code and the on-demand reply details panel. Code and tables scroll within the reading column.
- **Tools and preferences.** `js/documents.js`, `js/voiceInput.js`, `js/appearance.js`, `js/preferences.js` and `js/theme-init.js` connect the upload limit, recognition states, settings controls and first-paint theme to the existing services and storage keys.

Regression changes are in `tests/test_browser.py`, `tests/test_v2.py`, and `scripts/verify_chat.py`, `verify_shell.py`, `verify_design_system.py` and `verify_voice_input.py`. The API, storage schema and model providers used their existing implementations. The Flask compatibility page and standalone component gallery retained their separate entry points.

## Running and verifying

From the project root, use `make install` for a fresh Python 3.12 environment and `make run` to serve the workspace at http://127.0.0.1:8000. The static V2 application has no bundle or TypeScript compilation step. Browser test prerequisites are in the README.

```bash
make lint
make test
for f in static/v2/js/*.js static/v2/config.js; do node --check "$f" || exit 1; done
make test-browser
GAIA_BROWSER=chrome make test-browser
./venv/bin/python scripts/verify_shell.py --live http://127.0.0.1:8000
./venv/bin/python scripts/verify_chat.py --live http://127.0.0.1:8000
```

The 20 November 2026 run used a disposable database, uploads and browser profiles. All 66 Python tests passed. Playwright Chromium, installed Chrome and Playwright WebKit exercised the seven requested widths from 320 to 1440 px, editable language selection, real campus chat, reload and regeneration. A real text upload reached Ready, showed the expected extracted text and was removed. Browser fixture checks exercised interrupted streams, Markdown escaping, long code and tables, history, document errors, speech events and playback controls.

Chromium suite results were 35 design-system groups, 39 shell groups including live health, 10 chat groups including live campus, 4 language groups, 15 history groups, 8 document groups and 8 voice groups. The separate Flask frontend passed all 40 fixture cases. The design-system suite checked 72 token contrast pairs and two rendered contrast states. The settings footer remained in view at all seven widths. Physical mobile keyboards, screen readers, native Safari and Firefox, actual microphone recognition and audible playback remain outside this run. WebKit used Playwright’s engine on macOS.
