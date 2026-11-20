# Language-Agnostic Chatbot
## Complete Project Report

**A pivot-translation multilingual campus assistant with a general multilingual AI extension**

**Institution:** The NorthCap University, Gurugram

**Programme:** B.Tech CSE (AI/ML)

**Team:** Bhavesh Sardana (23csu070), Dakksh Sharma (23csu081), Avi (23csu061)

**Supervisor:** Ms. Meghna Sharma

**Report status:** Complete implementation report
**Report date:** 14 October 2026

---

## Abstract

This project develops a multilingual conversational assistant for university
campus support. The core system uses a pivot-translation architecture: it
detects the user's language, translates the request into English, classifies the
intent using one English TF-IDF plus Logistic Regression model, selects a safe
response from a campus knowledge base, and translates the response back into the
user's language. This design avoids training one intent model per language and
allows a new supported language to be added without retraining the classifier.

The original campus assistant supports English, Hindi, Punjabi, Spanish, French,
German and Italian at runtime. The evaluated six-language dataset contains 180
queries: 30 intent-balanced queries in each of English, Hindi, Punjabi, Spanish,
French and German. Language detection achieved 95.0% overall accuracy. The
English classifier achieved 0.8125 five-fold cross-validation accuracy and 0.8138
out-of-fold macro F1. End-to-end intent accuracy was 96.7% in English and 74.7%
averaged across the five non-English languages. A controlled no-pivot ablation
achieved only 13.3% average non-English accuracy, demonstrating that translation
to a common pivot is the main enabling mechanism.

The project was subsequently extended with GAIA V2, a FastAPI-based general
multilingual layer. GAIA preserves the deterministic campus pipeline as the
`campus_kb` route and adds general LLM chat, document question answering,
cross-language retrieval, web search, SSE streaming, persistent conversations,
document management, source cards, themes, history, responsive interaction and
voice-input controls. V2 uses a local multilingual MiniLM embedding model for
document retrieval, optional LLM generation through an OpenAI-compatible
provider, and SQLite persistence for conversations, document chunks, metadata
and embeddings.

The current implementation has 28 passing Python regression tests, passing core
Makefile tests and lint checks, a deterministic 10-case multilingual RAG
benchmark with a 100% top-document hit rate, and browser verification for the
main frontend flows. The report also records the boundaries honestly: the local
workspace cookie is not account authentication, SQLite is a single-node store,
OCR depends on optional system tooling, live external LLM generation requires a
private API key, and real-device microphone testing remains outside automation.

**Keywords:** multilingual NLP, pivot translation, intent classification,
language detection, conversational AI, retrieval-augmented generation, FastAPI,
Flask, document QA, cross-language retrieval, SQLite.

---

## 1. Introduction

### 1.1 Background

Students and university staff often ask the same operational questions in
different languages. A campus assistant therefore needs to understand more than
English while remaining affordable, predictable and maintainable. A separate
intent classifier for every language creates a data and maintenance burden. A
large multilingual language model can reduce that burden, but it introduces
cost, latency, nondeterminism, data-governance concerns and weaker auditability
for a bounded FAQ domain.

This project investigates a third option for the bounded campus problem. It
keeps one transparent English intent classifier and uses machine translation as
the language boundary. The architecture is deliberately modest: it can run on a
laptop, its classification decisions are inspectable, and its fallback behavior
is explicit.

The project later grew into a two-layer system. The original pivot chatbot is
retained as the deterministic campus route, while GAIA V2 provides a more
general assistant experience for open-ended chat, uploaded documents and web
information.

### 1.2 Problem statement

The system must answer campus questions from users who may write in different
languages, without maintaining a separate classifier and training set for each
language. It must also avoid confidently fabricating answers when the input is
ambiguous, unsupported or outside the campus knowledge base.

The extended system additionally needs to:

1. support general multilingual conversational interaction;
2. answer questions about uploaded PDF, DOCX, TXT and Markdown files;
3. retrieve document evidence across languages;
4. keep conversations isolated from one another;
5. provide visible source references and honest failure states;
6. survive application restarts without losing server-side context;
7. present the result through a usable responsive interface.

### 1.3 Aim

The aim is to design, implement and evaluate a practical language-agnostic
chatbot whose core knowledge behavior is deterministic and whose extension layer
can handle broader conversational and document tasks without compromising the
original campus pipeline.

