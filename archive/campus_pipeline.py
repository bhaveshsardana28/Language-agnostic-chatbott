"""Retired campus classifier for reproducing historical evaluations only."""
import json
import logging
import random
import time

import config
from src import classifier
from src.detection import detect_meta
from src.pipeline import translate_safe

logger = logging.getLogger(__name__)
_model = None
_responses = None

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


def respond(text: str, *, response_lang=None, meta=None, pivot=None) -> dict:
    """Full pivot pipeline. Never raises; failures come back as degraded replies."""
    t0 = time.perf_counter()
    timings = {}

    meta = meta or detect_meta(text)
    lang = meta["language"]
    timings["detect_ms"] = _ms(t0)
    if lang is None or lang not in config.SUPPORTED_LANGS:
        return _out(text, lang, None, 0.0, FALLBACK_GENERIC_FALLBACK, timings, meta, degraded=True)

    t = time.perf_counter()
    if pivot:
        english = pivot["english"]
    elif lang == config.PIVOT_LANG:
        english = text
    else:
        english = translate_safe(text, config.PIVOT_LANG, lang)
        if english is None:
            timings["translate_in_ms"] = _ms(t)
            logger.error("inbound translation failed for lang=%s", lang)
            return _out(text, lang, None, 0.0, FALLBACK_MSGS[lang], timings, meta, degraded=True)
    timings["translate_in_ms"] = _ms(t)

    t = time.perf_counter()
    if pivot:
        intent, conf = pivot["intent"], pivot["confidence"]
    else:
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
    target = response_lang or lang
    if target == config.PIVOT_LANG:
        reply = reply_en
    else:
        localized = FALLBACK_MSGS.get(target) if intent_out == "fallback" else None
        if localized is None:
            localized = translate_safe(reply_en, target, config.PIVOT_LANG)
        if localized is None:  # outbound MT failed: serve English, say so
            logger.error("outbound translation failed for lang=%s", lang)
            reply, degraded = reply_en, True
        else:
            reply = localized
    timings["respond_ms"] = _ms(t)
    return _out(english, lang, intent_out, conf, reply, timings, meta, degraded=degraded,
                response_language="en" if degraded else target)


def _out(english, lang, intent, conf, reply, timings, meta, degraded=False, response_language=None) -> dict:
    timings["total_ms"] = round(sum(timings.values()), 1)
    return {
        "lang": lang,
        "response_language": response_language or (lang if lang in FALLBACK_MSGS else "en"),
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
