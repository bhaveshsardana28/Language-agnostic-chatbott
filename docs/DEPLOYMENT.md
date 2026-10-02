# Deployment

## Current (what we submit/demo)

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python scripts/train.py   # builds models/intent_classifier.joblib
venv/bin/python app.py             # http://127.0.0.1:5000   (FYP pivot system)
venv/bin/python -m uvicorn backend.main:app --port 8000        # GAIA v2 layer
```

Dev servers, localhost. v2 additionally needs `.env` with `LLM_API_KEY`
(free Groq key) for the general/document/web routes; campus/translate work keyless.

## Docker: deliberately NOT introduced

One process, four pip deps, no services — a container would bundle nothing
the venv doesn't already provide, and the MT providers are external anyway.
If a deployment is ever needed, the app containers trivially (single FROM
python:3.12-slim; copy repo; pip install; `flask/gunicorn run`). Until that
day it's YAGNI — logged here per the "don't introduce Docker unnecessary"
rule.

## Before any real deployment, the minimum hardening list

1. Production server (gunicorn `app:app`) behind a proxy.
2. Restrict CORS/host binding; add request rate limiting.
3. Auth on anything beyond read-only demo use.
4. Move MT off free endpoints (quota + privacy) or self-host OPUS-MT.
5. Don't log raw user text (currently logged for the study — see app.py;
   add a LOG_USER_TEXT=off switch).
6. Serve via a process manager with restarts; keep `cache/` writable.
