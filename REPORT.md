# Language-Agnostic Chatbot: A Pivot-Translation Based Multilingual Conversational System

**Final-Year Project Report — working draft (numbers marked [RUN: ...] refresh by re-running the named script)**

The NorthCap University, Gurugram — B.Tech CSE (AI/ML)
Bhavesh Sardana (23csu070) · Dakksh Sharma (23csu081) · Avi (23csu061)
Supervisor: Ms. Meghna Sharma

---

## 1. Abstract

Multilingual chatbots are typically built one of two ways: train a separate
intent model per language (data-expensive), or use a large multilingual
language model (compute-expensive, opaque, hard to run on a laptop). We
implement and evaluate a third way: a **pivot translation** architecture where
every user message is translated into English, classified by a **single**
English intent model (TF-IDF + logistic regression), answered from a static
response knowledge base, and translated back. Adding a language requires
**zero new training data**. We evaluate on a 6-language test set
(English, Hindi, Punjabi, Spanish, French, German; 30 queries × 6 languages)
and find end-to-end intent accuracy of **74.7% averaged over the five
non-English languages** (96.7% on English) — versus 6.7–23.3% for the same
classifier without the pivot step, which quantitatively justifies the
architecture. Language detection achieves 95.0% per-query accuracy (raised from 94.4% by the
segment-level code-switching upgrade — one more short-German query recovered). We analyse where the pipeline loses accuracy
(translation error propagation dominates) and show a live demo extension:
adding Italian support by changing one configuration line.

## 2. Problem statement

A university wants one chatbot that answers campus questions for students
writing in their own language. Per-language intent models don't scale (new
training data per language). Large multilingual LMs do scale but are
expensive, slow, non-deterministic and un-auditable for a fixed FAQ domain.
**Goal:** bounded-domain, intent-driven multilingual chatbot with (a) no
per-language training, (b) laptop-class inference, (c) measurable accuracy,
(d) graceful degradation instead of wrong answers.

## 3. Architecture

```
user message (hi/pa/es/fr/de/en)
  1. language detection        langdetect + short-text heuristics
  2. translate -> English      deep-translator (Google; fallback: MyMemory)
                               retry w/ exponential backoff + disk cache
  3. intent classification     TF-IDF (unigrams) + Logistic Regression
  4. confidence gate           p < 0.30  -> localized "didn't understand"
  5. response selection        static intent->response knowledge base
  6. translate back            same provider chain, cached
  7. Flask web UI              language + intent + confidence badge
```

Design choices and their reasons (each is a viva answer):

| Choice | Why |
|---|---|
| Pivot via English | One model total, not one per language; English MT quality is the strongest available for free APIs |
| TF-IDF + LogReg | Trains in seconds, white-box (inspectable weights), beats bigrams on small data (measured: 0.805 vs 0.766 macro F1), no GPU |
| Static response KB | Deterministic, auditable, no hallucination — correct choice for institutional FAQs |
| Confidence fallback | A controlled "I don't know" beats a confident wrong answer; threshold set by out-of-fold sweep, not vibes |
| Provider fallback chain | Google Translate rate-limits (we hit this live); MyMemory is a free no-key backup |
| Disk cache for translations | Free reruns; latency collapses on repeat queries; eval reproducibility |

## 4. Dataset

**Training (English only):** 16 campus intents × 20 examples = 320 utterances,
hand-written (greetings, identity, goodbye, thanks, timetable, exams, results,
fees, hostel, library, attendance, placements, clubs/events, transport,
admissions, food). The **identity** intent was added after a Phase-1 live
battery exposed that "Wer bin ich?" (who am I) fell to fallback — it now
returns a safe localized answer and is covered by a regression test
(`test_wer_bin_ich_german`). Validated by `scripts/validate_data.py`
(balance, duplicates, KB coverage) — it caught a cross-intent duplicate
during development (`hostel mess menu` in both *hostel* and *food_canteen*).

**Multilingual test set:** 30 query templates (2 per intent) written in
English, then rendered in all 6 languages. Drafts produced with assistant
help, **pending verification by fluent speakers** (Hindi/Punjabi on campus;
es/fr/de verified by student community); any corrections are logged here:
- [ ] hi verified by: ___
- [ ] pa verified by: ___
- [ ] es verified by: ___
- [ ] fr verified by: ___
- [ ] de verified by: ___

Never used for training. This separation is stated in the viva.

## 5. Experiments

### 5.1 Classifier (English, 5-fold stratified CV) — [RUN: scripts/train.py]

| Metric | Value |
|---|---|
| CV accuracy | 0.8125 |
| Macro precision / recall / F1 | 0.8220 / 0.8125 / 0.8138 |
| Best config | unigrams, C=10.0, no class weight |
| Grid | ngram (1,1)/(1,2) × C 1/10 × class_weight none/balanced |

Confusion matrix: `results/confusion_matrix.png`. Weakest intents:
events_clubs (F1 0.57), results (0.70), exam_schedule (0.73) — lexical
overlap with placements/hostel/admissions is the failure mode.

