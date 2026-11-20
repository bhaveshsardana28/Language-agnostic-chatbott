"""Regressions for public request, provider transport and persistence contracts."""
from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from backend import llm, memory, router, settings, storage
from backend.main import app
from src import pipeline, translation
from src.detection import detect_meta


@pytest.mark.parametrize("body", [b"invalid", b"[]", b"null", b'{"message": null}',
                                  b'{"message": 3}', b'{"message":"x","conversation_id":[]}',
                                  b'{"message":"\\ud800"}'])
def test_invalid_body_has_no_side_effect(body):
    client = TestClient(app)
    with storage.connect() as db:
        before = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    assert client.post("/api/v1/chat", content=body).status_code == 400
    with storage.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == before


def test_concurrent_claim_and_atomic_turns():
    import uuid
    cid = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:
        owners = ["one", "two", "three", "four"]
        won = list(pool.map(lambda owner: memory.claim(cid, owner), owners))
        assert sum(won) == 1
        winner = owners[won.index(True)]
        list(pool.map(lambda i: memory.append_turn(cid, winner, str(i), str(i)), range(8)))
    history = memory.history(cid, winner)
    assert len(history) == 16
    assert all(x["content"] == y["content"] for x, y in zip(history[::2], history[1::2]))
    assert memory.history(cid, "different") == []
    storage.delete_conversation(cid, winner)
    memory.append_turn(cid, winner, "late", "answer")
    assert not memory.exists(cid)


def test_education_answer_language(monkeypatch):
    prompts = []
    def stream(messages):
        prompts.extend(messages)
        yield "अपनी परीक्षा की तारीख आयोजक से पूछें।"
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "stream_chat", stream)
    frames = TestClient(app).post("/api/v1/chat", json={"message": "When are my exams? Answer in Hindi."}).text
    events = [json.loads(line[6:]) for line in frames.splitlines() if line.startswith("data: ")]
    assert events[0]["route"] == "general" and events[0]["response_lang"] == "hi"
    assert "Hindi" in prompts[0]["content"] and events[1]["text"].startswith("अपनी")


def test_unavailable_explicit_translation(monkeypatch):
    monkeypatch.setattr(pipeline, "translate_safe", lambda *args: None)
    frames = TestClient(app).post("/api/v1/chat", json={"message":"Translate hello into French"}).text
    events = [json.loads(line[6:]) for line in frames.splitlines() if line.startswith("data: ")]
    assert events[0]["route"] == "translate"
    assert [e["type"] for e in events] == ["meta", "error", "done"]


def test_literal_preservation_and_hinglish(monkeypatch):
    monkeypatch.setattr(translation, "_google", lambda text, source, target: text.upper())
    assert translation.translate_text("use `git status` at https://example.org/X", "fr", "en") == (
        "USE `git status` AT https://example.org/X")
    meta = detect_meta("Mujhe batao maine kaunsa test word diya tha?")
    assert meta["language"] == "hi" and meta["code_switched"]
    assert router.decide("Translate hello into French", {"language": "en"}).response_lang == "fr"


@pytest.mark.parametrize("provider,frames,ok", [
    ("ollama", [b'{"message":{"content":"text"},"done":true}'], True),
    ("ollama", [b'{"message":{"content":"text"}}'], False),
    ("openai", [b'data: {"choices":[{"delta":{"content":"text"}}]}', b'data: [DONE]'], True),
    ("groq", [b'data: {"choices":[{"delta":{"content":"text"}}]}'], False),
    ("openrouter", [b'data: {"error":{"message":"example"}}'], False),
])
def test_provider_completion(monkeypatch, provider, frames, ok):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status_code = 200
    response.iter_lines.return_value = frames
    monkeypatch.setattr(llm.requests, "post", lambda *a, **kw: response)
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(settings, "LLM_PROVIDER", provider)
    if ok:
        assert llm.chat([{"role":"user","content":"question"}]) == "text"
    else:
        with pytest.raises(RuntimeError):
            llm.chat([{"role":"user","content":"question"}])


def test_interrupted_generation_does_not_pollute_context(monkeypatch):
    def interrupted(messages):
        yield "partial"
        raise TimeoutError()
    monkeypatch.setattr(llm, "stream_chat", interrupted)
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    response = TestClient(app).post("/api/v1/chat", json={"message":"Explain recursion"})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["meta", "delta", "error", "done"]
    assert memory.history(events[0]["conversation_id"]) == []


def test_concurrent_http_chats_keep_own_context(monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "stream_chat", lambda messages: iter([messages[-1]["content"]]))
    def chat(index):
        with TestClient(app) as client:
            text = f"Explain recursion in example {index}."
            res = client.post("/api/v1/chat", json={"message": text})
            frames = [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]
            cid = frames[0]["conversation_id"]
            assert memory.history(cid) == [{"role": "user", "content": text}, {"role": "assistant", "content": text}]
            return cid
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert len(set(pool.map(chat, range(4)))) == 4


def test_upload_limit_releases_capacity(monkeypatch):
    from backend import limits
    from fastapi import FastAPI, File, UploadFile
    small = FastAPI()
    small.add_middleware(limits.RequestLimits, upload_bytes=64)
    @small.post("/api/v1/documents")
    def upload(file: UploadFile = File(...)):
        return {"ok": True}
    client = TestClient(small)
    assert client.post("/api/v1/documents", files={"file": ("large.txt", b"A" * 70000)}).status_code == 413
    assert client.post("/api/v1/documents", files={"file": ("ok.txt", b"text")}).json() == {"ok": True}


