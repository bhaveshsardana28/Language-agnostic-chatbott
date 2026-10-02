# Phase 0 — Repository Audit (per master prompt)

Date: 30 Sep 2026 · Auditor: senior-eng pass, all answers verified against the
actual code, not the docs. Raw files unchanged: this document is the only
Phase-0 artifact.

## 0.1 What this repo actually is

A **pivot-translation intent chatbot** (the approved FYP architecture):
detect language → translate to English → ONE TF-IDF+LogisticRegression intent
model → static response KB → translate back. Flask UI. 931 lines of Python
across 10 files, plus data, results, and docs. The earlier Streamlit
multi-LLM prototype ("Aikya") lives untouched in `archive/` and is **not**
part of the running system.

## 0.2 The 25 mandated answers

| # | Question | Truth |
|---|---|---|
| 1 | Language detection model | `langdetect` 1.0.9 (naive Bayes over char 3-gram profiles, 55 languages) + project heuristics in `src/detection.py` |
| 2 | GlotLID? | **No. Not present, never was.** |
| 3 | FastText? | **No.** No `.bin/.ftz` models anywhere. |
| 4 | Language model files | None project-local; langdetect ships its profiles inside the package |
| 5 | Language mapping logic | ISO-639-1 code from langdetect → membership check against `config.SUPPORTED_LANGS`; short-text greeting map + ASCII low-confidence→English heuristic; empty → `None` |
| 6 | Confidence | `detect_langs` top-prob used only *inside* the heuristic (threshold 0.8 for ASCII short text); **not exposed** downstream today |
| 7 | Intent classifier | scikit-learn Pipeline: TfidfVectorizer(unigram, sublinear) → LogisticRegression(C=1.0), English-only, trained on 300 curated examples, saved to `models/intent_classifier.joblib` |
| 8 | Rule/embedding/ML/LLM | **ML-based** (classic ML via pivot English). No LLM anywhere |
| 9 | Intent definitions | 15 campus-domain intents, data-driven in `data/intents_en.json` (`examples` + `responses` per intent) |
| 10 | Multilingual examples | Test set only: 30 queries × 6 languages (`data/test_multilingual.json`), separate from training by design; AI-drafted, `pa/es/fr/de/hi` pending fluent-speaker verification |
| 11 | Embedding model | **None.** |
| 12 | Vector database | **None.** |
| 13 | Document ingestion | **None** in the running system (archive had PDF/DOCX extraction + TF-overlap retrieval; retired with Aikya) |
| 14 | Chunking | None (see 13) |
| 15 | Retrieval | None. Answers come from a static intent→response KB (`random.choice` over 4 responses per intent) |
| 16 | Reranking | None |
| 17 | LLM | **None.** Zero LLM calls, zero API keys needed |
| 18 | Prompt construction | N/A — no prompts exist |
| 19 | Conversation memory | None server-side; UI keeps display history in browser localStorage (cosmetic, not sent back) |
| 20 | Frontend↔backend | `templates/index.html` → `fetch POST /chat` JSON |
| 21 | APIs | `GET /` (page), `POST /chat` (message→reply). **No** /health, /languages, /intents, /feedback, no /api/v1/* versioning |
| 22 | Tests | 6 offline tests in `tests/test_core.py` (config, detection, Flask contract, English pipeline, monkeypatched non-EN cache/retry, e2e contract) — all green |
| 23 | Broken | Nothing failing. Latent: langdetect `de→nl/af/no/tr` slips on short German greetings (7 rows in e2e); Punjabi greeting under confidence gate |
| 24 | Incomplete (vs master prompt) | IDENTITY intent; language metadata object (script/conf); entity extraction; domain/OOD split beyond the confidence gate; retrieval/RAG; LLM generation; memory; response validation; observability beyond per-stage logging; security hardening (no rate limiting/CORS policy — localhost dev app); Docker was deliberately skipped |
| 25 | Preserve | `src/detection.py`, `src/translation.py` (provider fallback chain), `src/pipeline.py` (confidence gate/timings/cache), `src/classifier.py`, `scripts/train.py`+`tune_threshold.py`+`eval_*.py`, `data/`, `results/` methodology, `templates/index.html`. The audit's job is to protect exactly these. |

## 0.3 Phase-1 live battery (real measurements, `results/phase1_battery.json`)

| Query | Expected lang | Got | Intent | Conf | Wall ms | Verdict |
|---|---|---|---|---|---|---|
| Hello | en | en | greet | 0.459 | 22 | ✅ |
| आप कैसे हैं? | hi | hi | greet | 0.162 | 2500 | ✅ (thin margin) |
| ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ? | pa | pa | **fallback** | 0.105 | 2431 | ❌ MT noise under gate |
| ¿Cuándo son los exámenes? | es | es | exam_schedule | 0.541 | 2716 | ✅ |
| Quand sont les examens ? | fr | fr | exam_schedule | 0.486 | 3242 | ✅ |
| Wann sind die Prüfungen? | de | de | exam_schedule | 0.541 | 2591 | ✅ |
| Quando sono gli esami? | it | it | exam_schedule | 0.541 | 4707 | ✅ (7th language, zero retraining — Phase-7 claim holds live) |
| Wer bin ich? | de | de | **fallback** | 0.114 | 2679 | ❌ no IDENTITY intent in taxonomy (master prompt Phase-5 case, confirmed real) |

Notes: non-EN wall time = two MT hops through the free provider chain
(Google→MyMemory fallback, disk-cached); classify itself ~1–2 ms.

## 0.4 Confirmed gaps that map to cheap, in-scope fixes

1. IDENTITY intent missing → add to dataset (16th intent) + regression test `test_wer_bin_ich` (already demanded by master prompt P23/P28).
2. Language metadata not structured (`{language, script, confidence}`) → small `detection.py` extension (script via Unicode range; confidence = langdetect top-prob surfaced).
3. No /health or /languages endpoints → two small Flask routes.
4. Greeting robustness for pa/hi post-MT → 2–3 more "how are you" training variants, then retrain.
5. Docs set (`ARCHITECTURE/API/EVALUATION/MODELS/DATA/LIMITATIONS`) — mostly assembled from REPORT.md/README.

## 0.5 What the master prompt asks for that does NOT exist and cannot be audited "as-is"

Embeddings, GlotLID/FastText, vector DB, ingestion/chunking, retrieval,
reranking, LLM generation, RAG grounding, conversation memory, structured LLM
output, response validation — **none exist in the codebase** (phases 9–17,
35). Introducing them is new scope, not a fix; see the scope decision logged
in the conversation. It also partially conflicts with the approved FYP brief
("no large neural models in the core system", campus domain, Nov 21 deadline).

## 0.6 Recommendation recorded

Adopt the master prompt's engineering discipline (audit, regression tests,
structured metadata, docs, API hygiene) onto the approved pivot
architecture; log RAG/embeddings/LLM-generation as the post-submission v2
roadmap rather than a pre-deadline rewrite.
