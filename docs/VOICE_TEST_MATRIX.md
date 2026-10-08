# Voice test matrix (§33) — fill with REAL results only

State as of 30 Sep 2026: voice **input** (SpeechRecognition) and voice
**output** (SpeechSynthesis) are implemented and their state machines are
regression-tested against mocks (tests/test_browser.py, 61/63 checks).
**No real-microphone or real-speaker pass has been run.** Every row below
is NOT TESTED until you run it — do not present voice as verified before
this table is filled.

| Language | BCP-47 | Recognition | Synthesis | Browser | Device | Result | Notes |
|---|---|---|---|---|---|---|---|
| English | en-IN | | | Chrome |  | NOT TESTED | |
| Hindi | hi-IN | | | Chrome |  | NOT TESTED | check danda sentence-split aloud |
| Punjabi | pa-IN | | | Chrome |  | NOT TESTED | expect honest "no voice" fallback on most macOSes |
| German | de-DE | | | Chrome |  | NOT TESTED | |
| Spanish | es-ES | | | Chrome |  | NOT TESTED | |
| French | fr-FR | | | Chrome |  | NOT TESTED | |
| Italian | it-IT | | | Chrome |  | NOT TESTED | |
| (each again) | | | | Safari |  | NOT TESTED | Safari lacks webkitSpeechRecognition on some versions — mic button disables itself with an explanation |

**How to test (15 minutes):** `make run-v2` → Chrome → mic (allow) → per
row: Settings → Speech language → speak a short question → confirm
transcript; then reply → Listen → confirm correct-language voice or the
honest no-voice toast. Record PASS/FAIL + notes. macOS voice availability:
System Settings → Accessibility → Spoken Content → System Voice.
