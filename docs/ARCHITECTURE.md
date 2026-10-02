# Architecture (what actually runs — 30 Sep 2026)

Core separation: **engine** (language-agnostic) vs **domain** (the campus KB).
Everything in `src/` is language- and domain-agnostic; everything
campus-specific lives in `data/intents_en.json` + `config.py`.

```
user text (any supported language)
  │
  ▼  src/detection.py — langdetect (55-lang naive-Bayes profiles) + heuristics
language metadata {language, language_name, script, confidence}
  │
  ▼  config.SUPPORTED_LANGS gate — unsupported → localized decline
  ▼  src/translation.py — translate to English (pivot)
  │     provider chain: Google → MyMemory, retry+backoff, disk cache
  ▼  src/classifier.py — TF-IDF(unigram) + LogisticRegression (ONE English model)
intent + probability
  │
  ▼  confidence gate (0.30, tuned by scripts/tune_threshold.py)
low → localized fallback (per-language strings, no MT needed)   high ↓
  ▼  response KB: random choice from 4 responses/intent (data/intents_en.json)
  ▼  translate back over the same provider chain
reply + metadata + per-stage timings  →  Flask UI (language · intent · conf badges)
```

Extension mechanics (the thesis): a new language = add it to
`config.SUPPORTED_LANGS` + one fallback string. Italian was added live as
proof. A new *intent* = 20 English examples + 4 responses + `train.py` rerun.

Deliberately absent (v2 roadmap, not bugs): vector retrieval/RAG, LLM
generation, server-side memory, auth, Docker. Rationale in LIMITATIONS.md.