### 1.4 Objectives

The project objectives are:

- detect the language and script of each message;
- translate non-English input into an English pivot representation;
- classify the pivot text with one English intent model;
- select a safe answer from a structured response knowledge base;
- translate the answer back into the user's language;
- measure classifier, detection and end-to-end performance;
- implement confidence-based refusal for uncertain requests;
- provide a maintainable FastAPI extension around the original system;
- add multilingual document retrieval and grounded document answers;
- persist conversations and document indexes locally;
- enforce local workspace ownership boundaries;
- verify behavior through deterministic tests and browser checks.

### 1.5 Scope

The original system is a bounded campus assistant. Its response knowledge base
covers 16 intents including admissions, attendance, exams, fees, food/canteen,
hostel, identity, library, placements, results, timetable, transport, greetings,
goodbye, thanks and events/clubs.

GAIA V2 expands the user experience but does not replace the original model. It
adds the following routes:

| Route | Responsibility | External dependency |
|---|---|---|
| `campus_kb` | Deterministic pivot pipeline and campus response KB | Free MT for non-English input/output |
| `translate` | Explicit translation requests | Free MT provider chain |
| `document` | Uploaded-file retrieval and grounded QA | Local embeddings plus LLM for generation |
| `web` | Recency-oriented questions and source display | Keyless web search plus LLM |
| `general` | Open-ended multilingual chat | Configured LLM provider |

The archive directory contains an earlier Streamlit/LLM prototype named Aikya.
It is retained for reference and is not part of the running submission path.

---

## 2. Design rationale

### 2.1 Why pivot translation?

The central design choice is to normalize multilingual input into English before
classification:

```text
Language-specific input
        ↓
Language detection
        ↓
Translation to English pivot
        ↓
One English intent classifier
        ↓
Safe English response
        ↓
Translation to the user's language
```

This gives the project a simple extension rule: adding a language requires a
runtime language mapping, translation support and a localized fallback string;
the classifier does not need a new model or language-specific training set.

### 2.2 Why classic machine learning for the campus route?

The campus domain is small and structured. TF-IDF with Logistic Regression is
appropriate because it is fast, inexpensive, inspectable and easy to retrain.
The response knowledge base is deterministic, so the system does not generate
uncontrolled institutional facts. The confidence gate converts uncertainty into
an explicit fallback rather than a confident guess.

### 2.3 Why retain a separate general layer?

The original architecture is strong for a fixed set of campus intents but cannot
answer arbitrary questions or reason over uploaded documents. GAIA V2 therefore
uses route-specific behavior rather than forcing every request through one
model. Campus FAQs remain auditable; general and document routes use an LLM only
when their route and configuration permit it.

### 2.4 Why SQLite for persistence?

The application is a local, single-node project with small per-conversation
corpora. SQLite avoids adding an operational database service while providing
transactions, restart recovery, foreign-key cleanup and a portable file. The
document embeddings are serialized as NumPy `float32` blobs. Retrieval rebuilds
an in-memory matrix lazily for active sessions, preserving the existing exact
cosine implementation.

---

## 3. System architecture

### 3.1 High-level architecture

```text
                         ┌─────────────────────────┐
                         │      V2 web client      │
                         │ Common Ground frontend  │
                         └────────────┬────────────┘
                                      │ HTTP / SSE
                                      ▼
                         ┌─────────────────────────┐
                         │ FastAPI GAIA V2 layer   │
                         │ route detection        │
                         │ conversation lifecycle │
                         └──────┬──────┬──────┬────┘
                                │      │      │
                                │      │      └──────── Web search + LLM
                                │      └─────────────── Document RAG + LLM
                                └────────────────────── Campus pivot pipeline
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ SQLite durable store   │
                         │ conversations          │
                         │ messages               │
                         │ documents/chunks       │
                         │ embeddings             │
                         └─────────────────────────┘
```

The original Flask interface and pipeline remain available as a legacy or
regression path. The default V2 entry point is `http://localhost:8000/`.

### 3.2 Core campus pipeline

