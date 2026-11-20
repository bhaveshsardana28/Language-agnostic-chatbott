# Verification results

## General-purpose assistant verification

On 20 November 2026 the campus classifier, bundled answers and automatic translation for intent classification were removed from both live chat interfaces. The tests used temporary SQLite and upload paths. The offline suite also ran from a copy without classifier artifacts or bundled FAQ data.

| Check | Result |
|---|---|
| `make test` | 66 passed before the change. Final suite: 69 passed, 0 failed, six dependency deprecation warnings. Includes legacy JSON fields, provider failure, multilingual routing, ordinary academic questions, history and document isolation. |
| `make lint`, JavaScript syntax checks, `git diff --check` | Passed. The chatbot serves static assets directly. The separate portfolio also passed `npm --prefix portfolio run lint` and its production build with a temporary output directory. |
| `GAIA_BASE=http://127.0.0.1:18653 ./venv/bin/python tests/test_browser.py` | Chromium passed at 320, 375, 425, 768, 1024, 1280 and 1440 pixels. Verified language selection, streaming, persistence across refresh, regeneration and zero console errors in this journey. |
| `./venv/bin/python scripts/verify_chat.py --live http://127.0.0.1:18653` | Ten groups passed. The configured model answered 19 + 23 with 42 and a follow-up asking for twice that answer with 84. Both replies streamed through the existing interface. |
| Browser scripts under `scripts/verify_*.py` | Ran design_system, shell, chat, languages, history, documents, voice_input and flask_frontend. All eight exited successfully. Browser fixtures cover microphone behavior. The Flask suite observed its two expected HTTP error responses. |
| Real configured Groq requests | General knowledge, Python, mathematics, Hindi and Hinglish produced replies. A follow-up requested French in the same conversation. A university admissions question used the general route, the legacy JSON endpoint returned 15 for 7 + 8, and a newly uploaded text file yielded its project codename with a source. These last three requests initially hit the provider’s rate limit and passed on retry. |
| UI comparison and application startup | Compared all 59 static/template files with the pre-change working tree. All style and visual assets were byte-identical. Both pages retained their element hierarchy, IDs and classes. The restarted local frontend and health check returned HTTP 200. The live route catalog returned four active routes and an empty legacy campus list. |

These checks establish routing and feature behavior. The Hinglish and French samples contained terminology or grammar errors. Physical speech capture and audible playback, a Linux image build, and public multi-user deployment were not verified in this change.

### Files affected by this change

- Chat and compatibility routing: `backend/router.py`, `backend/main.py`, `backend/assistant.py`, `src/pipeline.py`, `app.py`. Historical experiments: `archive/campus_pipeline.py`, `scripts/eval_e2e.py`, `config.py`.
- Installation and packaging: `Makefile`, `Dockerfile`, `.dockerignore`, `.env.example`, `requirements.txt`, `requirements.lock`.
- Interface copy and fixtures: `static/v2/index.html`, `static/v2/js/mock.js`, `templates/index.html`, `static/js/app.js`, `static/js/api.js`.
- Tests: `tests/test_core.py`, `tests/test_v2.py`, `tests/test_audit.py`, `tests/test_browser.py`, `scripts/verify_chat.py`, `scripts/diagnose_frontend_startup.py`.
- Documentation: `README.md`, `FEATURE_MATRIX.md`, `FINAL_AUDIT_REPORT.md`, `TEST_RESULTS.md` and the API, architecture, data, demo, deployment, evaluation, Flask frontend, limitations, models and testing documents under `docs/`.

## Historical full-stack audit

The following results describe the implementation before removal of the campus feature. Current setup and behavior are documented in the [project README](README.md).


**20 November 2026, macOS, Python 3.12.7.** The baseline used a copy of the uncommitted working tree and the existing virtual environment. Final checks also used a newly installed environment, a freshly trained classifier, temporary SQLite databases and upload directories. Browser suites ran in disposable profiles. The speech fixtures and most API integration tests replace external services. The explicitly named live checks used the actual configured services.

## Baseline and final checks

