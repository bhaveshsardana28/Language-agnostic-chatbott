# GAIA V2 feature matrix

| Capability | Status | Evidence or boundary |
|---|---|---|
| FastAPI workspace and Flask compatibility UI | Implemented | FastAPI default, Flask legacy launcher and shared JSON adapter for the compatibility page. |
| Multilingual detection | Partial | English, Hindi, Punjabi, Spanish, French, German and Italian configured. Includes script and Romanized heuristics. Very short prompts and unfamiliar code-switches remain ambiguous. |
| Reply language, translation and code | Partial | Explicit in-message language selection, explicit translation, cached replies, literal code/URL protection and localized fallbacks. MT providers require connectivity and have quotas. |
| General chat and conversation context | Partial | Real Groq streaming and SQLite history. Exact retained wording across languages failed in a live recall check. Output budgets are configurable. Context is bounded by turn count rather than a model-specific tokenizer. |
| OpenAI, OpenRouter and Ollama | Implemented, live verification blocked | Transport and failure tests use synthetic frames. Models and credentials/local service are operator-supplied. |
| Web search | Partial | DuckDuckGo snippets and source links. Tool failure degrades to general chat with instructions to disclose missing live results. |
| Document ingestion and retrieval | Implemented | Native PDF/DOCX/text/images, optional local OCR, chunk/page metadata, embedding or keyword retrieval, source preview, duplicate recognition and deletion. Hardware and language-pack coverage varies. |
| Document QA | Partial | Live supported and absent-answer checks on a synthetic upload. Retrieved evidence is supplied to the model. Citation correctness on arbitrary documents requires evaluation. |
| Chat state | Implemented | Browser-local search/history, SQLite context, restore, edit-as-draft, stop, retry, copy and export. Latest successful reply regeneration uses a server revision. Older saved browser records may lack that revision. |
| Voice input and reply playback | Partial | Editable browser recognition transcripts and opt-in local-voice playback. Automated engine and lifecycle checks pass. Physical device accuracy and audible output remain untested. |
| Theme, keyboard and layout | Implemented | Light/dark/system, reduced motion, dialogs, focus and responsive layouts. Chromium and installed Chrome exercised. No full screen-reader qualification. |
| Safari and Firefox qualification | Blocked | Safari remote automation disabled. Downloaded Playwright Firefox failed to open its profile. |
| Persistence and ownership | Implemented for local workspaces | Single-worker SQLite, workspace cookie, bounded server turns, isolated document operations and process recovery. |
| Public accounts, cross-device sync, per-user quotas | Missing | Required before public multi-tenant release. |
| Deployment | Partial | Native setup uses the configured general model. Container definition and health check available. Linux image and deployment restore drill pending. |

Detailed measurements and release gates are in [TEST_RESULTS.md](TEST_RESULTS.md) and [FINAL_AUDIT_REPORT.md](FINAL_AUDIT_REPORT.md).