```text
User message
   │
   ▼
src/detection.py
   │  langdetect + short-text/script/code-switch heuristics
   ▼
Supported-language gate
   │
   ▼
src/translation.py
   │  GoogleTranslator → MyMemoryTranslator
   │  retry, exponential backoff, disk cache
   ▼
src/classifier.py
   │  TF-IDF unigram vectorizer + Logistic Regression
   ▼
Confidence gate: p < 0.30
   ├── fallback: localized “I did not understand” response
   └── accepted intent
          ▼
data/intents_en.json response knowledge base
          ▼
Translate response to user language
          ▼
Flask/V2 response with metadata and timings
```

### 3.3 V2 route pipeline

```text
Incoming message
   ▼
Per-message language metadata
   ▼
Router with explicit document/translation precedence
   ├── campus_kb  → deterministic pivot pipeline
   ├── translate  → translation service and prior assistant context
   ├── document   → retrieve chunks → grounding gate → grounded LLM prompt
   ├── web        → search results → source-aware LLM prompt
   └── general    → configured LLM provider
   ▼
SSE meta → delta frames → done frame
```

### 3.4 Document ingestion and retrieval

```text
Upload PDF/DOCX/TXT/MD
   ▼
Extension and 10 MiB validation
   ▼
Text extraction
   ├── PDF page markers
   ├── optional OCR fallback for scanned PDFs
   ├── DOCX paragraphs and tables
   └── plain text/Markdown decoding
   ▼
1,200-character chunks with 150-character overlap
   ▼
paraphrase-multilingual-MiniLM-L12-v2 embeddings
   or lexical fallback if embeddings are unavailable
   ▼
Atomic SQLite transaction
   ▼
Query embedding and cosine ranking
   ▼
Grounding gate / overview retrieval
   ▼
Bounded document context in the user message
   ▼
LLM response with source metadata
```

### 3.5 Separation of engine and domain

The reusable language and pipeline code lives under `src/`. Campus-specific
intent examples and responses are stored in `data/intents_en.json` and selected
configuration values. This separation means that the pivot engine can be
adapted to another bounded domain by replacing the knowledge base and retraining
the classifier.

---

## 4. Technology stack

| Layer | Technology | Role |
|---|---|---|
| Language | Python 3.12 | Backend, training and evaluation |
| Legacy/API UI | Flask | Original campus route and legacy interface |
| V2 API | FastAPI + Uvicorn | REST endpoints and SSE streaming |
| Language detection | `langdetect` 1.0.9 | ISO language detection and probabilities |
| Translation | `deep-translator` | Google primary, MyMemory fallback |
| Classifier | scikit-learn | TF-IDF and Logistic Regression |
| Embeddings | sentence-transformers | Cross-language document retrieval |
| Tensor backend | PyTorch CPU | Embedding inference |
| Persistence | SQLite | Conversations, messages and RAG data |
| Documents | pypdf, python-docx | PDF/DOCX extraction |
| Optional OCR | PyMuPDF, Pillow, pytesseract/Tesseract | Scanned PDF fallback |
| Frontend | HTML, CSS, JavaScript | Responsive V2 interface |
| Streaming | Server-Sent Events | Incremental chat deltas |
| Browser verification | Playwright/Chromium scripts | Frontend regression checks |
| Tests | pytest and project scripts | Unit, API, RAG and integration checks |

The core project does not use GlotLID, FastText language models, XLM-R, mBERT,
Whisper or TTS. The archived Aikya prototype's LLM integrations are not the
core pipeline.

---

## 5. Data and model development

### 5.1 Training dataset

The training file `data/intents_en.json` contains:

- 16 campus-domain intents;
- 20 English utterances per intent;
- 320 total training examples;
- four safe response strings per intent;
- English-only data by design.

The data validator checks balance, duplicate examples, response coverage and
intent consistency. During development it caught a cross-intent duplicate,
`hostel mess menu`, which appeared under both hostel and food/canteen.

### 5.2 Multilingual evaluation dataset

The test file `data/test_multilingual.json` contains 30 intent-balanced query
templates rendered in six languages:

| Language | ISO code | Queries |
|---|---:|---:|
| English | en | 30 |
| Hindi | hi | 30 |
| Punjabi | pa | 30 |
| Spanish | es | 30 |
| French | fr | 30 |
| German | de | 30 |
| **Total** |  | **180** |

The evaluation file is separated from training and is never used to fit the
classifier. Italian is supported at runtime as an extension-proof language but
is not part of the original six-language benchmark. The non-English test
translations were AI-assisted drafts and should receive fluent-speaker review;
this is an important dataset-quality caveat.

### 5.3 Classifier configuration

