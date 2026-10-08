# Testing guide

## Commands (all real, all run before this doc was written)

```bash
cd ~/language_agnostic_chatbot
make test                    # FYP core (10) + v2 API (11) + detection (26) — offline, mocked
make test-browser             # real-browser UI suite (61 checks) — server must be on :8000
```

## What each suite actually proves

| Suite | Covers | Never claims |
|---|---|---|
| `tests/test_core.py` (10) | FYP pivot pipeline, classifier gate, Flask contract | — |
| `tests/test_v2.py` (11) | FastAPI routes, router decisions, SSE frames, RAG plumbing (fake embeddings), session isolation, web fallback, docs endpoint | live LLM behavior |
| `tests/test_code_switching.py` (26) | mixed-script/Hinglish detection incl. all spec cases | languages beyond the 7 tested |
| `tests/test_browser.py` (61) | layout/scroll architecture, streaming state machine, anti-force-scroll, XSS escape regression, history/search/export, themes, debug panel, voice state machines (mocked engines), language chips/dividers, mobile drawer, overflow at 375/430/1280 | real mic/speakers, real Safari/iOS |

## Known untested-by-automation (manual checklist before demo)

1. Real-device Safari (scroll, dvh, keyboard-open composer) — see README.
2. Voice — fill docs/VOICE_TEST_MATRIX.md (engines are mocked in CI).
3. Live Groq rate-limit UX (the message exists; force it by spamming).
4. Theme paint-flash timing (logic verified; sub-100 ms timing is visual).

## Phase-11 audit results (axe-core 4.10.2, real runs — 30 Sep 2026)

**Accessibility — axe: CLEAN (0 violations)** on welcome screen, active chat
with messages, and settings modal, after fixing 5 real findings:
solid-button accent failed AA (`--accent-strong:#2563eb` token added: 4.54:1),
conversation list scroll region not keyboard-reachable (tabindex), dialogs
unnamed (`aria-labelledby`), backdrop wrongly claiming `role="dialog"`,
modal heading skip (h2→h4 → h3).

**Security:** zero secrets in the frontend (the one grep hit is the
error-classification regex); `.env` not served (404); external links
`rel="noopener"`; markdown renderer is escape-first (XSS regression-tested);
upload extension + size gated server-side.

**Performance (measured, headless Chromium):** page = 1 request, ~92 KB
uncompressed HTML (no JS/CSS network calls); DCL ~120 ms local; 408 DOM nodes
with a 120-message conversation; streaming updates via textContent
(no re-render framework), scroll follow rAF-throttled. Lighthouse NOT run —
no claims made beyond the numbers above.

## Regression policy

Every fixed bug keeps a named check here (e.g. `markdown escapes raw HTML`,
`stream-follow does not force-scroll a reading user`,
`chat-switch during streaming aborts cleanly`). New bug → new check in the
same commit.