| Check | Result and scope |
|---|---|
| Baseline `make test` | 40 passed, 6 deprecation warnings, 22.93 s. The original pytest command named the executable code-switching script but collected none of its cases. |
| Baseline browser | Real Chromium loaded V2 and rendered the keyless English campus answer. Additional browser suites exposed contrast, obsolete control names, drawer state and a transient harness navigation timeout. |
| Fresh setup | New Python 3.12.7 venv, `python -m pip install --no-cache-dir -r requirements.lock`, `make bootstrap-model`, `make test`. Model trained on 320 examples and loaded successfully. `python -m pip check` reported no broken requirements. |
| Python verification | `make test` runs pytest against the tests directory. The device/browser entry point is an executable script exercised separately. Coverage was measured with `python -m coverage run --source=backend,src,app -m pytest -q tests` and `python -m coverage report`. |
| Build and static checks | `make lint` compiles app, backend, scripts and tests. Node syntax check covered all V2 modules, V2 config and older static scripts. A malformed duplicate legacy Markdown renderer was repaired and its heading and highlighted-code output exercised. Portfolio lint and Vite build ran separately. |
| Dependency checks | Initial OSV scan flagged 9 of 87 installed distributions. The clean application environment contained 79 distributions. After upgrading its bootstrap pip, OSV returned zero matches. The separate portfolio went from 5 npm audit findings (1 high, 4 low) to zero after lock resolution, clean installation and build. Point-in-time package checks exclude the OS, container base image and future advisories. |
| Browser smoke | With a local server running, `make test-browser` and `GAIA_BROWSER=chrome make test-browser` exercised keyless chat, refresh and viewports 320, 375, 768, 1024 and 1440. Chromium 153 and installed Chrome 158 were used. |
| Browser suites | `scripts/verify_design_system.py` passed 35 groups including 72 token contrast pairs and two rendered states. Shell passed 39 groups with live health. Chat passed 9 groups with live campus. Language metadata passed 4, history 15, documents 8, and voice 8 with synthetic engines. Flask browser fixtures passed 40/40. Group counts are separate from pytest. |
| Browser exclusions | Safari WebDriver returned “Allow remote automation” disabled. Playwright Firefox downloaded but failed at launch with “Could not find profile folder” using both the default and an explicit writable temp directory. Neither browser received a functional PASS. |
| Local document retrieval | `HF_HUB_OFFLINE=1 ./venv/bin/python scripts/eval_rag_multilingual.py` retrieved the expected document first in 10/10 cases against three English documents with the cached multilingual MiniLM model. This measures top-one retrieval on this fixture. |
| Local OCR | `./venv/bin/python scripts/eval_ocr.py --json` exercised upright, rotated, low-contrast image and scanned PDF fixtures. English CER and WER were 0.0 on each. Host packs reported eng, osd and snum. Hindi and Punjabi OCR quality remain unmeasured. |
| Classifier | `./venv/bin/python scripts/eval_intent_holdout.py` retained 27 of 30 English queries after normalized training/test overlap and duplicate filtering. Across the 15 represented gold intents, gated accuracy was 26/27 (96.30%), macro precision 0.9111, recall 0.9333 and F1 0.9200. No tuning used this audit evaluation. |
| Detection | `./venv/bin/python scripts/eval_detection.py` scored 171/180 (95.0%). English, Hindi and Punjabi 30/30 each, French 28/30, Spanish 27/30, German 26/30. Italian has regression examples but no rows in this six-language dataset. |
| Performance | Ten warmed direct health-handler calls averaged 40.09 ms initially and 24.35 ms after eliminating duplicate OCR capability checks. This is a local microbenchmark. Campus routing now uses one classifier prediction per accepted campus turn. No production p95, sustained throughput or memory-leak measurement. |
| Docker | Docker CLI installed. The daemon socket was absent, so the image build, Linux health check and volume ownership smoke remain blocked. |
| Secret review | Git diff whitespace check and path-only pattern scan for Groq/OpenAI keys and private key headers. No matched credentials in the scanned source. Local .env and runtime data were excluded from build context and output. |

## Live multilingual campus benchmark

`./venv/bin/python scripts/eval_e2e.py` exercised detection, real translation services, the English classifier and reply selection on 30 campus prompts in six languages. The predicted intent matched the expected label in **137/180 (76.1%)**. Of 21 responses marked degraded, 19 returned no intent and two returned the correct intent with degraded output. This corpus includes the three English prompts excluded from the held-out evaluation above. These scores measure intent selection, not translation fluency.

| Language | Correct intent | Degraded responses |
|---|---:|---:|
| English | 29/30 | 0 |
| Hindi | 25/30 | 4 |
| Punjabi | 26/30 | 3 |
| Spanish | 21/30 | 5 |
| French | 19/30 | 4 |
| German | 17/30 | 5 |

Examples include German hostel questions falling below the confidence threshold after translation, and a university festival question classified as an exam schedule in three languages. Later prompts also encountered repeated translation service failures. The original timing fields undercount unsuccessful inbound translations. The corrected code records that wait, and a deterministic five-second fixture verifies it. The archived latency columns are unsuitable for comparing service performance. [Per-query results](results/audit-2026-11-20/e2e_detail.csv) · [Error records](results/audit-2026-11-20/e2e_errors.csv) · [Summary](results/audit-2026-11-20/e2e_summary.csv)

## User journeys

PASS applies only to the evidence named in the row. FAIL records an observed behavior. BLOCKED records a missing prerequisite.

