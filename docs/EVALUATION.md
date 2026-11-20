# Evaluation — how every number is produced

Historical record of the earlier implementation. For current behavior, see the [project README](../README.md).


Rule: no number appears in REPORT/PPT/screens that isn't written by one of
these scripts into `results/`. Pins: `requirements.txt`; Python 3.12.7.

| Artifact | Command | Output |
|---|---|---|
| Classifier CV | `venv/bin/python scripts/train.py` | `results/classifier_report.json`, `confusion_matrix.{csv,png}`, `models/intent_classifier.joblib` |
| Threshold sweep | `venv/bin/python scripts/tune_threshold.py` | `results/threshold_sweep.csv` + recommended value |
| Detection accuracy | `venv/bin/python scripts/eval_detection.py` | `results/detection_{summary,detail}.csv` |
| End-to-end per-lang | `venv/bin/python scripts/eval_e2e.py` | `results/e2e_{summary,detail,errors}.csv` |
| Ablation baseline | `venv/bin/python scripts/eval_e2e.py --baseline` | `results/baseline_{summary,detail}.csv` |
| Live battery | see docs/PROJECT_AUDIT.md §0.3 | `results/phase1_battery.json` |

## Current results (runs of 30 Sep 2026)

- Classifier (16 intents, 320 ex, stratified 5-fold): accuracy **0.8125**,
  macro-F1 **0.8138**; winner unigrams + C=10.0.
- Confidence gate: **0.30** (OOF sweep; maximizes kept-correct + rejected-wrong).
- Detection: **95.0%** overall (en/hi/pa 100%; confusions only de→nl/af/tr,
  es→pt/ca/fr, fr→fi/en on short text).
- E2E intent accuracy (30 queries/lang): en **96.7**, hi **90.0**, pa **86.7**,
  fr **73.3**, es **70.0**, de **53.3** → non-EN avg **74.7%**.
- Ablation (no pivot translation): 6.7–23.3% non-EN → pivot lift 3–13×.
- Latency: detect ~2 ms, classify ~1 ms, MT ~1 s/hop cold / ~0 cached;
  English total ~3–5 ms, non-EN ~2–3 s cold.

## Caveats stated with the numbers

- Test set: 30 queries/language → ±1 query ≈ 3.3%. Treat per-language numbers
  as that precise, no more.
- Test translations were AI-drafted; `_verified` flags in
  `data/test_multilingual.json` track fluent-speaker review (hi/pa first).
- E2E runs depend on free MT availability; the disk cache (`cache/`) makes
  reruns incremental and protects demos, but cold-run latency varies.
- Degraded rows (detection slips / MT outages) are reported separately from
  wrong answers — see REPORT §5.6.
