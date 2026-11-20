# Data documentation

Historical record of the earlier implementation. For current behavior, see the [project README](../README.md).


## Training data — `data/intents_en.json`
- **What:** 16 campus-domain intents × 20 English examples = 320 utterances,
  each intent with 4 safe response strings (the static KB).
- **Origin:** hand-written by the team (with AI-assistant drafting);
  English-only BY DESIGN (pivot architecture — no per-language training data).
- **Splits:** none on disk; `scripts/train.py` uses stratified 5-fold CV
  (shuffle, seed 42) — reported CV numbers are out-of-fold, not train scores.
- **Quality gates:** `scripts/validate_data.py` (exactly-20 balance, no
  cross-intent duplicates, ≥3 responses per intent; warns on supported
  languages lacking test coverage).

## Test data — `data/test_multilingual.json`
- **What:** 30 query templates (2 per intent) × 6 languages
  (en/hi/pa/es/fr/de) = 180 utterances. Italian is supported at runtime but
  deliberately NOT in the test set (validator warns, doesn't fail).
- **Origin:** English written by the team; other languages AI-drafted,
  **pending fluent-speaker verification** — tracked per language by the
  `_verified` block in the file header; corrections belong in the report's
  methodology section.
- **Rule:** never used for training. Enforced physically (separate file) and
  by the validator (test intents must exist in training).

## Derived artifacts (all regenerable)
- `models/intent_classifier.joblib` — trained model
- `cache/translations.json` — MT disk cache (checked-in size ~hundreds of
  entries; also the demo's offline safety net; delete freely, it rebuilds)
- `results/*.csv|json|png` — measurements; see docs/EVALUATION.md

## Deliberately NOT used
No downloaded corpora: with 20 examples/intent the marginal value of a big
external dataset is small vs the mislabelling/domain-mismatch risk. Sources
of all numbers are scripts, not screenshots.

Reproducing the historical training charts requires the optional `matplotlib==3.11.2` package in the research environment. The application install excludes plotting and model training.
