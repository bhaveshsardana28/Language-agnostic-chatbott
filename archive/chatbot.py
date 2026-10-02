"""
Chatbot engine — Multi-provider LLM support with streaming and routing.

Supported backends:
  • OpenAI (GPT-4o, GPT-3.5)
  • Google Gemini (1.5 Flash, 1.5 Pro)
  • Anthropic Claude (Sonnet, Haiku, Opus)
  • Codex (OpenAI Completion, legacy)
  • DeepSeek (Chat, OpenAI-compatible)
  • Groq (Llama, Mixtral, Gemma)
  • Perplexity (Sonar, OpenAI-compatible)
  • Ollama (local / remote)

Responses can be:
  • Single-shot via ``get_response``.
  • Token-streamed via ``stream_response`` when the provider supports it.
"""

from __future__ import annotations

import os
import re
import logging
from typing import List, Dict, Optional, Iterator, Any, Callable

import requests

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are Aikya, a helpful multilingual assistant. "
    "Respond in the same language as the user. Preserve idioms, tone and cultural nuance."
)

_LANG_NAMES = {
    "auto": "the user's language",
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "ja": "Japanese",
    "fr": "French",
    "de": "German",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ko": "Korean",
}


def lang_name(code: str) -> str:
    return _LANG_NAMES.get(code, "the user's language")


def _system_prompt(target_lang_name: str) -> str:
    if target_lang_name and target_lang_name != "the user's language":
        return f"You are Aikya, a helpful multilingual assistant. Respond in {target_lang_name}."
    return DEFAULT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def _history_to_openai_messages(
    history: List[Dict[str, str]], user_input: str, target_lang_name: str
) -> List[Dict[str, str]]:
    msgs = [{"role": "system", "content": _system_prompt(target_lang_name)}]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_input})
    return msgs


