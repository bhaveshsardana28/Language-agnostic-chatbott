"""Offline language, translation cache and Flask compatibility checks."""
from backend import llm, settings
from src import pipeline


def test_config():
    import config
    assert config.PIVOT_LANG == "en"
    assert len(config.SUPPORTED_LANGS) >= 6  # 6 core + Phase-7 demo language(s)
    assert "en" in config.SUPPORTED_LANGS
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


def test_language_meta():
    from src.detection import detect_meta
    m = detect_meta("नमस्ते, आप कैसे हैं?")
    assert m["language"] == "hi" and m["script"] == "Deva" and m["confidence"] > 0.5
    m = detect_meta("Wann sind die Prüfungen?")
    assert m["language"] == "de" and m["script"] == "Latn"
    m = detect_meta("")
    assert m["language"] is None and m["confidence"] == 0.0
    print("test_language_meta OK")


def test_provider_english_and_german(monkeypatch):
    calls = []
    def answer(messages):
        calls.append(messages)
        return "Model reply"
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "chat", answer)
    for question, target in [("Who am I?", "English"), ("Wer bin ich?", "German")]:
        result, status = pipeline.legacy_reply({"message": question})
        assert status == 200 and result["reply"] == "Model reply"
        assert result["intent"] is None and not result["degraded"]
        assert target in calls[-1][0]["content"] and calls[-1][1]["content"] == question


def test_pipeline_retry_and_cache(monkeypatch):
    attempts = []
    def translate(text, target_lang, source_lang):
        attempts.append(text)
        if len(attempts) == 1:
            raise OSError("fixture unavailable")
        return "bonjour"
    monkeypatch.setattr(pipeline, "translate_text", translate)
    monkeypatch.setattr(pipeline.time, "sleep", lambda seconds: None)
    assert pipeline.translate_safe("hello", "fr", "en") == "bonjour"
    assert pipeline.translate_safe("hello", "fr", "en") == "bonjour"
    assert len(attempts) == 2


def test_flask_chat_contract():
    import app
    client = app.app.test_client()
    result = client.post("/chat", json={"message": "How should I prepare for an exam?"}).get_json()
    assert result["intent"] is None and result["confidence"] == 0.0
    assert result["degraded"] and "LLM" in result["reply"]
    assert result["timings"]["total_ms"] >= 0


def test_api_routes():
    import app
    client = app.app.test_client()
    assert client.get("/api/v1/health").json["model"] == settings.LLM_MODEL
    assert client.get("/api/v1/languages").json["it"] == "Italian"
    assert client.get("/api/v1/intents").json == []
