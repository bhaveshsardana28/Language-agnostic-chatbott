"""Train + tune the intent classifier. Run: venv/bin/python scripts/train.py

What it does (all numbers land in results/ so the report is reproducible):
  1. Load data/intents_en.json
  2. Grid-search a small, honest grid with 5-fold stratified CV
     (ngram range x C x class_weight), scoring = macro F1
  3. Refit the winner on all 300 examples, save to models/
  4. Report: per-intent precision/recall/F1, macro F1, confusion matrix
"""

import json
import os
import sys
from collections import Counter

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict

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
    print(f"{len(X)} examples, {len(set(y))} intents")
    print("per-intent counts:", dict(Counter(y)))

    grid = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "clf__C": [1.0, 10.0],
        "clf__class_weight": [None, "balanced"],
    }
    base = classifier.build()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    search = GridSearchCV(base, grid, scoring="f1_macro", cv=cv, n_jobs=-1)
    search.fit(X, y)

    print("\nGrid results (macro F1):")
    for params, score in sorted(
        zip(search.cv_results_["params"], search.cv_results_["mean_test_score"]),
        key=lambda t: -t[1],
    ):
        print(f"  {score:.4f}  {params}")
    print(f"\nBest: macro F1 = {search.best_score_:.4f}  {search.best_params_}")

    # Out-of-fold predictions with the winner -> honest held-out metrics
    best = search.best_estimator_
    y_pred = cross_val_predict(best, X, y, cv=cv)
    labels = sorted(set(y))
    report = classification_report(y, y_pred, labels=labels, digits=4, output_dict=True)
    cm = confusion_matrix(y, y_pred, labels=labels)

    print("\nClassification report (5-fold cross_val_predict):")
    print(classification_report(y, y_pred, labels=labels, digits=4))

    # Persist everything the report needs
    os.makedirs("results", exist_ok=True)
    os.makedirs(os.path.dirname(config.MODEL_PATH), exist_ok=True)
    best.fit(X, y)
    classifier.save(best, config.MODEL_PATH)

    intents_list = labels
    np.savetxt("results/confusion_matrix.csv", cm, fmt="%d", delimiter=",")
    with open("results/classifier_report.json", "w") as f:
        json.dump(
            {
                "n_examples": len(X),
                "n_intents": len(labels),
                "labels": intents_list,
                "best_params": search.best_params_,
                "cv_macro_f1": round(search.best_score_, 4),
                "cv_accuracy": round(report["accuracy"], 4),
                "cv_macro_precision": round(report["macro avg"]["precision"], 4),
                "cv_macro_recall": round(report["macro avg"]["recall"], 4),
                "cv_macro_f1_oof": round(report["macro avg"]["f1-score"], 4),
                "per_intent": {
                    k: {m: round(vv, 4) for m, vv in v.items() if m != "support"}
                    for k, v in report.items()
                    if k in intents_list
                },
                "grid": [
                    {"params": {k: str(v) for k, v in p.items()}, "f1_macro": round(s, 4)}
                    for p, s in zip(search.cv_results_["params"], search.cv_results_["mean_test_score"])
                ],
            },
            f,
            indent=2,
        )

    # Confusion matrix PNG for the report/PPT
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import ConfusionMatrixDisplay

        fig, ax = plt.subplots(figsize=(10, 9))
        ConfusionMatrixDisplay(cm, display_labels=labels).plot(
            ax=ax, xticks_rotation=45, cmap="Blues", colorbar=False
        )
        fig.tight_layout()
        fig.savefig("results/confusion_matrix.png", dpi=150)
        print("wrote results/confusion_matrix.png")
    except ImportError:
        print("(matplotlib not installed — skipped confusion_matrix.png, CSV still written)")

    print(f"\nSaved model -> {config.MODEL_PATH}")
    print("Saved metrics -> results/classifier_report.json, results/confusion_matrix.csv")


if __name__ == "__main__":
    main()