The training script evaluates a small grid of vectorizer and classifier choices.
The selected configuration is:

- TF-IDF word unigrams;
- sublinear term-frequency scaling;
- Logistic Regression;
- `C=10.0`;
- no class weighting;
- stratified five-fold cross-validation;
- random seed 42 for reproducibility.

The trained artifact is `models/intent_classifier.joblib`.

### 5.4 Language detection logic

`langdetect` supplies the base language prediction. The project adds short-text
and script-aware heuristics, including mixed-script analysis and selected
romanized Hindi/Punjabi terms. The final metadata includes language, language
name, script and confidence. Unsupported languages receive a localized decline
rather than being silently forced through the classifier.

### 5.5 Translation reliability

The primary free translation provider is Google through `deep-translator`, with
MyMemory as a fallback. The wrapper includes retries, backoff and a disk cache.
The cache is important for repeatable evaluation and reduces warm-run latency.
It also introduces a quality caveat: a cached translation preserves whichever
provider result arrived first.

---

## 6. Implementation details

### 6.1 Confidence-aware campus responses

The classifier returns an intent probability. A threshold of 0.30 was selected
by an out-of-fold threshold sweep. When confidence is below the threshold, the
system returns a localized fallback. This behavior is intentionally
conservative: refusing to answer is preferable to presenting an incorrect
campus fact with confidence.

### 6.2 Response knowledge base

The campus response layer is data-driven. Each intent has safe response strings,
and the pipeline selects a response without an LLM. This keeps the core answer
space auditable and prevents an external generation model from inventing
university policy.

### 6.3 V2 routing

The V2 router chooses among translation, campus, document, web and general
routes. Explicit document references take precedence when a conversation has
uploaded files. Document overview questions use representative document chunks
instead of an overly strict factual similarity gate. Precise questions use
retrieval scores and a grounding threshold.

### 6.4 Document formats and extraction

The accepted upload formats are PDF, DOCX, TXT and Markdown. The public upload
limit is 10 MiB per file. PDF extraction retains `[Page N]` markers so source
cards and prompts can cite page numbers. DOCX extraction includes both
paragraphs and table rows.

For image-only PDFs, the optional OCR path renders pages and invokes Tesseract.
OCR availability is capability-detected and reported through the health endpoint.
If the tooling is absent, the application rejects the document as having no
extractable text instead of silently storing empty content.

### 6.5 Retrieval and grounding

The selected local embedding model is
`paraphrase-multilingual-MiniLM-L12-v2`. It supports cross-language similarity
between English documents and queries in languages such as Hindi, Spanish,
French and German. Vectors are normalized and ranked using cosine similarity.

For precise questions, the current embedding grounding threshold is 0.45. A
separate lower threshold is used by the degraded lexical fallback because its
Jaccard-like scores are not directly comparable to cosine similarity. Overview
questions bypass the factual gate and sample representative chunks so generic
questions such as “What is in this document?” can reach the LLM with evidence.

The context budget is bounded by `DOCUMENT_CONTEXT_MAX_CHARS`, defaulting to
12,000 characters. Excerpts are placed in the user message as well as governed
by a document-specific system prompt because model testing showed that some
models did not reliably use excerpts located only in the system message.

### 6.6 Persistence

The SQLite schema contains:

- `conversations`: conversation ownership and timestamps;
- `messages`: bounded user/assistant/system history;
- `rag_sessions`: session mode, embedding model and vector dimension;
- `documents`: uploaded filenames per RAG session;
- `chunks`: chunk text, page metadata and optional embedding blobs.

Ingestion is transactional. Text, metadata and embeddings are not made visible
until extraction and embedding validation succeed. Foreign keys allow deleting a
conversation to remove its document session and chunks. Active sessions use an
in-memory cache, while a cache miss reconstructs the matrix from SQLite.

### 6.7 Workspace ownership

Each browser receives a random `HttpOnly` `gaia_workspace` cookie. The value is
stored with conversations and document sessions. Requests from another browser
workspace cannot read, append to, upload into or delete the original session.
The mechanism is intended for local/demo isolation. It is not a substitute for
authenticated users, signed identity claims or production authorization.

### 6.8 Frontend implementation

The V2 Common Ground frontend provides:

