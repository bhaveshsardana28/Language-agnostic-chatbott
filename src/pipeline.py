"""The pivot pipeline: detect -> translate to English -> classify ->
pick response -> translate back. All robustness lives here so app.py
stays a thin HTTP layer.

Robustness:
  - translation retry with exponential backoff (Google rate-limits; seen live)
  - disk cache for translations (cache/translations.json) — repeat and eval
    runs don't re-hit the network
  - low-confidence intents get a localized graceful fallback, not a wrong answer
  - every stage timed; timings returned for the Phase 5 latency analysis
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Optional

import config
from src import classifier
from src.detection import detect_meta
from src.translation import translate_text

logger = logging.getLogger(__name__)

CACHE_PATH = "cache/translations.json"
_model = None
_responses = None
_cache: dict = {}

# Hardcoded on purpose: the fallback must work even when translation is down.
FALLBACK_MSGS = {
    "en": "Sorry, I didn't quite understand. Could you rephrase? I can help with timetable, exams, fees, hostel, library, placements and more.",
    "hi": "माफ़ कीजिए, मैं समझ नहीं पाया। क्या आप दोबारा पूछ सकते हैं? मैं टाइमटेबल, परीक्षा, फीस, हॉस्टल, लाइब्रेरी जैसे विषयों में मदद कर सकता हूँ।",
    "pa": "ਮਾਫ਼ ਕਰਨਾ, ਮੈਂ ਸਮਝ ਨਹੀਂ ਸਕਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਪੁੱਛੋ। ਮੈਂ ਟਾਈਮਟੇਬਲ, ਪ੍ਰੀਖਿਆਵਾਂ, ਫੀਸ, ਹਾਸਟਲ, ਲਾਇਬ੍ਰੇਰੀ ਵਰਗੇ ਵਿਸ਼ਿਆਂ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ।",
    "es": "Lo siento, no te he entendido. ¿Puedes reformular? Puedo ayudarte con horarios, exámenes, tasas, residencia, biblioteca y más.",
    "fr": "Désolé, je n'ai pas bien compris. Pouvez-vous reformuler ? Je peux aider avec les emplois du temps, examens, frais, résidence, bibliothèque, etc.",
    "de": "Entschuldigung, das habe ich nicht verstanden. Können Sie es anders formulieren? Ich helfe bei Stundenplan, Prüfungen, Gebühren, Wohnheim, Bibliothek u.v.m.",
    "it": "Mi dispiace, non ho capito. Puoi riformulare? Posso aiutarti con orari, esami, tasse, residenza, biblioteca e altro.",
}
FALLBACK_GENERIC_FALLBACK = FALLBACK_MSGS["en"]  # for unsupported/undetected langs


def _load_model():
    global _model
    if _model is None:
        _model = classifier.load(config.MODEL_PATH)
    return _model


def _load_responses() -> dict:
    global _responses
    if _responses is None:
        data = json.load(open(config.INTENTS_PATH, encoding="utf-8"))
        _responses = {k: v["responses"] for k, v in data["intents"].items()}
    return _responses


def _load_cache() -> dict:
    global _cache
    if not _cache and os.path.exists(CACHE_PATH):
        try:
            _cache = json.load(open(CACHE_PATH, encoding="utf-8"))
        except Exception:
            _cache = {}
    return _cache


def translate_safe(text: str, target: str, source: str, retries: int = 3) -> Optional[str]:
    """Translate with cache + backoff. Returns None on persistent failure."""
    key = f"{source}|{target}|{text}"
    cache = _load_cache()
    if key in cache:
        return cache[key]
    for attempt in range(retries):
        try:
            out = translate_text(text, target_lang=target, source_lang=source)
            if out:
                cache[key] = out
                os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
                with open(CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=1)
                return out
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning("translate failed (attempt %d/%d), retry in %ds: %s",
                           attempt + 1, retries, wait, exc)
            time.sleep(wait)
    return None


def respond(text: str) -> dict:
    """Full pivot pipeline. Never raises; failures come back as degraded replies."""
    t0 = time.perf_counter()
    timings = {}

    meta = detect_meta(text)
    lang = meta["language"]
    timings["detect_ms"] = _ms(t0)
    if lang is None or lang not in config.SUPPORTED_LANGS:
        return _out(text, lang, None, 0.0, FALLBACK_GENERIC_FALLBACK, timings, meta, degraded=True)

    t = time.perf_counter()
    if lang == config.PIVOT_LANG:
        english = text
    else:
        english = translate_safe(text, config.PIVOT_LANG, lang)
        if english is None:
            logger.error("inbound translation failed for lang=%s", lang)
            return _out(text, lang, None, 0.0, FALLBACK_MSGS[lang], timings, meta, degraded=True)
    timings["translate_in_ms"] = _ms(t)

    t = time.perf_counter()
    intent, conf = classifier.predict(_load_model(), english)
    timings["classify_ms"] = _ms(t)

    t = time.perf_counter()
    if conf < config.INTENT_CONFIDENCE_THRESHOLD:
        reply_en = FALLBACK_MSGS["en"]
        intent_out = "fallback"
    else:
        reply_en = random.choice(_load_responses()[intent])
        intent_out = intent

    degraded = False
    if lang == config.PIVOT_LANG:
        reply = reply_en
    else:
        localized = translate_safe(reply_en, lang, config.PIVOT_LANG)
        # fallback message is already localized, no translation needed
        if intent_out == "fallback":
            localized = FALLBACK_MSGS[lang]
        if localized is None:  # outbound MT failed: serve English, say so
            logger.error("outbound translation failed for lang=%s", lang)
            reply, degraded = reply_en, True
        else:
            reply = localized
    timings["respond_ms"] = _ms(t)
    return _out(english, lang, intent_out, conf, reply, timings, meta, degraded=degraded)


def _out(english, lang, intent, conf, reply, timings, meta, degraded=False) -> dict:
    timings["total_ms"] = round(sum(timings.values()), 1)
    return {
        "lang": lang,
        "language_meta": meta,
        "english": english,
        "intent": intent,
        "confidence": round(conf, 4),
        "reply": reply,
        "degraded": degraded,
        "timings": timings,
    }


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)
