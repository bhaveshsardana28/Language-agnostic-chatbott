"""Validate the dataset files. Run: venv/bin/python scripts/validate_data.py

Catches the classic dataset bugs before training does: wrong counts,
duplicate examples, missing responses, test-set intents with no training
intent, missing language columns.
"""

import json
import sys
from collections import Counter

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
import config

sys.path.insert(0, ".")  # noqa


def main() -> int:
    ok = True

    data = json.load(open(config.INTENTS_PATH, encoding="utf-8"))
    intents = data["intents"]
    n_ex = {name: len(spec["examples"]) for name, spec in intents.items()}
    print(f"Training set: {len(intents)} intents, {sum(n_ex.values())} examples")
    for name in sorted(intents):
        n = n_ex[name]
        flag = "" if n == 20 else "  <-- expected 20"
        if n != 20:
            ok = False
        print(f"  {name:15s} {n:3d}{flag}")
        if len(intents[name]["responses"]) < 3:
            print(f"  {name:15s} only {len(intents[name]['responses'])} responses (min 3)")
            ok = False

    all_ex = [e.lower().strip() for spec in intents.values() for e in spec["examples"]]
    dupes = [t for t, c in Counter(all_ex).items() if c > 1]
    if dupes:
        print("DUPLICATE training examples:", dupes)
        ok = False

    test = json.load(open(config.TEST_SET_PATH, encoding="utf-8"))
    langs_needed = set(config.SUPPORTED_LANGS)
    missing_lang, bad_intent = [], []
    test_langs = Counter()
    for q in test["queries"]:
        missing = langs_needed - set(q["text"])
        if missing:
            missing_lang.append((q["id"], missing))
        if q["intent"] not in intents:
            bad_intent.append((q["id"], q["intent"]))
        for lang in q["text"]:
            test_langs[lang] += 1
    print(f"\nTest set: {len(test['queries'])} queries")
    for lang in sorted(langs_needed):
        print(f"  {lang}: {test_langs.get(lang, 0)} texts")
    uncovered = sorted(langs_needed - set(test["queries"][0]["text"]))
    if uncovered:
        print(f"WARNING: supported languages with no test coverage: {uncovered} "
              f"(demo-only languages are acceptable but must be labelled as such)")
    if missing_lang:
        # a query missing a language the test set DOES cover = real error
        real_missing = [(i, m) for i, m in missing_lang if not m <= set(uncovered)]
        if real_missing:
            print("MISSING languages in queries:", real_missing)
            ok = False
    if bad_intent:
        print("Test intents with no training data:", bad_intent)
        ok = False

    print("\nVALIDATION", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