- welcome state and starter prompts;
- per-message streaming and typing state;
- cancellation, retry, edit and copy actions;
- safe Markdown rendering and code-copy controls;
- automatic text direction and language/script chips;
- language-switch dividers;
- conversation history with search, rename, export and deletion;
- local history persistence;
- document upload, list, clear and status states;
- source cards for document and web evidence;
- dark, light and system themes;
- responsive sidebar and mobile drawer;
- offline/health indication and debug information;
- browser SpeechRecognition voice input with editable transcripts.

Voice input deliberately does not auto-send the recognized text. Unsupported
browsers, permissions errors, recognition errors and cancellation are presented
as explicit UI states.

### 6.9 API surface

The principal V2 endpoints are:

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Redirect to the V2 frontend |
| `/legacy` | GET | Legacy UI for regression comparison |
| `/api/v1/health` | GET | Provider, model, LLM, storage and OCR status |
| `/api/v1/languages` | GET | Supported languages |
| `/api/v1/intents` | GET | Campus intents and routes |
| `/api/v1/conversations` | POST | Create a server conversation |
| `/api/v1/chat` | POST | SSE chat stream |
| `/api/v1/chat/{id}` | DELETE | Delete conversation and its documents |
| `/api/v1/documents` | POST | Upload a document for a conversation |
| `/api/v1/documents/{id}` | GET | List documents and chunk counts |
| `/api/v1/documents/{id}` | DELETE | Clear the conversation document store |

The chat stream emits `meta`, one or more `delta` frames, optional `error` and a
final `done` frame. The final frame contains latency, model label and source
metadata. The service uses safe error messages rather than returning stack
traces to clients.

---

## 7. Evaluation methodology

All quantitative results are generated by repository scripts and stored in the
`results/` directory. The main commands are:

```bash
python scripts/train.py
python scripts/tune_threshold.py
python scripts/eval_detection.py
python scripts/eval_e2e.py
python scripts/eval_e2e.py --baseline
python scripts/eval_rag_multilingual.py --json
```

The project distinguishes between:

1. classifier cross-validation;
2. language detection accuracy;
3. end-to-end intent accuracy;
4. a no-pivot ablation;
5. latency and error taxonomy;
6. RAG retrieval accuracy;
7. API and frontend regression tests.

The test set contains only 30 cases per language, so one query changes a
language result by approximately 3.3 percentage points. The results should be
read as engineering measurements, not as statistically precise estimates for
all possible users.

---

## 8. Results

### 8.1 English intent classifier

The selected model was evaluated with stratified five-fold cross-validation on
320 examples and 16 intents.

| Metric | Result |
|---|---:|
| Cross-validation accuracy | 0.8125 |
| Macro precision | 0.8220 |
| Macro recall | 0.8125 |
| Out-of-fold macro F1 | 0.8138 |
| Training examples | 320 |
| Intent classes | 16 |
| Best vectorizer | TF-IDF unigrams |
| Best classifier setting | Logistic Regression, `C=10.0` |

The weakest per-intent F1 values were observed for events/clubs (0.5714),
results (0.7027), exam schedule (0.7347) and admissions (0.7368). The main
failure pattern is lexical overlap between neighboring campus concepts.

### 8.2 Language detection

| Language | Correct | Total | Accuracy |
|---|---:|---:|---:|
| English | 30 | 30 | 100.0% |
| Hindi | 30 | 30 | 100.0% |
| Punjabi | 30 | 30 | 100.0% |
| German | 26 | 30 | 86.7% |
| Spanish | 27 | 30 | 90.0% |
| French | 28 | 30 | 93.3% |
| **Overall** | **171** | **180** | **95.0%** |

Errors were concentrated in short strings and related-language confusions such
as German being labeled Dutch/Afrikaans/related profiles, Spanish being labeled
Portuguese/Catalan and French being labeled Finnish/English. The detector
handles the supported language gate conservatively.

### 8.3 End-to-end intent accuracy

| Language | Pivot pipeline | No-translation baseline |
|---|---:|---:|
| English | 96.7% | 96.7% |
| Hindi | 90.0% | 6.7% |
| Punjabi | 86.7% | 6.7% |
| Spanish | 70.0% | 16.7% |
| French | 73.3% | 23.3% |
| German | 53.3% | 13.3% |
| **Non-English average** | **74.7%** | **13.3%** |

The pivot architecture improved non-English performance by approximately 3–13×
relative to sending raw non-English text into an English-only classifier. The
lowest result was German, matching its lowest detection accuracy and its
greater sensitivity to short-text detection slips.

