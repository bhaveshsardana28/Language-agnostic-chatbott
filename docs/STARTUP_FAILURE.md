# Existing Playwright chat timeout — fresh diagnosis before Phase 2

Date: 10 October 2026. Scope: diagnose the existing application without
changing its backend, frontend or test assertions.

## Finding

**The first chat timeout is caused by a frontend JavaScript parse error. It is
not caused by a missing API key, rate limit or slow model response.**

1. `static/js/markdown.js:24` opens an outer `highlight()` function that is
   never closed. A duplicated implementation appears inside it. Node and
   Chromium reject the entire script with `Unexpected end of input` at EOF.
2. Consequently `window.md`, `window.esc` and `window.speechText` are undefined.
3. `static/js/chat.js:12–18` polls indefinitely for those functions. Its
   asynchronous `init()` waits before obtaining DOM references or attaching
   the composer submit/Enter handlers (`chat.js:444–465`).
4. `main.js` independently makes the welcome screen visible, so the first
   browser check passes even though chat initialization has not completed.
5. Pressing Enter never sends `/api/v1/chat`, leaving the existing test at
   `tests/test_browser.py:40` waiting for an assistant bubble that cannot appear.

There is also a **separate selector mismatch**: the existing test uses
`.msg.assistant .bubble`, while the unfinished split constructs
`.msg--assistant .msg__bubble`. Both selectors matched zero messages in the
fresh diagnostic. Merely changing selectors or increasing the timeout would
hide neither the parse failure nor the missing send request.

Other unbound cross-module references described in `FRONTEND_AUDIT.md` remain:
`renderSidebar`, `refreshDocs`, `closeDrawer`, `setOffline`, missing docs/input
exports and the disconnected server-conversation lifecycle. A single closing
brace is not a complete repair of this pre-existing split.

## Real evidence from this run

Environment: Python 3.12.15, Playwright 1.63.0, Chromium 153.0.8010.12,
Node 22.22.3. The sandbox test environment was recreated using the previously
approved pytest/Playwright tools and the declared eager runtime dependencies.
Torch/sentence-transformers were not needed or installed for this diagnosis;
no real embedding test is claimed.

```text
node --check static/js/markdown.js
static/js/markdown.js:244
else initCopyHandler();
SyntaxError: Unexpected end of input
```

```text
Markdown asset: {"status": 200, "bytes": 12065}
Direct campus request: {"status": 200, "frame_types": ["meta", "delta", "done"], "route": "campus_kb", "text": "Exam date sheets are published on the NCU ERP under Examination → Date Sheet, usually 2–3 weeks before exams begin.", "errors": []}
Diagnostic conversation cleanup: {"deleted": true, "documents_deleted": false}
Page errors: ["Unexpected end of input"]
Chat POSTs after Enter: []
DOM state: {"md": "undefined", "esc": "undefined", "speechText": "undefined", "suggestions": 0, "allMessages": 0, "oldSelector": 0, "splitSelector": 0}
```

Health reported `status: ok`, `llm_ready: true`, provider `groq`, model
`qwen/qwen3.8-27b`, and an empty `llm_note`. The failing test's first question
uses the campus route, which does not need an LLM key. The direct campus
request is the decisive control, not the configuration flag alone. Its
response wording may vary because the campus knowledge base selects replies.

Unmodified browser suite:

```text
PASS                                                                 welcome screen visible on fresh load
File "tests/test_browser.py", line 40, in run
    page.wait_for_selector(".msg.assistant .bubble", timeout=30000)
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
```

This is one passed check followed by an aborted runner, not a completed suite.
No API keys were printed and no assertions or timeouts were changed.

### Final Phase 2 rerun — 11 October 2026

After the temporary Linux sandbox environment disappeared, the same declared
eager dependencies and approved test tools were installed in an isolated venv
on macOS 27.0.1 ARM64. Python was 3.12.7, Node 22.23.2 and Chromium
153.0.8010.12. The fresh diagnostic again observed the same asset size, parse
error, undefined Markdown globals, zero messages and zero chat POSTs. Health
was HTTP 200. The direct control was HTTP 200, `campus_kb`, frames
`meta → delta → done`, no errors, with this knowledge-base reply:

> Check the Examination section of the ERP portal for the official date sheet
> of mid-semester and end-semester exams.

Its diagnostic conversation was deleted. The unmodified browser runner again
passed welcome and timed out at line 40 after 30000ms. The offline pytest suite
was **21 passed, 1 warning in 2.02s**, and the standalone detector was **28 PASS**.

## Exact macOS reproduction

Terminal 1:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
node --check static/js/markdown.js
python scripts/diagnose_frontend_startup.py
python tests/test_browser.py
```

Open http://localhost:8000/ and DevTools → Console/Network. A fresh browser
profile shows the parser error; entering `when are my exams` sends no chat
POST. The read-only diagnostic script repeats this observation and checks the
API directly. It creates and deletes only its own diagnostic conversation.

**No environment tweak on the Mac fixes this parse error.** Do not replace a
key, spam requests, loosen assertions or extend the timeout to address it.
The frontend needs a separately authorized repair or the new frontend's
equivalent functionality. Phase 2 builds the new design system beside it.

Environment troubleshooting, only if the reproduction cannot start:

- Wrong folder: use the exact `cd` above; `ls backend static tests` must show
  this project.
- Inactive venv: `source venv/bin/activate`, or use `./venv/bin/python`.
- Missing app package: `python -m pip install -r requirements.txt`.
- Missing approved test tools: `python -m pip install pytest==9.1.1 playwright==1.63.0`,
  then `python -m playwright install chromium`.
- Port conflict: `lsof -nP -iTCP:8000 -sTCP:LISTEN`; reuse the correct server
  or Ctrl+C its owning Terminal. The existing browser suite requires port 8000.
- If Node is unavailable, the Chromium Console/diagnostic browser observations
  still identify the same parse error; Node is only the independent syntax check.
- A future **general-chat** missing-key error is separate: health will report
  `llm_ready: false`. Configure `LLM_API_KEY` in the existing local `.env` and
  restart FastAPI; never put it in frontend code. A real provider 429 requires
  waiting for the provider's quota window. Neither occurred in this first test.

## Preservation of the pre-existing application work

The user authorized a separate commit or stash. Chosen action: **commit**, so
the files remain available in place and the existing backend is not reverted.

Commit **`a0a7185`**, on `feature/redesign-v2`:

```text
chore(frontend): snapshot pre-existing application edits before redesign
18 files changed, 3035 insertions(+), 1277 deletions(-)
```

It contains exactly:

- `templates/index.html` — pre-existing modular template replacement.
- `static/css/{components,layout,motion,tokens}.css` — four pre-existing files.
- `static/js/{api,chat,components,documents,main,markdown,settings,sidebar,store,voiceInput,voiceMode,voiceOutput}.js`
  — twelve pre-existing files.
- `backend/main.py` — the already-existing `StaticFiles` import and `/static`
  mount, recorded unchanged. No new backend logic was authored.

`app.py`, requirements and tests were not included. No secrets or `.env` files
were staged. Ignored local files remain on disk. No stash was created, applied
or dropped; no files were deleted. Git author/committer values matched the
repository's established identity for this command only; Git config was not
changed.

Inspect the snapshot without modifying the working tree:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
git show --stat a0a7185
git show a0a7185:static/js/markdown.js
```

This is explicitly a preservation checkpoint of **known-broken work**, not a
passing release. Phase 2 implementation is in a separate commit.
