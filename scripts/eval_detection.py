"""Language-detection accuracy per language, on the multilingual test set.
Offline. Run: venv/bin/python scripts/eval_detection.py
Writes results/detection_summary.csv + results/detection_detail.csv
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.detection import detect_language


def main() -> None:
    test = json.load(open(config.TEST_SET_PATH, encoding="utf-8"))
    # Languages present in the test set (config may support more than evaluated).
    langs = sorted(set(config.SUPPORTED_LANGS) & set(test["queries"][0]["text"]))

    per_lang = {l: {"n": 0, "correct": 0} for l in langs}
    confusions = Counter()
    rows = []
    for q in test["queries"]:
        for lang in langs:
            text = q["text"][lang]
            pred = detect_language(text)
            ok = pred == lang
            per_lang[lang]["n"] += 1
            per_lang[lang]["correct"] += int(ok)
            if not ok:
                confusions[(lang, pred)] += 1
            rows.append((q["id"], lang, pred or "FAIL", int(ok), text[:40]))

    os.makedirs("results", exist_ok=True)
    total_n = sum(v["n"] for v in per_lang.values())
    total_ok = sum(v["correct"] for v in per_lang.values())

    print("Language detection accuracy (30 queries x 6 languages):")
    for lang in langs:
        v = per_lang[lang]
        acc = v["correct"] / v["n"]
        print(f"  {lang}  {v['correct']}/{v['n']}  ({acc:.1%})")
    print(f"  overall  {total_ok}/{total_n}  ({total_ok / total_n:.1%})")
    if confusions:
        print("\nConfusions (gold -> predicted):")
        for (gold, pred), n in confusions.most_common():
            print(f"  {gold} -> {pred}  ({n}x)")

    with open("results/detection_summary.csv", "w") as f:
        f.write("lang,n,correct,accuracy\n")
        for lang in langs:
            v = per_lang[lang]
            f.write(f"{lang},{v['n']},{v['correct']},{v['correct'] / v['n']:.4f}\n")
        f.write(f"ALL,{total_n},{total_ok},{total_ok / total_n:.4f}\n")
    with open("results/detection_detail.csv", "w") as f:
        f.write("id,lang,predicted,correct,text\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")
    print("\nwrote results/detection_summary.csv, results/detection_detail.csv")


if __name__ == "__main__":
    main()