### 8.4 Error analysis

The recorded error categories were:

1. short sister-language detection slips;
2. translation noise lowering classifier confidence below the 0.30 gate;
3. adjacent campus intents colliding after translation;
4. outbound translation failure causing a correct English answer with a
   degraded flag.

Translation error propagation is the dominant structural risk. The confidence
gate is therefore a feature, not merely an error symptom: it allows the system
to decline rather than guess.

### 8.5 Latency

Measured behavior shows that the classifier itself is not the latency bottleneck:

| Stage | Approximate behavior |
|---|---|
| Language detection | About 2 ms after warm-up |
| Intent classification | About 1–2 ms |
| Translation request | About 0.95–1.2 s cold |
| Non-English total | About 2–3 s cold |
| English total | About 3–5 ms |
| Cached translation | Near-zero translation overhead |

More than 99% of cold non-English latency is attributable to the external
translation hops. This justifies the disk translation cache and the rule to
avoid translating English input.

### 8.6 RAG evaluation

The new deterministic benchmark uses three small English documents and ten
queries in English, Spanish, Hindi, German and French. It evaluates top-document
retrieval without calling an LLM.

| Metric | Result |
|---|---:|
| Test cases | 10 |
| Languages represented | 5 |
| Top-document hit rate | 100.0% |
| Embedding mode | Production cached MiniLM |
| LLM calls | 0 |

Observed top-hit scores ranged from approximately 0.491 to 0.751. This is a
small engineering fixture, not a claim of universal multilingual retrieval
quality. It demonstrates that the implemented cross-language retrieval path,
SQLite serialization and ranking behavior work on the selected cases.

### 8.7 Document QA regression coverage

The RAG tests cover:

- broad document summaries;
- precise factual questions;
- refusal when the answer is absent;
- prompt/context construction;
- PDF page metadata;
- DOCX table extraction;
- multiple-document ranking;
- session isolation;
- empty and invalid uploads;
- atomic rollback after embedding failure;
- multilingual retrieval plumbing;
- explicit document-route precedence.

### 8.8 Frontend and stability verification

The browser verification covered the V2 shell, streaming state, history,
documents, language metadata, responsive layout, themes, Markdown escaping and
mocked voice input. The stability suite recorded 28/28 browser checks passing in
its documented run. Important verified fixes include:

- correct ownership of the chat scroll region;
- anti-force-scroll behavior while a user is reading older content;
- XSS-safe Markdown escaping;
- no conversation-open scroll jitter;
- mobile drawer and responsive document panel behavior;
- a starter-prompt send event reaching the normal input handler.

---

## 9. Testing and verification

### 9.1 Automated checks

The current Python regression suite reports:

```text
python -m pytest -q
28 passed, 1 warning
```

The project Makefile additionally runs:

- core Flask and pipeline tests;
- V2 API tests;
- code-switching detection tests;
- Python compilation/lint checks.

The latest checks completed successfully:

```text
make test       PASS
make lint       PASS
python -m compileall -q backend scripts tests   PASS
```

The one pytest warning is a Starlette/httpx deprecation warning from the test
client dependency stack; it does not currently fail the suite.

### 9.2 Persistence tests

Persistence tests clear the in-memory caches after creating a conversation and
uploading an embedded document. The test then reloads history and document
chunks from SQLite and verifies that retrieval still works. A second test
confirms that a different workspace cannot list, upload into or delete the
original conversation.

### 9.3 Honest verification boundaries

The following are not claimed as fully verified:

- live provider generation without a configured private API key;
- OCR output quality with real scanned documents in the current environment;
- real microphone and speaker behavior on Safari/iOS or other devices;
- multi-instance or managed-database behavior;
- statistical generalization beyond the small benchmark datasets.

---

## 10. Security, privacy and reliability

### 10.1 Input and output safety

The application validates message size and document extension/size. LLM and
document content is rendered through an escape-first Markdown path. Source links
are restricted to validated HTTP(S) URLs. Backend exceptions are logged
server-side and returned to clients as safe error messages.

### 10.2 Data boundaries

Document sessions are scoped to conversation IDs and persisted with workspace
ownership. Deleting a conversation removes its messages and document session.
The local database is ignored by git and should be treated as runtime data.

### 10.3 External data processing