def _call_openai(prompt: str, model: str = "gpt-4o", *, target_lang_name: str = "English",
                 history: Optional[List[Dict[str, str]]] = None) -> str:
    import openai as oai
    client = oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    resp = client.chat.completions.create(
        model=model, messages=msgs, temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(prompt: str, model: str = "gemini-1.5-flash", *, target_lang_name: str = "English",
                 history: Optional[List[Dict[str, str]]] = None) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    contents: list = []
    for m in (history or []):
        if m.get("role") == "user":
            contents.append({"role": "user", "parts": [m["content"]]})
        elif m.get("role") == "assistant":
            contents.append({"role": "model", "parts": [m["content"]]})
    contents.append({"role": "user", "parts": [prompt]})
    gm = genai.GenerativeModel(
        model_name=model, system_instruction=_system_prompt(target_lang_name)
    )
    return gm.generate_content(contents).text.strip()


def _call_claude(prompt: str, model: str = "claude-3-5-sonnet-20241022", *,
                 target_lang_name: str = "English",
                 history: Optional[List[Dict[str, str]]] = None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msgs = []
    for m in (history or []):
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": prompt})
    resp = client.messages.create(
        model=model, max_tokens=4096,
        system=_system_prompt(target_lang_name), messages=msgs,
    )
    return resp.content[0].text.strip()


def _call_codex(prompt: str, model: str = "code-davinci-002", *, target_lang_name: str = "English",
                history: Optional[List[Dict[str, str]]] = None) -> str:
    import openai as oai
    client = oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    sys_prefix = _system_prompt(target_lang_name) + "\n\n"
    resp = client.completions.create(
        model=model, prompt=sys_prefix + prompt, max_tokens=1024, temperature=0.7,
    )
    return resp.choices[0].text.strip()


def _call_deepseek(prompt: str, model: str = "deepseek-chat", *, target_lang_name: str = "English",
                   history: Optional[List[Dict[str, str]]] = None) -> str:
    import openai as oai
    client = oai.OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    resp = client.chat.completions.create(model=model, messages=msgs, temperature=0.7)
    return resp.choices[0].message.content.strip()


def _call_groq(prompt: str, model: str = "llama-3.1-70b-versatile", *, target_lang_name: str = "English",
               history: Optional[List[Dict[str, str]]] = None) -> str:
    import openai as oai
    client = oai.OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    resp = client.chat.completions.create(model=model, messages=msgs, temperature=0.7)
    return resp.choices[0].message.content.strip()


def _call_perplexity(prompt: str, model: str = "llama-3.1-sonar-large-128k-online", *,
                     target_lang_name: str = "English",
                     history: Optional[List[Dict[str, str]]] = None) -> str:
    import openai as oai
    client = oai.OpenAI(
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        base_url="https://api.perplexity.ai",
    )
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    resp = client.chat.completions.create(model=model, messages=msgs, temperature=0.7)
    return resp.choices[0].message.content.strip()


OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _call_ollama(prompt: str, model: str = "llama3.1", *, target_lang_name: str = "English",
                 history: Optional[List[Dict[str, str]]] = None) -> str:
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": _history_to_openai_messages(history or [], prompt, target_lang_name),
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    if "message" in data:
        return str(data["message"].get("content", "")).strip()
    if "response" in data:
        return str(data["response"]).strip()
    return ""


# ---------------------------------------------------------------------------
# Streaming variants (token-by-token) — yield chunks.
# Providers that don't support streaming fall back to single-shot wrapped.
# ---------------------------------------------------------------------------

def _stream_openai(prompt: str, history, model, target_lang_name) -> Iterator[str]:
    import openai as oai
    client = oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    stream = client.chat.completions.create(
        model=model, messages=msgs, temperature=0.7, stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _stream_ollama(prompt: str, history, model, target_lang_name) -> Iterator[str]:
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": _history_to_openai_messages(history or [], prompt, target_lang_name),
        "stream": True,
    }
    resp = requests.post(url, json=payload, stream=True, timeout=180)
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            import json as _json
            obj = _json.loads(line)
        except Exception:
            continue
        if obj.get("done"):
            break
        msg = obj.get("message", {})
        chunk = msg.get("content", "")
        if chunk:
            yield chunk


def _stream_groq(prompt: str, history, model, target_lang_name) -> Iterator[str]:
    import openai as oai
    client = oai.OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    msgs = _history_to_openai_messages(history or [], prompt, target_lang_name)
    stream = client.chat.completions.create(model=model, messages=msgs, temperature=0.7, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _stream_claude(prompt: str, history, model, target_lang_name) -> Iterator[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msgs = []
    for m in (history or []):
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": prompt})
    with client.messages.stream(
        model=model, max_tokens=4096,
        system=_system_prompt(target_lang_name), messages=msgs,
    ) as stream:
        for text in stream.text_stream:
            yield text


_STREAMERS = {
    "openai": _stream_openai,
    "ollama": _stream_ollama,
    "groq": _stream_groq,
    "claude": _stream_claude,
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_CALLERS = {
    "openai": _call_openai,
    "gemini": _call_gemini,
    "claude": _call_claude,
    "codex": _call_codex,
    "deepseek": _call_deepseek,
    "groq": _call_groq,
    "perplexity": _call_perplexity,
    "ollama": _call_ollama,
}

_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "codex": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}


def get_response(
    user_input: str,
    user_lang: str = "en",
    *,
    backend: str = "ollama",
    model: str = "llama3.1",
    target_lang: str = "auto",
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate a response using the selected provider.

    Raises RuntimeError on failure so the caller can show the error in the UI.
    """
    backend = backend.lower()
    logger.info("get_response: backend=%s model=%s target_lang=%s", backend, model, target_lang)

    if backend not in _CALLERS:
        raise ValueError(f"Unsupported backend: {backend}")

    caller = _CALLERS[backend]
    env_var = _KEY_ENV.get(backend)
    tln = lang_name(target_lang) if target_lang else "the user's language"

    # Check API key; Ollama needs none
    if env_var and not os.getenv(env_var):
        logger.warning("%s key (%s) not set – falling back to Ollama", backend, env_var)
        try:
            return _call_ollama(user_input, model="llama3.1", target_lang_name=tln, history=history)
        except Exception as exc:
            raise RuntimeError(f"{backend} key not set and Ollama fallback failed: {exc}")

    try:
        return caller(user_input, model=model, target_lang_name=tln, history=history)
    except Exception as exc:
        logger.error("%s call failed: %s", backend, exc)
        raise RuntimeError(f"{backend} backend failed: {exc}")


def stream_response(
    user_input: str,
    user_lang: str = "en",
    *,
    backend: str = "ollama",
    model: str = "llama3.1",
    target_lang: str = "auto",
    history: Optional[List[Dict[str, str]]] = None,
) -> Iterator[str]:
    """Yield response tokens for streaming UIs.

    If the backend has no native streamer, fall back to single-shot chunked.
    """
    backend = backend.lower()
    tln = lang_name(target_lang) if target_lang else "the user's language"
    env_var = _KEY_ENV.get(backend)
    if env_var and not os.getenv(env_var):
        backend = "ollama"

    streamer = _STREAMERS.get(backend)
    if streamer is None:
        # Provider has no streamer; do single-shot and yield once
        yield get_response(
            user_input, user_lang, backend=backend, model=model, target_lang=target_lang, history=history
        )
        return

    try:
        for chunk in streamer(user_input, history or [], model, tln):
            yield chunk
    except Exception as exc:
        logger.error("%s stream failed: %s", backend, exc)
        raise RuntimeError(f"{backend} stream failed: {exc}")


# ---------------------------------------------------------------------------
# Adaptive model router — picks the best backend/model by query complexity.
# ponytail: rule-based heuristic, no ML. Upgrade path: learned router table.
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r"```|\bdef\b|\bfunction\b|\bclass\b|\bimport\b|\bprint\(|\bconsole\.log|=\s*=>")
_LONG_RE = re.compile(r"\b(\w+)\b")


def score_complexity(text: str) -> int:
    """Return 0-100 score: higher = harder query."""
    s = text.strip()
    if not s:
        return 0
    score = 0
    words = _LONG_RE.findall(s)
    n = len(words)
    if n >= 40:
        score += 35
    elif n >= 15:
        score += 20
    elif n >= 6:
        score += 10
    if _CODE_RE.search(s):
        score += 30
    if any(k in s.lower() for k in ("explain", "analyze", "compare", "summarize", "why", "how come")):
        score += 15
    if any(k in s.lower() for k in ("translate", "what is", "define")):
        score += 5
    return min(score, 100)


def route_model(
    text: str, available: Dict[str, Optional[str]]
) -> tuple:
    """Pick (backend, model) by complexity.

    available maps backend -> configured model name (or None if not available).
    """
    score = score_complexity(text)

    # ponytail: prefer strongest model for hard queries, cheapest for easy
    def has(b):
        return b in available and available[b] is not None

    if score >= 50:
        for pref in ("claude", "openai", "gemini", "groq", "deepseek", "perplexity", "ollama"):
            if has(pref):
                return pref, available[pref]
    if score >= 20:
        for pref in ("groq", "openai", "gemini", "claude", "deepseek", "perplexity", "ollama"):
            if has(pref):
                return pref, available[pref]
    # easy / fallback
    for pref in ("ollama", "groq", "gemini", "deepseek", "openai", "claude", "perplexity"):
        if has(pref):
            return pref, available[pref]
    return "ollama", "llama3.1"


def generate_title(first_user_message: str, *, backend: str = "ollama", model: str = "llama3.1") -> str:
    """Ask the LLM for a short conversation title. Falls back to a heuristics slice."""
    prompt = (
        "Give this conversation a short title (max 5 words, no quotes, no punctuation at end). "
        "Remember, just a plain title string:\n\n" + first_user_message
    )
    try:
        title = get_response(prompt, backend=backend, model=model, target_lang="en")
        title = title.strip().strip('"').strip()
        if len(title) > 60:
            title = title[:60]
        if not title:
            return first_user_message.strip().replace("\n", " ")[:50] or "New Chat"
        return title
    except Exception:
        return first_user_message.strip().replace("\n", " ")[:50] or "New Chat"
