"""End-to-end evaluation on the multilingual test set.

Modes:
  venv/bin/python scripts/eval_e2e.py                    # full pivot pipeline (network)
  venv/bin/python scripts/eval_e2e.py --lang hi,es       # subset (translations are cached,
                                                         #  so rerun freely / resume)
  venv/bin/python scripts/eval_e2e.py --baseline         # no-translation baseline:
                                                         #  raw non-English text straight into
                                                         #  the English classifier. Proves the
                                                         #  pivot step is doing the work.

Writes results/e2e_summary.csv, results/e2e_detail.csv, results/e2e_errors.csv
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src import classifier, pipeline

SLEEP = 0.5  # be polite to the translation API; also keeps rate limits away


def main() -> None:
    args = sys.argv[1:]
    baseline = "--baseline" in args

    test = json.load(open(config.TEST_SET_PATH, encoding="utf-8"))
    # Evaluate the languages present in the test set, not every language the
    # app supports (config may gain demo languages the test set doesn't cover).
    test_langs = sorted(set(config.SUPPORTED_LANGS) & set(test["queries"][0]["text"]))
    if "--lang" in args:
        langs = [l for l in args[args.index("--lang") + 1].split(",") if l in test_langs]
    else:
        langs = test_langs
    model = classifier.load(config.MODEL_PATH)

    detail, errors = [], []
    for q in test["queries"]:
        for lang in langs:
            text = q["text"][lang]
            gold = q["intent"]
            if baseline:
                pred, conf = classifier.predict(model, text)
                row = dict(id=q["id"], lang=lang, gold=gold, pred=pred, conf=conf,
                           correct=int(pred == gold), degraded=0,
                           detect_ms="", translate_in_ms="", classify_ms="",
                           respond_ms="", total_ms="")
            else:
                t0 = time.perf_counter()
                r = pipeline.respond(text)
                if r["timings"].get("total_ms") is None:
                    r["timings"]["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                pred = r["intent"] or "TRANSLATION_FAILED"
                row = dict(id=q["id"], lang=lang, gold=gold, pred=pred,
                           conf=r["confidence"], correct=int(r["intent"] == gold),
                           degraded=int(r["degraded"]),
                           **{k: r["timings"].get(k, "") for k in
                              ("detect_ms", "translate_in_ms", "classify_ms", "respond_ms", "total_ms")})
                if r["degraded"] or pred != gold:
                    errors.append(dict(id=q["id"], lang=lang, gold=gold, pred=pred,
                                       conf=r["confidence"], text=text,
                                       english=r.get("english", "")))
                time.sleep(SLEEP if lang != "en" else 0)
            detail.append(row)

    tag = "baseline" if baseline else "e2e"
    os.makedirs("results", exist_ok=True)

    print(f"\n== {tag.upper()} == per-language intent accuracy ({len(test['queries'])} queries/lang):")
    summary = []
    for lang in langs:
        rows = [r for r in detail if r["lang"] == lang]
        n = len(rows)
        acc = sum(r["correct"] for r in rows) / n if n else 0
        deg = sum(r["degraded"] for r in rows)
        avg_total = _avg([r["total_ms"] for r in rows if r["total_ms"] != ""])
        avg_tr = _avg([r["translate_in_ms"] for r in rows if r["translate_in_ms"] != ""])
        avg_clf = _avg([r["classify_ms"] for r in rows if r["classify_ms"] != ""])
        summary.append((lang, n, acc, deg, avg_total, avg_tr, avg_clf))
        print(f"  {lang}  acc={acc:.1%}  degraded={deg}  "
              f"avg_total={avg_total:.0f}ms (translate_in={avg_tr:.0f}ms, classify={avg_clf:.1f}ms)")

    with open(f"results/{tag}_summary.csv", "w") as f:
        f.write("lang,n,accuracy,degraded,avg_total_ms,avg_translate_in_ms,avg_classify_ms\n")
        for lang, n, acc, deg, at, atr, acl in summary:
            f.write(f"{lang},{n},{acc:.4f},{deg},{at:.1f},{atr:.1f},{acl:.1f}\n")

    with open(f"results/{tag}_detail.csv", "w") as f:
        f.write("id,lang,gold,pred,conf,correct,degraded,detect_ms,translate_in_ms,classify_ms,respond_ms,total_ms\n")
        for r in detail:
            f.write(",".join(str(r[k]) for k in
                             ("id", "lang", "gold", "pred", "conf", "correct", "degraded",
                              "detect_ms", "translate_in_ms", "classify_ms", "respond_ms", "total_ms")) + "\n")

    if errors:
        with open(f"results/{tag}_errors.csv", "w") as f:
            f.write("id,lang,gold,pred,conf,text,english\n")
            for e in errors:
                f.write(",".join(str(e[k]).replace(",", ";") for k in
                                 ("id", "lang", "gold", "pred", "conf", "text", "english")) + "\n")
        print(f"\n{len(errors)} mismatches/degraded -> results/{tag}_errors.csv (error analysis source)")

    print(f"\nwrote results/{tag}_summary.csv, results/{tag}_detail.csv")


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


if __name__ == "__main__":
    main()
