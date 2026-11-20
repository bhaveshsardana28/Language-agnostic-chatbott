"""Application languages and paths for the historical evaluation tools."""

SUPPORTED_LANGS = {
    "en": "English",
    "hi": "Hindi",
    "pa": "Punjabi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
}
PIVOT_LANG = "en"

# Historical evaluation only. Below this classifier confidence, reply with a graceful fallback
# instead of a wrong answer. Tuned by scripts/tune_threshold.py on
# out-of-fold predictions (sweep balances kept-correct vs rejected-wrong).
# (was 0.125 for the C=1.0 model; re-derived 30 Sep 2026 against the
# C=10.0 winner — rerun tune_threshold.py after every retrain)
INTENT_CONFIDENCE_THRESHOLD = 0.30

INTENTS_PATH = "data/intents_en.json"          # English training dataset (Phase 2)
TEST_SET_PATH = "data/test_multilingual.json"  # human-written multilingual test set (Phase 2)
MODEL_PATH = "models/intent_classifier.joblib"  # trained TF-IDF + LogReg (Phase 3)
LOG_PATH = "logs/app.log"
