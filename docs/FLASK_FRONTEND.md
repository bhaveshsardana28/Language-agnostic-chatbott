# GAIA: no-build multilingual Flask frontend

This frontend uses only `templates/index.html`, `static/css/style.css`, and
`static/js/app.js`. No framework, build step, CDN, remote font, or backend change
is required. The existing V2 frontend under `static/v2/` is untouched.

## Open the correct app

Use **http://localhost:5000/** for this frontend, not port 8000. The project's
default `make run` / `python app.py` still starts the separate FastAPI V2 app.
Do not use FastAPI's `/legacy` URL: it can render the template but does not
provide the Flask `POST /chat` endpoint this frontend needs.

From the repository directory, with Python **3.12.7** available:

1. Place the three frontend files at the paths above. They are already installed
   in this workspace. For a manual copy, create the destination folders first:

   ```bash
   mkdir -p templates static/css static/js
   ```

2. For a clean checkout, install the existing locked dependencies locally:

   ```bash
   python3 --version
   # Confirm 3.12.7 before continuing; do not recreate a working environment.
   python3 -m venv venv
   ./venv/bin/python -m pip install -r requirements.lock
   ```

3. Serve the existing Flask application (no backend edits):

   ```bash
   ./venv/bin/python -m flask --app app:app run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
   ```

4. In a second macOS Terminal tab:

   ```bash
   open http://localhost:5000/
   ```

   If a server is already running there, just open the URL; do not start a second
   instance. Stop a foreground server with Ctrl+C.

### Flask wiring

The existing Flask application's `GET /` already renders `index.html`. Flask
serves the two assets under `/static/`, and the existing `POST /chat` handles
requests. These three pieces must be on the same origin. `CONFIG` at the top of
`static/js/app.js` contains the entire frontend transport contract and timeout.

## Behavior and assumptions

- Languages: English (`en`), Hindi (`hi`), Punjabi/Gurmukhi (`pa`), Spanish (`es`),
  French (`fr`), German (`de`). Italian is intentionally not included.
- Auto-detect sends `language: null`. Selecting a language sends its code and
  localizes the greeting, draft suggestions and placeholder. The surrounding
  interface remains English. Suggestions fill the draft; they never auto-send.
- Flask reports the detected input language in `lang` and the detector’s estimate
  in `language_meta.confidence`. The legacy intent fields return `null` and
  `0.0` for compatibility.
- The Flask handler honors a supported `language` field when choosing the reply
  language. Auto-detection still runs on the original input.
- There is no browser storage or cookie access in this frontend. Refresh clears
  messages, draft and theme preference. Messages still go to the server; this
  does not assert anything about server/provider logging or retention.
- System theme follows OS changes; the theme button cycles System → Light →
  Dark → System. Font families are local fallbacks, not downloaded assets.
- No chosen language is RTL, but input and message bodies use `dir="auto"` and
  logical CSS. Arabic text is included in the rendering checks.
- Replies are plain text, not HTML/Markdown. API errors and 45-second timeouts
  show a safe error with Retry. Retry preserves the original message/language.
- Clear chat immediately cancels a pending fetch and discards stale responses.
  This clears browser memory, not server-side records or server computation.

## Verification

```bash
make test
./venv/bin/python scripts/verify_flask_frontend.py
```

The browser checks use the project's installed Playwright/Chromium and intercept
all requests locally. No live server, network, model or API key is required once
those existing test dependencies are installed. No additional dependency was
added. This is separate from `make test`, which retains the project's existing
offline application suite.

Verified: 39 application tests, 40 offline browser cases, and a live English
Flask chat response. Browser checks cover six languages, literal XSS payloads,
IME events, retry/timeout, clear-during-request, RTL, scrolling, memory-only state,
system/manual themes, reduced motion, and 360/768/1440px layouts. Existing
dependency deprecation warnings remain. Real-device IME, Safari/Firefox,
screen-reader announcements and live non-English translation quality still need
manual checks; no full WCAG certification is claimed.

Manual messages:

| Language | Message |
|---|---|
| English | Why is the sky blue? |
| Hindi | पुस्तकालय कब खुलता है? |
| Punjabi | ਲਾਇਬ੍ਰੇਰੀ ਕਦੋਂ ਖੁੱਲ੍ਹਦੀ ਹੈ? |
| Spanish | ¿Cuándo abre la biblioteca? |
| French | Quand la bibliothèque ouvre-t-elle ? |
| German | Wann öffnet die Bibliothek? |

For each, inspect the detected-language badge and expand translation details.
Also try keyboard-only navigation, Shift+Enter, a real IME, mobile zoom, OS dark
mode, browser offline mode + Retry, and refreshing/clearing a pending chat.