Non-English input may be sent to free translation providers. General, document
and web generation may be sent to the configured LLM provider. The application
is therefore appropriate for public or non-sensitive demonstration data only
until privacy, retention and provider terms have been reviewed.

### 10.4 Operational limitations

The default deployment is a local development server. Before public exposure,
the project needs a production server, host and CORS restrictions, rate
limiting, authenticated identities, secure cookies, request-size controls,
provider monitoring and a privacy review.

---

## 11. Limitations

1. **Translation error propagation:** a poor translation can change the intent
   or lower confidence.
2. **Small training set:** 320 examples limit the classifier's ability to
   separate semantically adjacent campus intents.
3. **Small evaluation set:** 30 queries per language means one query changes a
   result by approximately 3.3 percentage points.
4. **Short-text language ambiguity:** very short phrases can be confused with
   related language profiles.
5. **Code-switching coverage:** Hindi/Punjabi plus English receive targeted
   heuristics; romanized Tamil, Urdu and other pairs are weaker.
6. **Free MT reliability:** quota, quality and availability are outside the
   application; caching can preserve an imperfect first result.
7. **Static campus KB scope:** the deterministic route cannot answer beyond its
   16 intents.
8. **LLM dependency in V2:** general, document and web routes require a
   configured provider except mocked tests and keyless routes.
9. **RAG threshold heuristic:** the 0.45 embedding gate is calibrated evidence,
   not a learned factual verifier.
10. **OCR dependency:** scanned-PDF support requires optional Python packages and
    a system Tesseract executable.
11. **Workspace cookie is not authentication:** possession of the cookie is
    sufficient to act as that local workspace.
12. **SQLite scale:** the local durable store is not a replacement for a
    managed database or vector service in a horizontally scaled deployment.
13. **Voice testing:** browser recognition is feature-detected and mocked in
    automation; real-device voice quality remains unverified.

---

## 12. Deployment and usage

