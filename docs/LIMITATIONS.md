# Limitations (audited, do not soften these in the report)

1. **Generation availability.** General, web and document answers need a configured, reachable LLM. Upstream rate limits can interrupt a turn.
2. **Code-mixed input (Hinglish etc.) — detection layer HANDLED (30 Sep 2026).**
   Script-segment analysis + romanized-Hindi/punjabi lexicons now classify
   "Mujhe new language seekhne mein..." / "मैं Python सीखना चाहता हूँ, but..." as
   Hindi primary with code-switch metadata (26-case regression suite:
   tests/test_code_switching.py). Residual limits: the romanized lexicon is
   Hindi/Punjabi only; secondary-language detection for Latin-script mixes is
   best-effort; and the *LLM's own comprehension* of odd tokens (e.g. literal
   "DESH KI" caps) is model-dependent — detection can be right while the
   generation misreads. Confidence for lexicon-based calls is a documented
   evidence-count score, not a probability.
3. **Short sister-language detection slips.** de→nl/af/no, es→pt/ca, fr→en on
   short texts (95.0% overall). The system declines gracefully rather than
   answering in the wrong language.
6. **Free MT dependency.** Google/MyMemory rate-limit (observed live:
   both throttled this dev machine within a day). Disk cache + provider
   fallback + graceful degradation mitigate; a paid MT tier or on-prem OPUS-MT
   is the production path.
7. **Bounded server memory.** V2 now persists the last `MEMORY_TURNS` turns and
    document indexes in SQLite, so restart recovery works. Older turns remain
    client-side only; follow-ups beyond the server window need the frontend's
    retained history or a future long-term conversation store.
8. **Workspace cookie is not authentication.** V2 prevents accidental
    cross-browser conversation/document access with a random local workspace
    cookie, but anyone who obtains that cookie can act as that workspace. Do NOT
    expose publicly without authenticated account subjects, rate limiting and a
    hardened CORS/host policy (see DEPLOYMENT.md).
9. **Privacy.** Explicit translation can send text to the translation providers. General chat sends recent turns to the configured model, and document chat also sends retrieved excerpts.

## v2 layer (GAIA) limitations — live-observed, 30 Sep 2026

10. **Free-MT quality quirks.** The provider fallback chain once produced
    "Foster es mañana" for "the exam is tomorrow" (MyMemory after Google
    throttled). Correctness of the translate route depends on provider health;
    the disk cache freezes whichever quality was first received.
11. **LLM context compliance.** Qwen ignored document excerpts when they sat
    in the system prompt; they must ride in the user turn (fixed + verified).
    Any model swap must re-run the cross-language RAG check.
12. **Grounding gate is a cosine heuristic.** 0.45 cleanly separated a real
    answer (0.709) from a topic-adjacent miss (0.397) in live tests, but it
    is not a learned verifier; borderline docs may pass/fail imperfectly.
14. **SQLite is a local single-node store.** It supports restart recovery and
    modest concurrent access, but is not a replacement for a managed database
    or vector service at multi-instance scale. Keep the database on durable
    storage and migrate deliberately before horizontal deployment.
15. **Code-switching beyond hi/pa**: handled for Hindi/Punjabi + English
   (detection layer, see item 2); other romanized pairs (e.g. romanized
   Tamil, Urdu in Latin script) are NOT covered by the lexicons and will
   fall through to whole-text langdetect — honest but weaker.
