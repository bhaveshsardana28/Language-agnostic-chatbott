# PPT outline — 14 slides, ~10 minutes. Build in PowerPoint/Google Slides; every number below is already measured (see results/ and REPORT.md §5).

1. **Title** — Language-Agnostic Chatbot: A Pivot-Translation Based Multilingual
   Conversational System. Team + supervisor.
2. **The problem** — per-language models need per-language data;
   big multilingual LMs are heavy. Demo-campus-student angle: ask in Hindi/Punjabi.
3. **The idea in one slide** — pivot architecture box diagram (7 steps from
   REPORT §3). Emphasize: ONE model, trained once, in English only.
4. **Dataset** — 16 intents × 20 EN examples (identity intent added after a
   live battery caught "Wer bin ich?" → fallback — own it, it's the best
   process slide); separate 30×6 multilingual test set; validator screenshot;
   the duplicate-example catch as a quality anecdote.
5. **Classifier** — TF-IDF + LogReg; grid search table (macro F1 0.814, best
   = unigrams, C=10.0); confusion matrix PNG from results/.
6. **Confidence fallback** — the threshold trade-off table from
   results/threshold_sweep.csv; "a controlled can't-answer beats a wrong answer".
7. **Robustness** — MT provider fallback chain (we hit Google's rate limit
   live), retry+backoff, disk cache; `make test` screenshot.
8. **Results: detection** — 94.4% table; note sister-language confusions.
9. **Results: end-to-end** — pivot vs no-translation baseline table; the bar
   chart (6.7–23.3% without pivot) is the money slide.
10. **Latency** — per-stage table, cold vs cached; MT dominates ⇒ cache wins.
11. **The zero-retraining proof** — live: add Italian = one line in config.py,
    ask a question in Italian, answer arrives in Italian. (DEMO_SCRIPT.md step 6.)
12. **Limitations** — MT error propagation, code-mix, small data; stated
    confidently with the fix for each (REPORT §6) — this slide wins viva points.
13. **Future work** — back-translation augmentation, sentence embeddings for
    code-mix, slots, Docker deploy.
14. **Thanks + questions** — repo URL/QR, team contributions split.

Design: dark background, one accent color, ≤5 bullets/slide, big numbers.