### 12.1 Installation

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python scripts/train.py
```

### 12.2 Start the V2 application

```bash
make run-v2
```

Open:

```text
http://localhost:8000/
```

The V2 general/document/web routes require a configured `LLM_API_KEY` unless
the provider is a local Ollama-compatible configuration. The campus and
translation routes can operate without an LLM key.

### 12.3 Run the legacy comparison app

```bash
make run-legacy
```

The legacy path is retained for regression comparison and is not the default
experience.

### 12.4 Optional OCR setup

Set `OCR_ENABLED=1` and install PyMuPDF, Pillow, the Python `pytesseract`
wrapper and the operating-system Tesseract executable. Use:

```text
GET /api/v1/health
```

to inspect the `ocr_available` capability flag.

### 12.5 Runtime configuration

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | LLM provider name | `groq` |
| `LLM_MODEL` | Provider model label | `qwen/qwen3.8-27b` |
| `LLM_API_KEY` | Private provider credential | empty |
| `GAIA_DB_PATH` | SQLite database path | `data/gaia.db` |
| `MEMORY_TURNS` | Server-side conversation window | `10` |
| `MAX_MESSAGE_CHARS` | Message limit | `4000` |
| `DOCUMENT_CONTEXT_MAX_CHARS` | Document prompt budget | `12000` |
| `OCR_ENABLED` | Enable optional OCR attempt | `1` |
| `OCR_LANG` | Tesseract language code | `eng` |

Secrets belong in `.env` or the deployment secret manager and must not be
committed.

---

## 13. Future work

### 13.1 Core multilingual pipeline

- expand each intent from 20 to at least 100 carefully reviewed examples;
- obtain fluent-speaker verification for the multilingual test set;
- add back-translation augmentation only after quality checks;
- improve detection for short sister-language phrases;
- add broader, language-independent code-switch handling;
- add entity and slot extraction for dates, course codes and locations;
- evaluate sentence embeddings against TF-IDF before changing the production
  campus route.

### 13.2 GAIA V2 production hardening

- replace workspace cookies with authenticated account subjects;
- add CSRF protection and secure-cookie deployment settings;
- add rate limiting, audit logging and provider health metrics;
- add background ingestion jobs and progress IDs for large documents;
- move SQLite to a managed relational store for multi-instance deployment;
- migrate vector retrieval to a managed/local vector database when corpus size
  requires it;
- add document deletion, retention and user-data export policies;
- add a formal prompt-injection and untrusted-document evaluation suite;
- install and test OCR across representative scanned-PDF languages.

### 13.3 Evaluation

- increase the number of multilingual queries per intent;
- separate human-reviewed and AI-drafted translations in the reported metrics;
- measure answer faithfulness and citation correctness, not only retrieval hit;
- test real configured LLM providers with reproducible prompts and redacted
  logs;
- add load, concurrency and restart tests against a production-like service.

### 13.4 User experience

- connect optional speech output after privacy and browser review;
- perform manual Safari/iOS and Android testing;
- add keyboard-accessible document and source-card audit to every release;
- expose document processing status as a durable job state for large uploads.

---

## 14. Conclusion

The project demonstrates that a multilingual campus assistant does not require a
separate intent model for every language. A single English TF-IDF plus Logistic
Regression model, surrounded by language detection and translation, achieved
95.0% language detection and 74.7% average non-English end-to-end intent
accuracy on the evaluated benchmark. The no-pivot ablation's 13.3% non-English
average confirms that the pivot representation is doing the main work.

The implementation also demonstrates a practical evolution path. The original
deterministic campus pipeline remains intact and auditable, while GAIA V2 adds
general chat, document retrieval, source-aware responses, streaming and a
substantially richer interface. SQLite persistence now recovers server memory
and document indexes after restart; optional OCR provides a defined path for
scanned PDFs; local workspace ownership prevents accidental cross-browser data
access; and deterministic RAG evaluation provides evidence for the current
retrieval plumbing.

The system is suitable as a local demonstration and as a strong final-year
project implementation. It is not yet a fully hardened public multi-user
service. Authentication, rate limiting, provider privacy, OCR deployment,
managed persistence and larger human-reviewed evaluation remain the necessary
steps before production use.

---

## Appendix A — Repository map

```text
app.py                         Flask entry point and legacy-compatible path
config.py                      Supported languages and shared configuration
src/detection.py               Language and script detection
src/translation.py             Pivot translation providers/cache
src/classifier.py              TF-IDF + Logistic Regression model
src/pipeline.py                Core detect → translate → classify → respond flow
backend/main.py                FastAPI V2 routes and SSE chat flow
backend/router.py              V2 route decisions and document precedence
backend/memory.py              Bounded persistent conversation memory
backend/rag.py                 Document ingestion, retrieval and grounding
backend/documents.py           File extraction, chunking and optional OCR
backend/storage.py             SQLite schema and persistence operations
backend/settings.py            Environment-driven V2 settings
static/v2/                     Common Ground frontend
data/intents_en.json           English campus training/response data
data/test_multilingual.json    Multilingual evaluation data
models/                        Regenerated classifier artifact
results/                       Reproducible evaluation artifacts
scripts/                       Training, evaluation and browser verification
tests/                         Core, V2, RAG and persistence regressions
docs/                          Architecture, API, testing and phase records
archive/                       Retired prototype, reference only
```

## Appendix B — Evidence and reproducibility

| Claim | Evidence |
|---|---|
| Classifier metrics | `results/classifier_report.json` |
| Language detection metrics | `results/detection_summary.csv` |
| End-to-end and baseline metrics | `results/e2e_summary.csv`, `results/baseline_summary.csv` |
| Error categories | `results/e2e_errors.csv`, `docs/EVALUATION.md` |
| RAG retrieval benchmark | `scripts/eval_rag_multilingual.py` |
| RAG regression tests | `tests/test_rag_qa.py` |
| Restart and ownership tests | `tests/test_persistence.py` |
| API contract | `docs/API.md` |
| Deployment instructions | `docs/DEPLOYMENT.md` |
| Known limitations | `docs/LIMITATIONS.md` |
| Frontend stability evidence | `docs/STABILITY_REPORT.md` and browser verification scripts |

## Appendix C — Final verification record

The latest local verification completed during report preparation was:

```text
python -m pytest -q                         28 passed
make test                                   PASS
make lint                                   PASS
python -m compileall -q backend scripts tests PASS
python scripts/eval_rag_multilingual.py     100.0% hit rate on 10 cases
```

The test suite emitted one non-failing Starlette/httpx deprecation warning.
Live external LLM generation was not claimed because it depends on a private
provider credential. OCR capability was reported by the health endpoint and was
false in the current environment because the optional OCR stack was not
available.
