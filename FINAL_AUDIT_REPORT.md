# GAIA V2 full-stack audit

Historical record of the earlier implementation. For current behavior, see the [project README](README.md).


**Release decision, 20 November 2026.** The native single-worker application is suitable for a controlled local pilot. Public multi-user deployment still requires authenticated ownership, retention and quota controls, and validation of the Linux image. Live tests found a multilingual recall error. See [test evidence](TEST_RESULTS.md) and the [feature matrix](FEATURE_MATRIX.md).

## What was inspected

The active app is a FastAPI service with a no-build HTML/JavaScript frontend. It uses a scikit-learn campus classifier, two HTTPS translation services, an OpenAI-compatible or Ollama streaming client, and a DuckDuckGo search adapter. SQLite holds turns, extraction reports, chunks and float32 vectors. Originals and cached translations are separate files. NumPy ranks local MiniLM embeddings. The OCR path uses PyMuPDF, Pillow and Tesseract. Flask serves the campus-only interface. The archived prototype and React/Vite portfolio are outside the deployed chat application.

The audit used the working tree of `feature/redesign-v2`, including existing redesign work. Tests and training ran against disposable databases, generated models, uploads and browser profiles. Only synthetic/public benchmark material was submitted to live services. No deployment, commit, real-data migration or deletion was performed.

## Prioritized findings and repairs

| ID | Severity | Root cause and impact | Repair and evidence |
|---|---|---|---|
| 01 | High | Docker copied the checkout, including eligible private attachments outside the upload directory. | Restricted the build context and added explicit source copies. Configured an unprivileged runtime UID. Static inspection only until the image is built. |
| 02 | High | A first-time conversation claim could report success after a competing insert. Message writes could recreate a deleted chat, and the memory cache could disagree with SQLite. | Verify persisted ownership, scope reads and writes to the owner, and commit each turn as a pair. Failed generation stays out of future context. Parallel claim, simultaneous chat, deletion and process-recovery tests cover these paths. |
| 03 | High | Incremental in-memory RAG updates could lose chunks under concurrent uploads. Source-file cleanup could race a second reference. | SQLite serializes document commits. Retrieval caches up to 16 immutable revision-specific indexes. Source cleanup rechecks references under a write lock. Duplicate upload, concurrent indexing, deletion and isolation tests pass. |
| 04 | High | The initial environment had published dependency advisories, including packages that decode untrusted uploads. | Upgraded parser and supporting pins, replaced the unbounded translation wrapper, upgraded the bootstrap installer and updated the separate portfolio lock. Rechecked clean environments against OSV and npm. |
| 05 | High | Validation occurred after chat allocation. Non-string fields were coerced and malformed payloads could reach a 500. File limits applied after multipart parsing and PDF scaling could exceed the render budget. | Bounded raw bodies, strict field checks, Unicode validation, per-worker concurrency limits, and a pre-render PDF guard. Rejected requests, capacity recovery and corrupt-file tests pass. |
| 06 | Medium | Campus reply overrides translated the question. Campus routing and answering classified the same text twice. Punctuation could hide a campus keyword. Code and URLs could be changed by MT. | Reused the probe result, translated the selected answer, protected literals, and reported the delivered reply language. Live French technical translation and Hindi campus checks succeeded. |
| 07 | Medium | Provider EOF could finalize a partial reply. Upstream error details and raw chat text could reach logs. Web snippets were concatenated into the system message. | Require a terminal frame, bound output tokens, remove provider body and raw-message logging, send external evidence as user-role data, and distinguish configuration, rate-limit and interruption errors. Transport fixtures and live grounded QA exercised these paths. |
| 08 | Medium | Retrying a completed reply could append a duplicate turn to the server. Late streams/uploads could update the newly selected chat. | Added revision-checked regeneration for the latest reply, guarded asynchronous UI completions, and restored completed reply state after refresh. Older replies can be reused as drafts. |
| 09 | Medium | The desktop intelligence drawer could cover mobile navigation after resize. Some control targets and theme colors failed the project's checks. | Corrected breakpoint state, focusability, contrast and target sizes. Updated stale accessible-name fixtures while retaining the interactions and assertions. |
| 10 | Medium | A stalled recognition engine could leave the UI waiting. V2 lacked connected reply playback. | Added recognition watchdogs and explicit local-voice playback with cancel and microphone interruption. Synthetic browser tests cover both engines. Physical audio qualification is open. |
| 11 | Medium | Setup could choose Python 3.14, hide a training failure, or start without the campus artifact. The FastAPI legacy form posted to an absent route. Pytest missed the executable code-switching suite. | Corrected the Makefile, setup docs, shared legacy JSON handler and pytest discovery. Test collection uses temporary storage. A fresh Python 3.12.7 install generated the model and passed the suite. |

