# Voice test matrix (§33) — fill with REAL results only

State as of 20 Nov 2026: V2 **voice input** is implemented and its state machine
is regression-tested with a mocked SpeechRecognition engine
(`scripts/verify_voice_input.py`). This proves UI behavior only; it does not prove
microphone permission, locale recognition quality or OS speech-service support.
V2 offers per-reply playback through matching local speech-synthesis voices. Automated playback and recognition tests use deterministic engines. **No real-microphone or real-speaker pass
has been run.** Every row below is NOT TESTED until you run it.

| Language | BCP-47 | Recognition | Synthesis | Browser | Device | Result | Notes |
|---|---|---|---|---|---|---|---|
| English | en-IN | | | Chrome |  | NOT TESTED | |
| Hindi | hi-IN | | | Chrome |  | NOT TESTED | editable transcript and optional local playback |
| Punjabi | pa-IN | | | Chrome |  | NOT TESTED | |
| German | de-DE | | | Chrome |  | NOT TESTED | |
| Spanish | es-ES | | | Chrome |  | NOT TESTED | |
| French | fr-FR | | | Chrome |  | NOT TESTED | |
| Italian | it-IT | | | Chrome |  | NOT TESTED | |
| (each again) | | | | Safari |  | NOT TESTED | Safari may lack SpeechRecognition; the V2 mic button should disable with an explanation |

**How to test (15 minutes):** `make run` → Chrome → mic (allow) → per row:
Settings → Speech input language → speak a short question → confirm the editable
transcript; then press Enter and record the recognition result. Use Listen on the assistant reply and check stop, locale and conversation switching. Record PASS/FAIL + notes. macOS voice availability:
System Settings → Accessibility → Spoken Content → System Voice.
