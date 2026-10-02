# Model inventory (only what's really used)

| Model | Purpose | Version | Source | In→Out | Language coverage | License | Local/API | Resources |
|---|---|---|---|---|---|---|---|---|
| langdetect | Language ID | 1.0.9 (pinned) | PyPI (port of Google's language-detection) | text → ISO-639-1 + prob | 55 language profiles (shipped in package); we gate to our 7. v2 layer adds script-segment analysis + romanized-Hindi/Punjabi lexicons + tech-term whitelisting on top (src/detection.py) — langdetect still does the per-segment heavy lifting | Apache-2.0 | Local | negligible CPU/RAM |
| TF-IDF + LogisticRegression | Intent classification | scikit-learn 1.9.1 (pinned); artifact `models/intent_classifier.joblib` (our training) | trained locally by `scripts/train.py` | English text → intent + probability | English (by design — pivot handles the rest) | BSD-3 (sklearn) | Local | ~2 ms/predict, MB-scale artifact |
| GoogleTranslator (deep-translator 1.11.4) | Pivot MT, primary | (web endpoint; unpinnable) | calls translate.google.com | text → translated text | 100+; we use hi/pa/es/fr/de/it↔en | MIT (wrapper); Google terms apply to the service | API (free, no key) | ~0.3–1.2 s/call cold |
| MyMemoryTranslator (deep-translator) | Pivot MT, fallback | (web endpoint) | mymemory.translated.net | text → translated text | 100+ (locale codes e.g. hi-IN) | MIT (wrapper); MyMemory terms apply | API (free, no key; anonymous daily quota — observed throttling) | ~0.5–1.5 s/call |

Explicitly NOT used (claims you must not make): GlotLID, FastText, mBERT /
XLM-R / any multilingual embedding model, any vector database, any LLM
(local or API), Whisper/TTS in the live path. The archived prototype in
`archive/` called LLM APIs — it is retired and not part of submissions.

## v2 layer (GAIA — actually used, 30 Sep 2026)

| Model | Purpose | Version | Source | Local/API | Notes |
|---|---|---|---|---|---|
| Qwen 3.8 27B chat | general / document / web generation | `qwen/qwen3.8-27b` via Groq free tier | groq.com | API (key in .env, never committed) | strong hi/de/es; env-swappable (`LLM_MODEL`), live-verified in 7-language battery |
| paraphrase-multilingual-MiniLM-L12-v2 | cross-language document retrieval | sentence-transformers 6.1.0, torch 2.14.1 CPU | HuggingFace | Local (~470 MB, first-run download) | live-measured ES↔EN similarity 0.709 on policy doc; grounding gate 0.45 |
| — vector store | per-session chunk store | numpy brute-force cosine (backend/rag.py) | — | Local | sessions are small; Qdrant is the documented upgrade path, not a current need |
