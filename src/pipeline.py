"""Cached machine translation and the stateless legacy chat adapter."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from typing import Optional

import config
from backend import llm, router, settings
from backend.assistant import safe_error, system_prompt
from src.detection import detect_meta
from src.translation import translate_text

logger = logging.getLogger(__name__)

CACHE_PATH = "cache/translations.json"
_cache: dict = {}
_cache_lock = threading.Lock()
_CACHE_LIMIT = 4096

def _load_cache() -> dict:
    global _cache
    if not _cache and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding="utf-8") as handle:
                saved = json.load(handle)
            _cache = {k: v for k, v in saved.items() if isinstance(v, str)}
        except Exception:
            _cache = {}
    return _cache


def translate_safe(text: str, target: str, source: str, retries: int = 3) -> Optional[str]:
    """Translate with cache + backoff. Returns None on persistent failure."""
    key = f"{source}|{target}|{text}"
    with _cache_lock:
        cache = _load_cache()
        if key in cache:
            return cache[key]
    for attempt in range(retries):
        try:
            out = translate_text(text, target_lang=target, source_lang=source)
            if out:
                with _cache_lock:
                    cache[key] = out
                    while len(cache) > _CACHE_LIMIT:
                        del cache[next(iter(cache))]
                    directory = os.path.dirname(CACHE_PATH) or "."
                    temporary = None
                    try:
                        os.makedirs(directory, mode=0o700, exist_ok=True)
                        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                                         delete=False) as stream:
                            temporary = stream.name
                            json.dump(cache, stream, ensure_ascii=False)
                        os.replace(temporary, CACHE_PATH)
                    except OSError:
                        logger.warning("translation cache write unavailable")
                    finally:
                        if temporary and os.path.exists(temporary):
                            os.unlink(temporary)
                return out
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning("translation attempt %d/%d failed: %s", attempt + 1, retries, type(exc).__name__)
            if attempt + 1 < retries:
                time.sleep(wait)
    return None


def legacy_reply(payload):
    """JSON chat contract shared by Flask and the FastAPI legacy page."""
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
        return {"error": "message must be a string"}, 400
    text = payload["message"].strip()
    if len(text) > 4000:
        return {"error": "message too long"}, 413
    if not text:
        return {"error": "empty message"}, 400

    target = payload.get("language")
    if target is not None and (not isinstance(target, str) or target not in config.SUPPORTED_LANGS):
        return {"error": "unsupported language"}, 400
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return {"error": "invalid Unicode"}, 400
    started = time.perf_counter()
    meta = detect_meta(text)
    detected = meta["language"]
    detected_at = time.perf_counter()
    route = router.decide(text, meta)
    language = target or route.response_lang
    degraded = False
    try:
        if route.route == "translate" and route.translate_text:
            language = target or route.translate_target
            source_lang = detect_meta(route.translate_text)["language"] or "auto"
            reply = translate_safe(route.translate_text, language, source_lang)
        else:
            ready, reason = settings.llm_ready()
            if not ready:
                raise RuntimeError(f"LLM unavailable: {reason}")
            reply = llm.chat([{"role": "system", "content": system_prompt(language)},
                              {"role": "user", "content": text}])
        if not reply or not reply.strip():
            raise RuntimeError("Empty reply")
    except Exception as exc:
        logger.warning("Compatibility chat unavailable: %s", type(exc).__name__)
        language = language if language in config.SUPPORTED_LANGS else "en"
        reply = safe_error(language, str(exc))
        degraded = True
    finished = time.perf_counter()
    return {"lang": detected, "language_meta": meta, "response_language": language,
            "english": text if detected == "en" else "", "intent": None, "confidence": 0.0,
            "reply": reply, "degraded": degraded,
            "timings": {"detect_ms": round((detected_at - started) * 1000, 1),
                        "translate_in_ms": 0.0, "classify_ms": 0.0,
                        "respond_ms": round((finished - detected_at) * 1000, 1),
                        "total_ms": round((finished - started) * 1000, 1)}}, 200
