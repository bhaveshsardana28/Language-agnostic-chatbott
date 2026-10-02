# Limitations (audited, do not soften these in the report)

1. **MT error propagation.** A mistranslated query can flip the intent and the
   user sees a confident wrong answer. This is the #1 measured failure mode
   (REPORT §5.6). Mitigation in place: confidence gate; future: back-
   translation sanity check.
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
4. **Small data.** 320 training utterances bound the classifier (CV 0.81);
   30 queries/language bound test resolution (±3.3% per query).
5. **Static KB = no open-domain ability.** By design: deterministic, auditable,
   zero hallucination — but it can never answer outside its 16 intents; the
   fallback gate is the honesty mechanism.
6. **Free MT dependency.** Google/MyMemory rate-limit (observed live:
   both throttled this dev machine within a day). Disk cache + provider
   fallback + graceful degradation mitigate; a paid MT tier or on-prem OPUS-MT
   is the production path.
7. **Single-shot conversations.** No server-side memory; follow-ups
   ("and for tomorrow?") don't resolve context. Client history is display-only.
8. **No auth/rate-limiting/CORS policy.** Localhost demo app. Do NOT expose
   publicly without a hardening pass (see DEPLOYMENT.md note).
9. **Privacy.** Non-English (and fallback English) text leaves the machine to
   free MT providers. Fine for public FAQ content; NOT for personal data —
   needs a privacy review + likely paid/private MT before real users.

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
13. **Router keyword list is English-only** (applied to the English pivot
    form), so campus detection depends on MT quality for the probe — a bad
    translation can mislabel the domain.
14. **No auth, in-process memory, single-worker assumptions.** Same as item 8;
    v2 is a local demo app, not a multi-user service.
15. **Code-switching beyond hi/pa**: handled for Hindi/Punjabi + English
   (detection layer, see item 2); other romanized pairs (e.g. romanized
   Tamil, Urdu in Latin script) are NOT covered by the lexicons and will
   fall through to whole-text langdetect — honest but weaker.
