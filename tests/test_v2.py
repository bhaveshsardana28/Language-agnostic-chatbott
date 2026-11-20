"""v2 (FastAPI/GAIA) tests — fully offline: LLM and MT are monkeypatched.
Run: venv/bin/python tests/test_v2.py    (or via pytest)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from backend import llm, memory, router, settings
from backend.main import app
from src import pipeline

client = TestClient(app, raise_server_exceptions=False)


def _parse_sse(text: str):
    out = []
    for frame in text.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data:"):
            out.append(json.loads(frame[5:].strip()))
    return out


def _post(message, cid=None):
    r = client.post("/api/v1/chat", json={"message": message, "conversation_id": cid})
    assert r.status_code == 200, r.text
    return _parse_sse(r.text)


def _patch_llm(reply="(llm reply)"):
    def fake_stream(messages, model=None):
        for w in reply.split(" "):
            yield w + " "
    llm.stream_chat = fake_stream
    settings.LLM_API_KEY = "test-key"  # pass the provider gate; calls are mocked anyway


def _unpatch_all():
    import importlib
    importlib.reload(llm)  # restore real stream_chat (not called in these tests)
    settings.LLM_API_KEY = ""


def test_health_and_catalog():
    r = client.get("/")
    assert r.status_code == 200 and 'id="welcome-title"' in r.text and "<title>LANGUAGE AGNOSTIC CHATBOT · Multilingual workspace</title>" in r.text  # default root is the V2 frontend
    legacy = client.get("/legacy")
    assert legacy.status_code == 200 and "<title>LANGUAGE AGNOSTIC CHATBOT</title>" in legacy.text
    h = client.get("/api/v1/health").json()
    assert h["status"] == "ok" and "llm_provider" in h
    assert "it" in client.get("/api/v1/languages").json()
    intents = client.get("/api/v1/intents").json()
    assert intents == {"campus_kb": [], "routes": ["translate", "web", "document", "general"]}
    print("test_health_and_catalog OK")


def test_general_route_stream_mocked():
    _patch_llm("The fuzzy answer streams well")
    try:
        ev = _post("Explain quantum computing")
        meta, done = ev[0], ev[-1]
        assert meta["type"] == "meta" and meta["route"] == "general"
        text = "".join(e.get("text", "") for e in ev if e["type"] == "delta")
        assert "fuzzy answer" in text
        assert done["type"] == "done" and done["latency_ms"] >= 0
        assert meta["conversation_id"]
    finally:
        _unpatch_all()
    print("test_general_route_stream_mocked OK")


def test_language_switch_per_message():
    _patch_llm("ok")
    try:
        e1 = _post("Explain machine learning")
        cid = e1[0]["conversation_id"]
        e2 = _post("summarize this in Hindi", cid)
        assert e2[0]["language_meta"]["language"] == "en"        # detection per-message
        assert e2[0]["response_lang"] == "hi"                    # explicit instruction wins
        e3 = _post("Jetzt auf Deutsch.", cid)
        assert e3[0]["language_meta"]["language"] == "de"
        assert e3[0]["response_lang"] == "de"
    finally:
        _unpatch_all()
    print("test_language_switch_per_message OK")


def test_translate_route_and_context():
    seen = {}

    def fake_translate(text, target, source, retries=3):
        seen["args"] = (text, target, source)
        return f"<{target}>{text}"

    real = pipeline.translate_safe
    pipeline.translate_safe = fake_translate
    try:
        ev = _post("Translate 'good morning' into French")
        assert ev[0]["route"] == "translate"
        assert any("<fr>good morning" in e.get("text", "") for e in ev)
        # bare "translate into X" uses the last assistant turn (context)
        cid = ev[0]["conversation_id"]
        memory.append(cid, "assistant", "hello world")
        _post("Translate into German", cid)
        assert seen["args"][0] == "hello world" and seen["args"][1] == "de"
    finally:
        pipeline.translate_safe = real
    print("test_translate_route_and_context OK")


def test_education_questions_use_general_model():
    _patch_llm("Consult the relevant institution.")
    try:
        for prompt in ("When are my exams?", "How do university admissions work?", "Explain a Python class"):
            events = _post(prompt)
            assert events[0]["route"] == "general"
            assert "Consult the relevant institution." in "".join(e.get("text", "") for e in events)
            assert events[-1]["type"] == "done"
    finally:
        _unpatch_all()


def test_memory_context_and_bounds():
    captured = {}

    def fake_stream(messages, model=None):
        captured["n_user"] = sum(1 for m in messages if m["role"] == "user")
        yield "noted"
    llm.stream_chat = fake_stream
    settings.LLM_API_KEY = "test-key"  # pass the provider gate; calls are mocked
    try:
        ev = _post("Why is the sky blue?")
        cid = ev[0]["conversation_id"]
        _post("Explain it like I am five years old", cid)
        assert captured["n_user"] >= 2  # follow-up sent with prior user turn
        assert memory.last_assistant(cid) == "noted"
        for i in range(settings.MEMORY_TURNS * 3):
            memory.append(cid, "user", f"m{i}")
        assert len(memory.history(cid)) <= settings.MEMORY_TURNS * 2
    finally:
        _unpatch_all()
    print("test_memory_context_and_bounds OK")


def test_limits_validation_and_llm_missing():
    assert client.post("/api/v1/chat", json={"message": " "}).status_code == 400
    big = "x " * (settings.MAX_MESSAGE_CHARS // 2 + 10)
    assert client.post("/api/v1/chat", json={"message": big}).status_code == 413

    # general chat without a configured key must fail gracefully, not crash
    real_key, real_provider = settings.LLM_API_KEY, settings.LLM_PROVIDER
    settings.LLM_API_KEY, settings.LLM_PROVIDER = "", "groq"
    try:
        ev = _post("Explain recursion")
        err = [e for e in ev if e["type"] == "error"]
        assert err and "LLM" in err[0]["message"]
    finally:
        settings.LLM_API_KEY, settings.LLM_PROVIDER = real_key, real_provider
    print("test_limits_validation_and_llm_missing OK")


def test_conversation_delete():
    ev = _post("hello")
    cid = ev[0]["conversation_id"]
    assert client.delete(f"/api/v1/chat/{cid}").json()["deleted"] is True
    assert client.delete(f"/api/v1/chat/{cid}").json()["deleted"] is False
    print("test_conversation_delete OK")


class _FakeEmbed:
    """Hash-of-word bag vectorizer — semantic enough to test the plumbing,
    zero download, fully deterministic."""

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        import numpy as np
        out = []
        for t in texts:
            v = np.zeros(64, dtype=np.float32)
            for w in t.lower().split():
                v[hash(w) % 64] += 1
            n = np.linalg.norm(v)
            out.append(v / n if n else v)
        import numpy as np
        return np.array(out)


def test_rag_flow_and_isolation():
    from backend import rag
    real_model = rag._model
    real_gate = rag.GROUND_THRESHOLD
    rag._model = _FakeEmbed()  # skip the download; exercise the same code path
    rag.GROUND_THRESHOLD = 0.05  # fake vectors are hash-bags; gate tested via live runs
    _patch_llm("The refund window is 30 days [1].")
    try:
        cid = client.post("/api/v1/conversations").json()["conversation_id"]
        report = client.post(
            "/api/v1/documents",
            data={"conversation_id": cid},
            files={"file": ("policy.txt",
                            b"Our refund policy allows refunds within 30 days of purchase. "
                            b"Shipping is free over 50 euros. Contact support for questions.")},
        ).json()
        assert report["document"] == "policy.txt" and report["chunks"] >= 1
        assert rag.has_session(cid)

        ev = _post("What is the refund window?", cid)
        assert ev[0]["route"] == "document"
        done = ev[-1]
        assert done["type"] == "done" and done.get("sources")
        assert done["sources"][0]["document"] == "policy.txt"

        # cross-language retrieval path: German query, English doc, same plumbing
        de = _post("Wie lange ist die refund policy gültig?", cid)
        assert de[0]["route"] == "document"  # same session store

        # session isolation: a different conversation must not see the doc
        cid2 = client.post("/api/v1/conversations").json()["conversation_id"]
        assert not rag.has_session(cid2)
        ev2 = _post("What is the refund window?", cid2)
        assert ev2[0]["route"] == "general"

        # cleanup deletes the vectors with the chat
        assert client.delete(f"/api/v1/chat/{cid}").json()["documents_deleted"] is True
        assert not rag.has_session(cid)

        # document listing endpoint (UI document panel)
        cid3 = client.post("/api/v1/conversations").json()["conversation_id"]
        client.post("/api/v1/documents", data={"conversation_id": cid3},
                    files={"file": ("a.txt", b"alpha content for retrieval")})
        client.post("/api/v1/documents", data={"conversation_id": cid3},
                    files={"file": ("b.txt", b"beta content")})
        docs = client.get(f"/api/v1/documents/{cid3}").json()["documents"]
        assert {d["document"] for d in docs} == {"a.txt", "b.txt"}
        assert all(d["chunks"] >= 1 for d in docs)
        assert client.get(f"/api/v1/documents/{cid3}x").json()["documents"] == []
    finally:
        rag._read_index.cache_clear()
        rag._model = real_model
        rag.GROUND_THRESHOLD = real_gate
        _unpatch_all()
    print("test_rag_flow_and_isolation OK")


def test_upload_validation():
    cid = client.post("/api/v1/conversations").json()["conversation_id"]
    r = client.post("/api/v1/documents", data={"conversation_id": cid},
                    files={"file": ("evil.exe", b"MZ....")})
    assert r.status_code == 415
    print("test_upload_validation OK")


def test_web_route_mocked_and_fallback():
    from backend import web as webtool
    _patch_llm("According to [1], yes.")
    real = webtool.web_search
    webtool.web_search = lambda q, max_results=4: [
        {"title": "T", "url": "https://example.com", "snippet": "S"}]
    try:
        ev = _post("What is the latest news about AI chips?")
        assert ev[0]["route"] == "web"
        assert ev[-1].get("sources") and ev[-1]["sources"][0]["url"] == "https://example.com"
    finally:
        webtool.web_search = real

    # tool failure must degrade to general, never crash or fake sources
    webtool.web_search = lambda q, max_results=4: (_ for _ in ()).throw(RuntimeError("down"))
    try:
        ev = _post("What is the latest news about AI chips?")
        assert ev[0]["route"] == "web"               # router intent…
        assert ev[-1].get("sources") == []           # …gracefully degraded, no fake citations
        full = "".join(e.get("text", "") for e in ev if e["type"] == "delta")
        assert "According" in full                    # reassembled stream answered anyway
    finally:
        _unpatch_all()
        import importlib
        importlib.reload(webtool)
    print("test_web_route_mocked_and_fallback OK")


def main():
    test_health_and_catalog()
    test_general_route_stream_mocked()
    test_language_switch_per_message()
    test_translate_route_and_context()
    test_education_questions_use_general_model()
    test_memory_context_and_bounds()
    test_limits_validation_and_llm_missing()
    test_conversation_delete()
    test_rag_flow_and_isolation()
    test_upload_validation()
    test_web_route_mocked_and_fallback()
    print("\nALL V2 TESTS PASSED")


if __name__ == "__main__":
    main()