def test_concurrent_documents_are_retrievable_after_deletion(monkeypatch):
    from backend import rag
    monkeypatch.setattr(rag, "embeddings_available", lambda: False)
    cid = memory.create("test-owner")
    def upload(name):
        return rag.add_document(cid, f"Contents of {name}".encode(), name, "test-owner", True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(upload, ["same.txt", "same.txt", "other.txt", "third.txt"]))
    assert results[0]["document_id"] == results[1]["document_id"]
    hits = rag.query(cid, "overview", overview=True, owner_id="test-owner")["hits"]
    assert {h["document"] for h in hits} == {"same.txt", "third.txt", "other.txt"}
    assert rag.delete_document(cid, results[0]["document_id"], "test-owner")
    assert {h["document"] for h in rag.query(cid, "", overview=True)["hits"]} == {"third.txt", "other.txt"}


def test_separate_process_recovers_state():
    import subprocess
    import sys
    cid = memory.create("restart-check")
    memory.append_turn(cid, "restart-check", "hello", "bonjour")
    out = subprocess.check_output([sys.executable, "-c",
        "import json,sys; from backend import memory; print(json.dumps(memory.history(sys.argv[1])))", cid],
        text=True)
    assert json.loads(out) == memory.history(cid)



def test_legacy_form_on_fastapi(monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "chat", lambda messages: "Check with your exam organizer.")
    client = TestClient(app)
    assert client.get("/legacy").is_success
    reply = client.post("/chat", json={"message":"When are my exams?", "language":"en"})
    assert reply.is_success and reply.json()["intent"] is None and "organizer" in reply.json()["reply"]



def test_ambiguous_and_unsupported_inputs(monkeypatch):
    assert detect_meta("🙂!?")["language"] is None
    assert router.decide("🙂!?", detect_meta("🙂!?")).route == "general"
    meta = detect_meta("Как мне выучить новый язык?")
    assert meta["language"] == "ru"
    assert router.decide("Как мне выучить новый язык?", meta).route == "general"
    reply, status = pipeline.legacy_reply({"message": "when are my exams", "language": "hi"})
    assert status == 200 and reply["response_language"] == "hi" and reply["degraded"]


def test_regeneration_replaces_only_latest_reply(monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    calls = []
    def stream(messages):
        calls.append(messages)
        yield f"Answer {len(calls)}"
    monkeypatch.setattr(llm, "stream_chat", stream)
    client = TestClient(app)
    payload = {"message":"Explain recursion"}
    def events():
        result = client.post("/api/v1/chat", json=payload)
        return [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")]
    first = events()
    cid = first[0]["conversation_id"]
    payload.update(conversation_id=cid, replace_reply=first[-1]["reply_id"])
    second = events()
    assert second[-1]["reply_id"] != first[-1]["reply_id"]
    assert calls[0] == calls[1]
    assert [m["content"] for m in memory.history(cid)] == ["Explain recursion", "Answer 2"]
    assert client.post("/api/v1/chat", json=payload).status_code == 409


def test_inflight_chat_budget_returns_retry_after():
    from threading import Event
    from fastapi import FastAPI
    from backend.limits import RequestLimits
    entered, release = Event(), Event()
    service = FastAPI()
    service.add_middleware(RequestLimits, upload_bytes=64, max_chats=1)

    @service.post("/api/v1/chat")
    def hold():
        entered.set()
        assert release.wait(3)
        return {"ok": True}

    with TestClient(service) as client, ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, "/api/v1/chat")
        try:
            assert entered.wait(3)
            busy = client.post("/api/v1/chat")
            assert busy.status_code == 429 and busy.headers["Retry-After"] == "2"
        finally:
            release.set()
        assert first.result().is_success
        assert client.post("/api/v1/chat").is_success

@pytest.mark.parametrize("message", [
    "¿Cómo organizo mi semana?",
    "मैं अपनी पढ़ाई की योजना कैसे बनाऊँ?",
    "How do I use a Python library?",
    "What is the NorthCap University admissions process?",
])
def test_general_routing_preserves_original_message(monkeypatch, message):
    def unexpected_translation(*args, **kwargs):
        pytest.fail("A general question triggered a translation preflight")

    calls = []
    def stream(messages):
        calls.extend(messages)
        yield "Model answer"

    monkeypatch.setattr(pipeline, "translate_safe", unexpected_translation)
    monkeypatch.setattr(settings, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "stream_chat", stream)
    response = TestClient(app).post("/api/v1/chat", json={"message": message})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["meta", "delta", "done"]
    assert events[0]["route"] == "general" and events[1]["text"] == "Model answer"
    assert calls[-1] == {"role": "user", "content": message}
    assert "LANGUAGE AGNOSTIC CHATBOT" in calls[0]["content"]


def test_legacy_translation_respects_requested_language(monkeypatch):
    seen = []
    def translate(text, target, source):
        seen.append((text, target))
        return "Guten Morgen"
    monkeypatch.setattr(pipeline, "translate_safe", translate)
    result, status = pipeline.legacy_reply({"message": "Translate good morning into French", "language": "de"})
    assert status == 200 and seen == [("good morning", "de")]
    assert result["reply"] == "Guten Morgen" and result["response_language"] == "de"
