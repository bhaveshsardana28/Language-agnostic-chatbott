# Viva preparation — 30 likely questions with model answers

Practise out loud. Every factual claim maps to `results/` — if asked "how do
you know?", point at the file. Numbers below are from our actual runs
(30 Sep 2026).

## The architecture

**1. Why pivot through English instead of one model per language?**
Per-language models need per-language training data — that cost scales
linearly with languages and is the whole problem we're removing. English has
the best free machine translation, so pivoting through it quality on both hops. We measured the alternative: the same English model
*without* the pivot scores 6.7–23.3% on our non-English test queries vs
53.3–90.0% with it (non-English average 74.7%).

**2. Why not multilingual BERT / XLM-R / mT5?**
Three concrete reasons, none of which is "we didn't know". (a) **Compute and
determinism:** transformer inference on CPU is 100–1000× our TF-IDF+LogReg's
~2 ms, and we target laptop deployment. (b) **Auditability:** institutional
FAQ bots must give deterministic, inspectable answers; we can point at a
logistic-regression weight, we can't do that for 110M parameters.
(c) **Data efficiency:** with 20 examples per intent, a classical model is at
its sweet spot; fine-tuning a transformer on 300 examples overfits.
The honest caveat we'd add: for open-domain chat or code-mixed text, a
multilingual embedding model likely wins — that's our documented future work.

**3. What happens when translation is wrong?**
Errors propagate: garbage in → plausible-but-wrong English → confident wrong
intent → wrong answer, translated back. We quantify this in §error-analysis
(`results/e2e_errors.csv`): it's the dominant failure mode. Mitigations in
the system: confidence fallback gate, short-text detection heuristics, and
deterministic KB answers that fail *visibly* (wrong topic) rather than
fluently hallucinating like an LLM would.

**4. What is novel here?**
Not any single component — the novelty is the measured pipeline: a
zero-retraining multilingual extension mechanism (demonstrated live by adding
Italian as language 7 within the demo), plus an honest per-stage evaluation
(detection accuracy, end-to-end per-language accuracy, latency breakdown,
ablation baseline) that student projects usually skip.

**5. Why a static response KB and not an LLM for generation?**
Determinism and auditability. An institution can't have the answer to "what
is the fee deadline" change wording between runs, and a generated answer can
hallucinate policy. Static KB = correct by construction for a bounded domain.
Trade-off accepted and documented: no open-domain ability.

**6. Walk me through one request end to end.**
"From the Hindi query: langdetect says `hi` (~2 ms); we translate to English
via Google→MyMemory fallback chain (~300–500 ms cold, 0 ms cached); TF-IDF
vectorizes, LogReg scores 15 intents (~2 ms); if max probability < 0.125 we
reply with a localized 'didn't understand'; else we sample a KB response for
the intent and translate it back; every stage's ms is logged."

## The ML

**7. Why TF-IDF + logistic regression specifically?**
TF-IDF unigrams give sparse lexical features; LogReg is a well-calibrated
linear model that trains in milliseconds and outputs probabilities (needed
for our confidence gate). Benchmarks on small intent datasets (e.g. the
classical baselines on CLINC150-type tasks) show linear TF-IDF models are
competitive at this data scale.

**8. Why unigrams when bigrams capture word order?**
We measured it: bigrams make features sparser and *hurt* on 300 examples —
macro F1 0.766 vs 0.805 with unigrams (GridSearchCV, 5-fold stratified).
With 10× data we'd expect bigrams to win. Say exactly that.

**9. What do the grid-search results mean?**
We searched ngram×C×class_weight (8 combos) by macro F1 under stratified
5-fold CV because accuracy alone hides per-intent imbalance. Winner:
unigrams, C=1.0; class weighting made no difference (classes are balanced by
construction, 20 each — which is why accuracy == macro recall here).

**10. How did you set the 0.30 confidence threshold?**
Empirically, not by intuition: out-of-fold predict_proba on all 320 samples,
sweep maximizing (correctly-accepted + wrongly-rejected)
(`results/threshold_sweep.csv`). The script reads the winning hyperparams
from the training report, and we re-derive the threshold after every retrain —
it moved from 0.125 to 0.30 when the grid winner moved from C=1.0 to C=10.0.
That coupling is exactly why it's scripted, not a constant someone wrote down.

**11. Isn't 0.81 accuracy low?**
For 16 intents from 320 examples with strict cross-validation, it's the
honest range — the confusion matrix shows losses concentrate in lexically
adjacent campus intents (events_clubs↔placements, exam_schedule↔results).
The fix is data, not architecture: doubling examples/intent is the expected
biggest win, and augmentation is listed as future work. We'd rather report
0.81 measured than 0.95 imagined.

**12. How do you prevent the test set leaking into training?**
Physically separate files; the trainer only reads `intents_en.json`;
`validate_data.py` asserts every test intent exists in training and CI-style
checks catch duplicates. The test set was written *after* training data was
frozen.

**13. What is class_weight and why didn't you need it?**
It reweights the loss for imbalanced classes. Our dataset is deliberately
balanced (20 per intent), and the grid confirmed `balanced` changes nothing.

**14. LogReg outputs probabilities — how?**
Softmax over the linear scores (multinomial LogReg). We use the max class
probability as the confidence for the fallback gate, with the caveat that
it's a heuristic confidence, not calibrated probability.

## The pipeline & robustness