## Remaining release gates

1. **Identity, retention and quotas.** The HttpOnly browser cookie is a local bearer credential. Establish account identity, revocation and migration of legacy local workspaces before using this for unrelated customers. Apply per-identity quotas at the gateway and define expiration, encryption, backup and restore for database, originals, translations and browser-local history.
2. **Quality.** The live translation-based campus pipeline selected the correct intent for 137 of 180 prompts. German scored 17/30 and French 19/30. Twenty-one responses degraded. The audit fixed missing failure-path timing exposed during this run. Exact cross-language recall also failed on a live synthetic turn. Romanized and short inputs remain heuristic. Retrieved passages can influence a model despite prompt separation. Qualify grounded answers, verbatim identifiers and translations on a larger bilingual corpus.
3. **Operations.** Build and smoke-test the Docker image, including volume ownership, backups and the target OCR packs. Stress-test the target CPU, RAM and disk with representative workloads. SQLite and translation-cache writes were evaluated in a single-worker configuration. Long-running native extraction requires process isolation and hard CPU/memory limits for a public upload service.
4. **External dependencies.** MT and search can be throttled or change format. Hosted model access and retention depend on the provider account. Groq was exercised live. Other providers require their own configured smoke and context-window tests. SSE clients can stop rendering immediately while an in-flight synchronous upstream read waits for its timeout.
5. **Client coverage.** Safari WebDriver requires a host permission. Firefox could not launch its temporary profile. Verify real Safari/Firefox, real microphone and speakers, mobile keyboards, assistive technology and installed Indic speech/OCR packs on target devices.
6. **Integrity and observability.** Schema migrations are additive. Corruption repair, disaster recovery, multi-node consistency, long-run memory growth and production percentile latency remain unqualified. Health reports configuration and OCR capability. The service still uses ordinary Python log records and lacks a deployed metrics/alerting pipeline.

## Implementation references

Request validation, ownership and streaming are in [main.py](backend/main.py), [limits.py](backend/limits.py), [memory.py](backend/memory.py) and [storage.py](backend/storage.py). Retrieval and extraction are in [rag.py](backend/rag.py) and [documents.py](backend/documents.py). Language and transport changes are in [router.py](backend/router.py), [pipeline.py](src/pipeline.py), [translation.py](src/translation.py) and [llm.py](backend/llm.py). Dedicated regressions are in [test_audit.py](tests/test_audit.py). The full JavaScript syntax pass also found and repaired an incomplete duplicate renderer in the older static tree. The current V2 and Flask entry points use separate renderers.

## Changes by area

- Installation, image and packages — `.dockerignore`, `.gitignore`, `.env.example`, `Dockerfile`, `Makefile`, both Python requirements files and the portfolio package manifest/lock.
- Application — `app.py`, backend request limits, chat, settings, provider, router, memory, storage, RAG, extraction and search modules, plus detection, translation and the campus pipeline.
- Browser — V2 HTML, shell and color tokens, chat, documents, intelligence panel, history, Markdown, voice input and new voice output. The older static JavaScript form and Markdown renderer also changed.
- Verification — isolated pytest configuration, audit regressions, existing persistence/RAG/OCR/code-switch tests and browser smoke; standalone language, document, voice, shell, design, Flask, startup diagnosis and intent/RAG evaluation scripts.
- Documentation — README, API, models, deployment, testing and voice notes, plus the three root audit artifacts.

Earlier report edits, screenshots, design work and local attachments were present before this audit. The work was performed in the working tree without staging or committing those changes.
