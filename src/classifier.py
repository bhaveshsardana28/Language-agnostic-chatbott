"""Intent classifier: TF-IDF + Logistic Regression.

The single English model everything routes through. Kept deliberately
small: one sklearn Pipeline, saved with joblib. Why this design is
defensible is in REPORT.md ("Why not transformers").
"""

from __future__ import annotations

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def build(ngram_max: int = 2, C: float = 10.0, class_weight=None) -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, ngram_max),
                sublinear_tf=True,      # dampens long-text term spam
                strip_accents=None,     # keep accents; text is English here anyway
            )),
            ("clf", LogisticRegression(
                C=C,
                class_weight=class_weight,
                max_iter=2000,
                random_state=42,
            )),
        ]
    )


def save(model: Pipeline, path: str) -> None:
    joblib.dump(model, path)


def load(path: str) -> Pipeline:
    return joblib.load(path)


def predict(model: Pipeline, text: str) -> tuple[str, float]:
    """Return (intent, confidence). Confidence = max class probability."""
    proba = model.predict_proba([text])[0]
    best = proba.argmax()
    return model.classes_[best], float(proba[best])
