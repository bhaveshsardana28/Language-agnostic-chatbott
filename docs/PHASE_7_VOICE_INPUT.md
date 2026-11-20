# Phase 7 — V2 voice input

**Implemented 13 October 2026.** The default entry point is
`http://localhost:8000/`.

This phase adds one bounded flow: browser SpeechRecognition places an editable
transcript into the existing composer. It does not add speech synthesis, waveform
capture, Voice Mode, or raw-audio storage.

## Delivered

- The V2 composer has a real voice-input control with supported, requesting,
  listening, idle and unsupported states.
- Speech language settings persist in `gaia.redesign.v2` with Auto plus seven
  explicit BCP-47 locales: `en-IN`, `hi-IN`, `pa-IN`, `es-ES`, `fr-FR`, `de-DE`
  and `it-IT`.
- Auto uses the latest detected user language in the active V2 conversation and
  defaults to `en-IN` when there is no detected language.
- Interim and final transcripts update the existing editable composer. Recognition
  never submits automatically; the user can edit and press Enter or Send normally.
- Escape, Cmd/Ctrl+Shift+M, the microphone button, submit, New chat, conversation
  changes, hidden-tab transitions and page hide stop recognition.
- Permission, blocked-service, missing-microphone, no-speech and network errors
  become actionable status/toast messages and return to idle.
- The implementation never calls `getUserMedia`, `MediaRecorder` or stores raw
  audio. Page load remains permission-free.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/js/voiceInput.js` | V2 SpeechRecognition state machine, transcript handling, locale selection and cleanup |
| `static/v2/js/chat.js` | Exposes latest detected user language to the voice controller |
| `static/v2/js/preferences.js` | Persists and validates `speechLanguage` |
| `static/v2/js/appearance.js` | Synchronizes the speech-language setting |
| `static/v2/index.html` | Mic control, live status and speech-language select |
| `static/v2/css/shell.css` | Responsive voice states and status styling |
| `static/v2/js/main.js` | Initializes the V2 voice controller |
| `scripts/verify_voice_input.py` | Mocked-engine browser checks |

## Verification

```text
./venv/bin/python scripts/verify_voice_input.py
6 Phase 7 voice-input check groups passed; mocked engine only.

./venv/bin/python scripts/verify_shell.py
30 shell check groups passed; voice page-load privacy assertion included.

node --check static/v2/js/voiceInput.js
node --check static/v2/js/chat.js
node --check static/v2/js/main.js

git diff --check
clean
```

The machine-readable result is `docs/voice-input-checks.json`.

## Honest boundaries

The automated engine is fake and proves the UI state machine only. Real Chrome,
Safari, microphone permission, locale recognition quality and OS-level speech
availability remain **NOT TESTED** in `docs/VOICE_TEST_MATRIX.md`. Speech output,
per-reply Listen, waveform analysis, auto-read and full-screen Voice Mode remain
later phases.

The subsequent full-stack audit added opt-in per-reply local playback. See the current device verification matrix in `docs/VOICE_TEST_MATRIX.md`.