| # | Journey | Status | Evidence |
|---|---|---|---|
| 1 | Fresh setup and startup | PASS | Clean dependency install, model bootstrap, tests, native FastAPI startup and health. Docker tracked separately. |
| 2 | Frontend to backend | PASS | Live health/shell and campus streams in Chromium and Chrome. |
| 3 | English conversation | PASS | Real campus browser flow and live Groq recall of the synthetic word marigold. |
| 4 | Hindi conversation | FAIL | Live campus answer in Hindi succeeded. On an exact-word follow-up, Groq initially returned a different noun. On repeat it translated marigold to गेंदा instead of preserving the original token. |
| 5 | Hinglish conversation | PASS | Corrected the observed misdetection of “Mujhe batao maine kaunsa test word diya tha?”; live rerun routed as Hindi and recalled marigold. Single example. |
| 6 | Language switching | PASS | Same live conversation switched English → Hindi → Hinglish → Italian. Requested language routing and memory plumbing verified. Exact recall quality qualified in row 4. |
| 7 | Ambiguous/unsupported language | PASS | Emoji-only input produces unknown language; unsupported Russian bypasses campus routing. Verified locally, with no claim about live model fluency. |
| 8 | Intent and fallback | PASS | English campus classification, punctuation, confidence gate and nonsense fallback tests; held-out metrics above. |
| 9 | Document upload | PASS | Live synthetic text upload returned 200. Parser/OCR tests cover other formats and duplicates. |
| 10 | Answer from document | PASS | Live Groq returned 42 from synthetic aurora.txt and reported that document as the source. A quoted instruction to answer with a different word did not change this answer. |
| 11 | Answer absent | PASS | Live response reported missing information about a favourite opera. Regression tests cover retrieval-gate refusal and page metadata. |
| 12 | Voice input and audible output on hardware | BLOCKED | No physical-device speech session. Synthetic tests exercise editable transcription, permission denial, silent input, absent device, stalled service, supported locale, explicit local playback and stop. |
| 13 | History | PASS | Browser save/search/restore including actual refresh. SQLite bounds verified independently. |
| 14 | Independent conversations and ownership | PASS | Cross-client access tests, concurrent chat, ownership claim tests and document isolation checks. |
| 15 | Provider unavailable | PASS | Missing credentials, provider error frames, empty/incomplete streams and failed-turn persistence tested with controlled fixtures. |
| 16 | Slow/interrupted requests | PASS | Browser abort/retry, health timeout, incomplete upstream frames and discarded stale responses. Upstream cancellation latency under sustained load unmeasured. |
| 17 | Invalid inputs | PASS | Wrong JSON shapes, malformed body, empty/oversized input, invalid Unicode, invalid/corrupt uploads, document page limits and failed ingestion. |
| 18 | Mobile layout | PASS | Five requested widths in Chromium and Chrome; 320 px document controls and drawer resize exercised in Chromium. Real mobile keyboards untested. |
| 19 | Refresh and recovery | PASS | Browser reload preserved completed English reply; mocked history restored source cards and reloaded the document list. |
| 20 | Backend restart | PASS | A second Python process read the recorded turn from the isolated database; cache reset reloaded persisted vectors. |
| 21 | Concurrency | PASS | Simultaneous claims and HTTP chats, atomic paired turns, duplicate plus different document uploads, deletion, stale regeneration and capacity rejection/recovery. |
| 22 | Keyboard and accessibility | PASS | Skip link, Enter/Shift+Enter, dialog focus containment/restoration, reduced motion and contrast checks. Screen-reader and full WCAG conformance unmeasured. |

## Semantic review rubric

For each fixed prompt, review **meaning**, **requested language**, **literal fidelity** (names, numbers, URLs, commands) and **grounding** where evidence is supplied. Score each applicable dimension 2 for correct, 1 for understandable with a minor deviation, or 0 for materially wrong, fabricated or missing. Record verbatim discrepancies and provider errors separately. A changed requested identifier or unsupported document claim fails the case even when the prose is fluent.

On the live technical translation, the French answer preserved HTTP 204 and `git status` (literal fidelity 2). On the exact-word Hindi recall, the second answer conveyed the flower’s meaning (meaning 2) but changed the required token (literal fidelity 0). On the synthetic document, the answer 42 matched the uploaded fact (grounding 2). These are spot checks by the auditor; a bilingual human evaluation across all languages remains open.

The final clean Python suite passed **66 tests** with six dependency deprecation warnings in 4.64 seconds. The coverage run passed the same 66 tests in 13.81 seconds. Measured Python statement coverage was **83%** (1,923 statements, 325 missed) across the selected application modules. JavaScript, models, dependencies and the portfolio are outside that coverage denominator. The final Chromium startup diagnostic recorded no page errors and exactly one chat POST after Enter; the live smoke also verified regeneration after reload.

### Reproducing the verification

From the repository root with Python 3.12.7 available, run `make install`, `make lint`, then `make test`. Test configuration selects temporary data and upload paths before application import. Source-level syntax checks use `for f in static/js/*.js static/v2/js/*.js static/v2/config.js; do node --check "$f" || exit 1; done`. Portfolio checks use `npm --prefix portfolio ci`, `npm --prefix portfolio run lint`, `npm --prefix portfolio run build` and `npm --prefix portfolio audit`.

For Chromium, install the optional Playwright dependency as shown in the README. Start the server with `make run`. Run `make test-browser`, `./venv/bin/python scripts/verify_shell.py --live http://127.0.0.1:8000`, and `./venv/bin/python scripts/verify_chat.py --live http://127.0.0.1:8000`. Run the remaining browser scripts with the project interpreter. Several write historical check JSON files, so use a disposable checkout if you want to preserve existing captures. Real service checks require their own configuration and connectivity.