### 5.2 Confidence threshold — [RUN: scripts/tune_threshold.py]

The gate is chosen by out-of-fold sweep against the *current* best model
(the script reads `best_params` from `classifier_report.json` — never
hardcoded). With unigrams/C=10.0 the optimum is **0.30**, trading a few
correct-but-uncertain answers for far fewer confident wrong ones; the full
kept-correct vs rejected-wrong table is `results/threshold_sweep.csv`.
Re-derived after every retrain (it moved from 0.125 when C changed 1.0→10.0).

### 5.3 Language detection — [RUN: scripts/eval_detection.py]

| Lang | Accuracy |
|---|---|
| en | 100% |
| hi | 100% |
| pa | 100% |
| de | 86.7% |
| es | 90.0% |
| fr | 93.3% |
| **overall** | **95.0%** |

Confusions only between related languages (de→nl/af, es→pt/ca, fr→fi/en)
on short strings — the classic langdetect failure mode.

### 5.4 End-to-end intent accuracy (the headline) — [RUN: scripts/eval_e2e.py]

| Lang | Pivot pipeline | No-translation baseline |
|---|---|---|
| en | 96.7% | 96.7% |
| hi | 90.0% | 6.7% |
| pa | 86.7% | 6.7% |
| es | 70.0% | 16.7% |
| fr | 73.3% | 23.3% |
| de | 53.3% | 13.3% |
| **non-EN avg** | **74.7%** | **13.3%** |

Degraded (declined-gracefully) rows in the final run: de 4, es 2, fr 1
(detection slips), hi 2 (outbound MT failed; answered in English with the
degraded flag — intent still correct).

(The baseline feeds raw non-English text to the English classifier — the
controlled ablation proving the pivot stage does the work. Numbers from
`scripts/eval_e2e.py` run 30 Sep 2026; `results/e2e_summary.csv`.)

### 5.5 Latency per stage — [from results/e2e_detail.csv, runs 30 Sep 2026]

| Stage | Cold (first hit) | Warm (cached) |
|---|---|---|
| detect | ~2 ms (one-time ~140 ms langdetect warmup) | ~2 ms |
| translate in | ~950–1200 ms avg | ~0 ms (disk cache) |
| classify | ~1–2 ms | ~1–2 ms |
| respond (incl. translate out) | ~1–2 s | ~0.4–1.0 s |
| **total, English** | ~5 ms | ~5 ms |
| **total, non-English** | ~2.0–3.0 s | ~0.4–1.1 s |

Translation is >99% of non-English latency cold and still dominates warm — the
classifier is noise (1–2 ms). This is the quantitative justification for the
disk cache and for never translating English input.

### 5.6 Error analysis — [from results/e2e_errors.csv, 41 flagged of 180]

1. **Detection slips on short sister-language text (7 rows: de 4, es 2, fr 1).**
   e.g. "bis morgen" detected as Norwegian; the query lands on an
   unsupported language and the system declines gracefully — counted as
   degraded, not as a wrong answer. Matches §5.3's confusion list exactly.
2. **MT noise drops confidence below the 0.30 gate → localized fallback
   (23 rows, spread across all five non-EN languages).** The system refuses
   rather than guesses; conservative but honest, and the dominant
   accuracy-limiting stage.
3. **Adjacent campus intents collide after translation (8 rows):**
   events_clubs→exam_schedule ×3, food_canteen→hostel ×2, and one each of
   hostel/placements/admission_info→exam_schedule. Once MT renders
   "when do admissions open" ≈ "when do exams start", unigram TF-IDF can't
   always separate them. The fix is training data, not a bigger model.
4. **Outbound MT failure (3 rows: hi 2, thanks —)** degrades to an English
   answer with the flag set; intent was still correct.
German's 53.3% concentrates categories 1+2 — consistent with its lowest
detection score (86.7%).

## 6. Limitations (honest)

- MT errors propagate; a mistranslated entity can flip the intent.
- Code-mixed text (Hinglish) is the hardest realistic input; detection
  heuristics handle only short ASCII greetings today.
- 300-example training set bounds classifier accuracy; the test set (30/lang)
  bounds statistical resolution (±1 query ≈ 3.3%).
- Static KB can't answer beyond its intents; by design, it says so instead
  of guessing.

## 7. Future work

- More examples per intent (100+) + augmentation via back-translation.
- Sentence embeddings (e.g. LaBSE) for code-mixed robustness — measured
  comparison before any adoption.
- Slot filling (dates, course codes) on top of intents.
- Conversation context for follow-ups ("and for tomorrow?").
- Deploy: Docker + gunicorn (repo structure already supports it).

## 8. Conclusion

One English model + free MT serves 7 languages with **78.3% average
end-to-end accuracy over the 6 evaluated languages (74.7% on the five
non-English ones)**, beats the no-pivot baseline by 3–13× on non-English
input, runs on a laptop, and extended to a 7th language (Italian) with a
one-line config change — demonstrating the core claim: **language coverage
without language-specific training data**.
