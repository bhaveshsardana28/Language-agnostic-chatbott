"""Evaluate cross-lingual document retrieval without calling an LLM.

The benchmark uses several English documents and translated queries. It tests
the retrieval boundary only, making failures reproducible without API keys or
provider variability.

Examples:
    python scripts/eval_rag_multilingual.py
    python scripts/eval_rag_multilingual.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import rag, settings, storage  # noqa: E402


CASES = [
    ("en", "How many employees work on Project Aurora?", "aurora.txt"),
    ("es", "¿Cuántos empleados trabajan en el Proyecto Aurora?", "aurora.txt"),
    ("hi", "प्रोजेक्ट ऑरोरा में कितने कर्मचारी हैं?", "aurora.txt"),
    ("de", "Wo befindet sich der Hauptsitz von Projekt Aurora?", "aurora.txt"),
    ("fr", "Quel est le code interne du projet Aurora?", "aurora.txt"),
    ("es", "¿Cuántos equipos tiene el Proyecto Borealis?", "borealis.txt"),
    ("de", "Wo befindet sich Borealis?", "borealis.txt"),
    ("fr", "Combien de équipes travaille sur Borealis?", "borealis.txt"),
    ("hi", "कोबाल्ट परियोजना में कितनी टीमें हैं?", "cobalt.txt"),
    ("es", "¿Dónde está la sede de Cobalt?", "cobalt.txt"),
]

DOCUMENTS = {
    "aurora.txt": b"Project Aurora has 42 employees. Its headquarters are in Jaipur. The internal project code is AURORA-731.",
    "borealis.txt": b"Project Borealis has 7 teams. Its headquarters are in Pune. The internal project code is BOREALIS-204.",
    "cobalt.txt": b"Project Cobalt has 18 teams. Its headquarters are in Madrid. The internal project code is COBALT-518.",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--min-hit-rate", type=float, default=0.7)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="gaia-rag-eval-") as directory:
        old_path = settings.GAIA_DB_PATH
        settings.GAIA_DB_PATH = os.path.join(directory, "eval.db")
        storage.init_db()
        rag._sessions.clear()
        session_id = "multilingual-evaluation"
        try:
            for filename, content in DOCUMENTS.items():
                rag.add_document(session_id, content, filename, owner_id="evaluation")
            results = []
            for language, query, expected in CASES:
                answer = rag.query(session_id, query, top_k=args.top_k)
                hits = [hit.get("document") for hit in answer["hits"]]
                results.append({
                    "language": language,
                    "query": query,
                    "expected": expected,
                    "hits": hits,
                    "score": answer["hits"][0].get("score") if answer["hits"] else None,
                    "degraded": answer["degraded"],
                    "correct": expected in hits,
                })
            hit_rate = sum(item["correct"] for item in results) / len(results)
            report = {
                "cases": len(results),
                "hit_rate": round(hit_rate, 3),
                "embedding_mode": not any(item["degraded"] for item in results),
                "results": results,
            }
        finally:
            settings.GAIA_DB_PATH = old_path
            rag._sessions.clear()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"RAG multilingual hit rate: {report['hit_rate']:.1%} ({report['cases']} cases)")
        print("mode:", "embeddings" if report["embedding_mode"] else "keyword fallback")
        for item in report["results"]:
            mark = "ok" if item["correct"] else "MISS"
            print(f"[{mark}] {item['language']} -> {item['expected']} ({item['score']})")
    return 0 if report["hit_rate"] >= args.min_hit_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
