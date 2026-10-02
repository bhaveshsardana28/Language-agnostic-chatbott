"""Pick INTENT_CONFIDENCE_THRESHOLD from out-of-fold predictions.

Run: venv/bin/python scripts/tune_threshold.py
Writes results/threshold_sweep.csv and prints the recommended value —
paste it into config.py after checking the trade-off table.
"""

import json
import os
import sys

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_predict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import classifier


def main() -> None:
    data = json.load(open(config.INTENTS_PATH, encoding="utf-8"))
    X, y = [], []
    for intent, spec in data["intents"].items():
        for ex in spec["examples"]:
            X.append(ex)
            y.append(intent)
    y = np.array(y)

    # Match the winning hyperparams recorded by train.py — never hardcode.
    report = json.load(open("results/classifier_report.json"))
    bp = report["best_params"]
    ngram_max = bp["tfidf__ngram_range"][-1]
    print(f"Using train.py winner: C={bp['clf__C']}, ngram_max={ngram_max}")

    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    model = classifier.build(ngram_max=ngram_max, C=bp["clf__C"])
    proba = cross_val_predict(model, X, y, cv=cv, method="predict_proba")
    conf = proba.max(axis=1)
    classes = np.sort(np.unique(y))
    correct = classes[proba.argmax(axis=1)] == y

    print(f"confidence: correct mean {conf[correct].mean():.3f} | "
          f"wrong mean {conf[~correct].mean():.3f} | n wrong {(~correct).sum()}\n")

    rows, best_t, best_score = [], 0.0, -1
    for t in np.arange(0.10, 0.60, 0.025):
        kc = int(((conf >= t) & correct).sum())
        rw = int(((conf < t) & ~correct).sum())
        fr = int(((conf < t) & correct).sum())
        wa = int(((conf >= t) & ~correct).sum())
        rows.append((round(t, 3), kc, rw, fr, wa))
        if kc + rw > best_score:
            best_score, best_t = kc + rw, t
        print(f"t={t:.3f}  kept-correct={kc:3d}  wrong-rejected={rw:3d}  "
              f"false-rejects={fr:3d}  wrong-accepted={wa:3d}")

    os.makedirs("results", exist_ok=True)
    with open("results/threshold_sweep.csv", "w") as f:
        f.write("threshold,kept_correct,wrong_rejected,false_rejects,wrong_accepted\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")

    print(f"\nRecommended INTENT_CONFIDENCE_THRESHOLD = {best_t:.3f} "
          f"(currently {config.INTENT_CONFIDENCE_THRESHOLD})")


if __name__ == "__main__":
    main()