**15. What if language detection is wrong?**
Then we translate from the wrong language and the result is usually garbage
that fails the confidence gate → graceful fallback. Measured: 95.0% detection
accuracy; failures cluster on short sister-language pairs (de/nl, es/pt).

**16. Short queries like "ok" or "hola"?**
Explicit handling: a greeting map for known short forms, an ASCII-low-
confidence heuristic defaulting to English, and `None` on empty input →
polite prompt to say more. See `src/detection.py`.

**17. What if the translation API is down?**
Retry with exponential backoff (1s, 2s, 4s), then a fallback provider
(MyMemory), then — if both fail — a degraded, localized graceful reply. We
hit Google's rate limit during development; that's exactly why the chain
exists. Demo script explains how we'd say this live.

**18. What does the disk cache buy?**
Three things: repeat questions are free (latency ~5–10 ms total), evaluation
runs are resumable/reproducible, and the demo can't be killed by a rate limit
because rehearsed questions are already cached.

**19. Code-mixed text like Hinglish?**
Documented limitation, demonstrated live in the demo. Detection heuristics
only patch short ASCII greetings; Hinglish routes to `hi` or `en`
unpredictably. Fix: sentence-level language ID trained on code-switched data
or multilingual embeddings — future work, with a dataset collection plan.

**20. Why Flask and not Streamlit/FastAPI?**
The brief/spec approved with our supervisor says Flask + HTML/CSS/JS, and
Flask is the right size: one route, one template, no build step. (FastAPI
would also be fine; Streamlit is not a real web app for portfolio purposes.)

## The evaluation

**21. Why these 6 languages?**
EN is the pivot; hi/pa are realistic for our campus (native speakers
available to verify the test set); es/fr/de are high-resource languages with
the best free MT quality, so they isolate pivot logic from MT weakness.

**22. Is 30 queries per language enough to claim anything?**
It's a smoke-sized test set — ±1 query ≈ 3.3% — so we report per-language
numbers with that resolution in mind and don't over-claim. Scaling to 100+
per language with fluent-speaker collection is planned work; the pipeline
costs nothing extra to rerun.

**23. Your baseline comparison — is it fair?**
The baseline is the *same* classifier and *same* test set, differing only in
removing the translation stage (ablation). Apples-to-apples by construction;
it's the standard way to show a component's contribution.

**24. Where exactly does your system lose accuracy?**
From `results/` error analysis, in order: (1) MT garbling intent-bearing
phrases, (2) classifier confusion between adjacent campus intents,
(3) detection slips on short text, (4) provider outages → degraded
fallbacks (counted separately, never claimed as accuracy).

## The engineering & process

**25. What did the Phase-1 audit change?**
Our earlier prototype was a Streamlit wrapper calling external LLM APIs —
impressive-looking but it wasn't the approved architecture and had no
measurable ML of its own. We archived it unmodified (`archive/`) and rebuilt
to spec. The audit itself is part of the engineering process story.

**26. How do others reproduce your numbers?**
`pip install -r requirements.txt` (exact pins), `python scripts/train.py`,
`python scripts/tune_threshold.py`, `python scripts/eval_detection.py`,
`python scripts/eval_e2e.py`. Every number in the report tags the script
that produces it.

**27. What would break at 10,000 users?**
The SQLite/dev server and in-process cache — and the free MT quota. Upgrade
path (documented, not built, because YAGNI for a demo): gunicorn workers,
Redis cache, paid MT tier. The *classifier* is O(1)-ish per request (~2 ms)
and not the bottleneck.

**28. Security/privacy: user messages go to Google/MyMemory?**
Yes — that's an honest trade-off of free MT and it's in the report. A campus
deployment would either accept it (public FAQ content) or move to on-premise
MT (e.g. OPUS/M2M models) at higher infra cost.

**29. If you had one more month?**
In order: (1) 5× training data via fluent-speaker collection +
back-translation augmentation; (2) 100-query-per-language human-written test
set; (3) measured comparison vs a multilingual-embedding classifier;
(4) Docker deploy. We have the harness; data collection is the constraint.

**30. What did each of you personally build?**
Bhavesh: classifier, training/tuning scripts, evaluation harness, this viva
doc. Dakksh: pipeline robustness (retry/cache/fallbacks), translation layer,
eval runs. Avi: Flask UI, templates, report/PPT/demo assembly, test-set
language verification coordination. (Adjust to what you actually did — never
claim a teammate's module in the room.)

## Rapid-fire facts to memorize

- 16 intents × 20 = 320 EN training examples; 30×6 test queries
- CV acc 0.8125, macro F1 0.8138 (unigrams, C=10.0)
- Detection 95.0% overall (en/hi/pa 100%); code-switching: 26-case regression suite green
- End-to-end per-language: en 96.7 · hi 90.0 · pa 86.7 · fr 73.3 · es 70.0 · de 53.3 (non-EN avg 74.7%)
- No-pivot baseline: 6.7–23.3% non-EN (avg 13.3%) — pivot lifts 3–13×
- Threshold 0.30 from OOF sweep (was 0.125 under C=1.0; re-derived post-retrain)
- "Wer bin ich?" → de → identity (0.93 live) — regression-tested
- Demo proof: Italian added by one config line; `quando sono gli esami?` works live
- Stage latency: detect ~2 ms, classify ~1–2 ms, MT hop ~1 s cold / ~0 cached; non-EN total ~2–3 s cold
- Numbers verified on pinned deps: sklearn 1.9.1, Flask 3.1.3, langdetect 1.0.9
