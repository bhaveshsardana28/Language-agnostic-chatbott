# Language-Agnostic Chatbot

**A Pivot-Translation Based Multilingual Conversational System**
+ **GAIA v2 — Global Multilingual AI Assistant layer**

Final-year project — B.Tech CSE (AI/ML), The NorthCap University, Gurugram.

| | |
|---|---|
| **Team** | Bhavesh Sardana (23csu070) · Dakksh Sharma (23csu081) · Avi (23csu061) |
| **Supervisor** | Ms. Meghna Sharma |

## Core idea

Instead of training one intent model per language, the system detects the
user's language, translates the message into a **pivot language** (English),
classifies intent with **one model trained once in English**, selects a
response, and translates it back. **Adding a language needs no new training
data** — only translation support for that language.

## Pipeline

```
User message (hi / pa / es / fr / de / en)
  1. Language detection            (langdetect, short-text heuristics)
  2. Translate -> English (pivot)  (deep-translator / Google)
  3. Intent classification         (TF-IDF + Logistic Regression, scikit-learn)
  4. Response selection            (intent -> response knowledge base)
  5. Translate reply -> user's language
  6. Render in Flask web UI        (+ detected-language badge)
```

Domain: **campus assistant** (timetable, exams, fees, hostel, library,
identity, …) — 16 intents, 20 English examples each. A separate multilingual
test set (30 queries × 6 languages) is never used in training.

## Quick start

```bash
python3 -m venv venv                 # if python3 is missing: /opt/anaconda3/bin/python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py             # FYP pivot system -> http://localhost:5000
```

## GAIA v2 — the general multilingual layer (FastAPI, port 8000)

The v2 layer turns the FYP baseline into a general-purpose assistant while
preserving it as one route (`campus_kb`). Nothing in the graded pipeline
was replaced — it became a component.

```bash
cp .env.example .env                 # add LLM_API_KEY (free: console.groq.com)
make run-v2                          # -> http://localhost:8000
```

| Route | What handles it | Needs LLM key? |
|---|---|---|
| `general` | any question, any language (Groq: `qwen/qwen3.8-27b`, env-swappable) | yes |
| `campus_kb` | FYP pivot pipeline (16 intents, TF-IDF+LogReg, measured) | no |
| `translate` | "translate X into Y" — free MT with cache+fallback | no |
| `document` | per-chat uploaded PDF/DOCX/TXT; cross-language retrieval via `paraphrase-multilingual-MiniLM-L12-v2`; grounding gate 0.45; honest "not found" | yes |
| `web` | recency questions via keyless DuckDuckGo, sources shown | yes |

Per-message language detection, language-switch instructions ("answer in
Hindi"), bounded conversation memory, SSE streaming, dark/light/system themes,
welcome screen with suggestions, markdown + code blocks with copy buttons,
per-conversation sidebar (search/rename/delete/export, grouped by date),
message actions (copy/regenerate/edit/Listen), document chips, sources,
professional debug panel, settings, offline banner, mobile drawer,
**voice input** (browser speech recognition, BCP-47 language selection) and
**voice output** (language-matched synthesis, honest no-voice fallback) —
device-level voice testing pending, see docs/VOICE_TEST_MATRIX.md.
Tested with real-browser Playwright suite: `make test-browser` (61 checks)
+ code-switching detection suite (26 checks). Demo: docs/DEMO_SCRIPT.md.
APIs: `/api/v1/{chat,conversations,documents,languages,intents,health}` —
see docs/API.md. Tests: `make test` (11 v2 + 10 FYP + 26 code-switching + 19 browser).

Run the offline test suite: `./venv/bin/python tests/test_core.py` (or `make test`).

## Project structure

```
app.py                 Flask app: /chat endpoint + UI
config.py              Languages, threshold, paths — single source of truth
src/
  detection.py         Language detection (langdetect + short-text heuristics)
  translation.py       Pivot translation wrapper (deep-translator)
  classifier.py        TF-IDF + LogReg train/predict            (Phase 3)
  pipeline.py          detect -> translate -> classify -> reply (Phase 4)
data/
  intents_en.json            English training set               (Phase 2)
  test_multilingual.json     Human-written multilingual test set (Phase 2)
scripts/               Training + evaluation scripts            (Phase 3/5)
templates/index.html   Chat UI
tests/test_core.py     Offline core tests
archive/               Earlier Streamlit prototype ("Aikya") — not part of the
                       submission; kept unmodified for reference only
portfolio/             Personal portfolio site — unrelated to this project
```

## Status (phased plan)

- [x] 1. Audit & cleanup — repo scaffold, pinned deps, tests green
- [x] 2. Dataset — 15 intents × 20 EN examples + 30×6 multilingual test set
       (validator: `scripts/validate_data.py`; test translations pending fluent-speaker review)
- [x] 3. Classifier — TF-IDF(uni) + LogReg(C=10.0), 16 intents/320 examples:
       **CV acc 0.8125, macro F1 0.8138**
       (`scripts/train.py` → `results/classifier_report.json`, `confusion_matrix.png`)
- [x] 4. Robustness — threshold fallback (0.30, re-derived per retrain by
       `scripts/tune_threshold.py`), MT retry+backoff, Google→MyMemory provider
       fallback, disk cache; structured language metadata (script+confidence)
- [x] 5. Evaluation (30 Sep 2026 runs) — detection **95.0%**; e2e per language:
       en 96.7 · hi 90.0 · pa 86.7 · fr 73.3 · es 70.0 · de 53.3 (non-EN avg **74.7%**)
       vs no-pivot baseline 6.7–23.3%; per-stage latency + error taxonomy in
       `results/` and REPORT §5. Rerun: `scripts/eval_detection.py`,
       `scripts/eval_e2e.py` (cache makes reruns fast)
- [x] 6. UI — language/intent/confidence badges, typing state, localStorage history, mobile
- [x] 7. Extension proof — Italian added via one line in `config.py`, zero retraining
- [x] 8. Docs — `REPORT.md` (results tables), `PPT_OUTLINE.md`, `DEMO_SCRIPT.md`
- [x] 9. Viva prep — `VIVA_PREP.md` (30 Q&A incl. "why not XLM-R")

## Known limitations (documented, with fixes where possible)

- Translation errors propagate into the classifier and back out to the user.
- Code-mixed text (e.g. Hinglish) defeats both detection and translation.
- Very short queries are ambiguous; low-confidence intents get a graceful
  "I didn't understand" reply instead of a wrong answer.

Each limitation gets a measured number in the final report, not hand-waving.
