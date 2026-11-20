"""Evaluate gated English intent predictions on non-overlapping test queries."""
import json
from pathlib import Path
import re
import sys

from sklearn.metrics import accuracy_score, precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from src import classifier


def normalize(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def main():
    training = json.loads(Path(config.INTENTS_PATH).read_text())["intents"]
    examples = {normalize(text) for intent in training.values() for text in intent["examples"]}
    queries = json.loads(Path(config.TEST_SET_PATH).read_text())["queries"]
    model = classifier.load(config.MODEL_PATH)
    assert set(model.classes_) == set(training)
    gold, predicted = [], []
    seen = set()
    for query in queries:
        text = query["text"]["en"]
        key = normalize(text)
        if key in examples or key in seen:
            continue
        seen.add(key)
        label, confidence = classifier.predict(model, text)
        gold.append(query["intent"])
        predicted.append(label if confidence >= config.INTENT_CONFIDENCE_THRESHOLD else "fallback")
    precision, recall, f1, _ = precision_recall_fscore_support(
        gold, predicted, labels=sorted(set(gold)), average="macro", zero_division=0)
    print(f"{len(gold)}/{len(queries)} distinct held-out prompts, {len(set(gold))} represented intents")
    print(f"accuracy={accuracy_score(gold, predicted):.4f} macro precision={precision:.4f} "
          f"recall={recall:.4f} F1={f1:.4f}")


if __name__ == "__main__":
    main()
