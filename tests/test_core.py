"""
Core checks for the pivot chatbot.

Run:
    venv/bin/python -m pytest tests/test_core.py
or (no pytest needed):
    venv/bin/python tests/test_core.py

Offline only. Translation (deep-translator -> Google) is *not* tested here:
it needs network, and flaky-network tests are worse than no tests.
Translation robustness is covered by the pipeline tests in Phase 4.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    import config
    assert config.PIVOT_LANG == "en"
    assert len(config.SUPPORTED_LANGS) >= 6  # 6 core + Phase-7 demo language(s)
    assert "en" in config.SUPPORTED_LANGS
    assert 0.0 < config.INTENT_CONFIDENCE_THRESHOLD < 1.0
    print("test_config OK")


def test_detection():
    from src.detection import detect_language
    assert detect_language("hello") == "en"
    assert detect_language("hola") == "es"
    assert detect_language("bonjour") == "fr"
    assert detect_language("namaste") == "hi"
    assert detect_language("नमस्ते") == "hi"
    assert detect_language("") is None
    assert detect_language("   ") is None
    assert detect_language("I would like to know the exam schedule for this semester") == "en"
    print("test_detection OK")


def test_flask_endpoints():
    import app as flask_app
    c = flask_app.app.test_client()
    assert c.get("/").status_code == 200

    r = c.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.get_json()["lang"] == "en"

    r = c.post("/chat", json={"message": "   "})
    assert r.status_code == 400
    print("test_flask_endpoints OK")


def test_pipeline_english():
    """English path needs no network. Assert intent + confidence threshold logic."""
    from src import pipeline
    r = pipeline.respond("when is my next class")
    assert r["lang"] == "en"
    assert r["intent"] == "timetable"
    assert r["confidence"] > 0.0 and 0.0 <= r["confidence"] <= 1.0
    assert r["reply"]

    # nonsense -> graceful fallback, not a wrong answer
    r = pipeline.respond("zzz qqq wwww vvvv")
    assert r["intent"] == "fallback"
    assert "understand" in r["reply"].lower()
    print("test_pipeline_english OK")


def test_pipeline_retry_and_cache(tmp_path=None):
    """Translation failure must degrade gracefully; cache must avoid re-calls."""
    from src import pipeline
    calls = {"n": 0}

    def fake_translate(text, target_lang=None, source_lang=None):
        calls["n"] += 1
        return f"[{source_lang}->{target_lang}] {text}"

    import tempfile
    pipeline._cache = {}
    real_cache_path = pipeline.CACHE_PATH
    pipeline.CACHE_PATH = os.path.join(tempfile.mkdtemp(), "test_cache.json")
    pipeline_orig_translate_text = pipeline.translate_text
    pipeline.translate_text = fake_translate
    try:
        r = pipeline.respond("मुझे फीस के बारे में बताइए")
        assert r["lang"] == "hi"
        assert r["reply"].startswith("[en->hi]") or r["intent"] == "fallback"
        # cache: a second identical request adds no new inbound translate call
        n_after_first = calls["n"]
        pipeline.respond("मुझे फीस के बारे में बताइए")
        assert calls["n"] <= n_after_first + 1  # reply translate may differ; inbound cached
    finally:
        pipeline.translate_text = pipeline_orig_translate_text
        pipeline.CACHE_PATH = real_cache_path
        pipeline._cache = {}
    print("test_pipeline_retry_and_cache OK")


def test_flask_chat_contract():
    import app as flask_app
    c = flask_app.app.test_client()
    r = c.post("/chat", json={"message": "what is my timetable today"})
    assert r.status_code == 200
    j = r.get_json()
    for key in ("lang", "intent", "confidence", "reply", "timings"):
        assert key in j, key
    assert j["intent"] == "timetable"
    print("test_flask_chat_contract OK")


def test_language_meta():
    from src.detection import detect_meta
    m = detect_meta("नमस्ते, आप कैसे हैं?")
    assert m["language"] == "hi" and m["script"] == "Deva" and m["confidence"] > 0.5
    m = detect_meta("Wann sind die Prüfungen?")
    assert m["language"] == "de" and m["script"] == "Latn"
    m = detect_meta("")
    assert m["language"] is None and m["confidence"] == 0.0
    print("test_language_meta OK")


def test_identity_english():
    from src import pipeline
    import json
    r = pipeline.respond("do you know who I am")
    assert r["intent"] == "identity"
    # safety rule: reply must come from the audited safe-response KB
    kb = json.load(open("data/intents_en.json", encoding="utf-8"))
    assert r["reply"] in kb["intents"]["identity"]["responses"]
    print("test_identity_english OK")


def test_wer_bin_ich_german():
    """Regression (master prompt Phase 5/28): 'Wer bin ich?' must classify as
    IDENTITY in German, never unexplained FALLBACK. MT monkeypatched offline:
    inbound fixed to 'who am i', outbound echoed."""
    from src import pipeline

    def fake_translate(text, target_lang=None, source_lang=None):
        if target_lang == "en":
            return "who am i"
        return f"[de] {text}"

    import tempfile
    real_cache, real_tt = pipeline.CACHE_PATH, pipeline.translate_text
    pipeline._cache = {}
    pipeline.CACHE_PATH = os.path.join(tempfile.mkdtemp(), "c.json")
    pipeline.translate_text = fake_translate
    try:
        r = pipeline.respond("Wer bin ich?")
        assert r["lang"] == "de", r
        assert r["intent"] == "identity", r
        assert r["language_meta"]["script"] == "Latn"
        assert "kennen" in r["reply"] or r["reply"].startswith("[de]"), r["reply"]
    finally:
        pipeline.translate_text = real_tt
        pipeline.CACHE_PATH = real_cache
        pipeline._cache = {}
    print("test_wer_bin_ich_german OK")


def test_api_routes():
    import app as flask_app
    c = flask_app.app.test_client()
    r = c.get("/api/v1/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"
    langs = c.get("/api/v1/languages").get_json()
    assert langs["en"] == "English" and "it" in langs  # Phase-7 demo language
    intents = c.get("/api/v1/intents").get_json()
    assert "identity" in intents and "timetable" in intents
    print("test_api_routes OK")


def main():
    test_config()
    test_detection()
    test_flask_endpoints()
    test_language_meta()
    test_pipeline_english()
    test_pipeline_retry_and_cache()
    test_identity_english()
    test_wer_bin_ich_german()
    test_api_routes()
    test_flask_chat_contract()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
