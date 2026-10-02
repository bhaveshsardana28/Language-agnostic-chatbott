"""Provider-agnostic LLM streaming. Raw HTTP (requests) — the SDK adds
nothing here. Two real implementations only:

  - ollama            : POST {base}/api/chat        (local, no key)
  - openai-compatible : POST {base}/chat/completions (groq / openrouter / openai)

Both stream; both raise RuntimeError on failure so the router can degrade.
Tests monkeypatch stream_chat()/chat() — no live calls in the suite.
"""

from __future__ import annotations

import json
from typing import Iterator, List, Dict

import requests

from backend import settings

_TIMEOUT = (10, 120)  # connect, read


def chat(messages: List[Dict[str, str]], model: str | None = None) -> str:
    return "".join(stream_chat(messages, model=model))


def stream_chat(messages: List[Dict[str, str]], model: str | None = None) -> Iterator[str]:
    provider = settings.LLM_PROVIDER
    model = model or settings.LLM_MODEL
    if provider == "ollama":
        yield from _stream_ollama(messages, model)
    else:
        yield from _stream_openai_compat(messages, model)


def _stream_ollama(messages, model) -> Iterator[str]:
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    with requests.post(url, json=payload, stream=True, timeout=_TIMEOUT) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("done"):
                break
            chunk = obj.get("message", {}).get("content", "")
            if chunk:
                yield chunk


def _stream_openai_compat(messages, model) -> Iterator[str]:
    if not settings.LLM_API_KEY:
        raise RuntimeError(f"LLM_API_KEY missing for provider {settings.LLM_PROVIDER}")
    url = f"{settings.OPENAI_COMPAT_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=_TIMEOUT) as r:
        if r.status_code >= 400:
            raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:200]}")
        for line in r.iter_lines():
            if not line or not line.startswith(b"data:"):
                continue
            data = line[5:].strip()
            if data == b"[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content")
            except (KeyError, IndexError, json.JSONDecodeError):
                continue  # malformed chunk: skip, never crash a stream
            if delta:
                yield delta
