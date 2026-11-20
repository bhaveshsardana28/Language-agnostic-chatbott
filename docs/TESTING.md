# Testing guide

The working-tree verification and release decision are recorded in [the test results](../TEST_RESULTS.md).

## Commands

```bash
cd ~/language_agnostic_chatbot
make test                    # core + V2/RAG + persistence + OCR — offline, mocked where needed
make test-browser            # default V2 route + configured-provider chat smoke
make test-v2-voice           # V2 SpeechRecognition state machine — fake engine only
./venv/bin/python -m pytest -q tests          # full pytest suite when pytest is installed
./venv/bin/python scripts/eval_rag_multilingual.py --json  # 10-case retrieval benchmark
./venv/bin/python scripts/eval_ocr.py --json               # CER/WER synthetic OCR fixtures
```

## What each suite actually proves

| Suite | Covers | Never claims |
|---|---|---|
| `tests/test_core.py` | language detection, cached translation and Flask compatibility contract | — |
| `tests/test_v2.py` (11) | FastAPI routes, router decisions, SSE frames, RAG plumbing (fake embeddings), session isolation, web fallback, docs endpoint | live LLM behavior |
| `tests/test_rag_qa.py` | document overview/precision/refusal, prompt grounding, pages/tables, atomic ingestion | live provider generation |
| `tests/test_persistence.py` | SQLite restart recovery, serialized embeddings, workspace ownership boundary | multi-node database behavior |
| `tests/test_ocr.py` | signatures, page-aware native/mixed extraction, duplicate/report authorization, local image/PDF OCR, rotated and low-contrast synthetic fixtures | handwriting and uninstalled language packs |
| `tests/test_code_switching.py` (26) | mixed-script/Hinglish detection incl. all spec cases | languages beyond the 7 tested |
| `tests/test_browser.py` | default V2 route and configured-provider arithmetic reply | real mic/speakers, real Safari/iOS |
| `scripts/verify_shell.py` | V2 responsive shell, prompts, themes, drawer, health and page-load privacy boundary | real speech recognition |
| `scripts/verify_voice_input.py` | V2 locale setting, requesting/listening, interim/final transcript, keyboard/Escape, errors and no-audio boundary using a fake engine | real mic, locale quality, Safari/iOS |

## Known untested-by-automation (manual checklist before demo)

1. Real-device Safari (scroll, dvh, keyboard-open composer) — see README.
2. Voice — fill docs/VOICE_TEST_MATRIX.md (engines are mocked in CI).
3. Validate rate-limit handling with a synthetic upstream 429. Use an ordinary authorized live request to verify provider access.
4. Theme paint-flash timing (logic verified; sub-100 ms timing is visual).
5. Handwriting, complex tables, photographs with severe perspective distortion,
   and languages whose Tesseract packs are not installed. The synthetic quality
   run reports CER/WER rather than claiming a universal accuracy percentage.

## Historical Phase-11 audit results (axe-core 4.10.2, real runs — 30 Sep 2026)

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
