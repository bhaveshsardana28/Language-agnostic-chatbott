"""Pivot translation with a provider fallback chain.

Primary: deep-translator GoogleTranslator (free, no key, best quality).
Fallback: deep-translator MyMemoryTranslator (free, no key, separate quota)
          — kicks in when Google rate-limits (it does; seen live in Phase 5).
TranslateError propagates up only when ALL providers fail; the pipeline
turns that into a degraded-graceful reply.
"""

from typing import Optional

from deep_translator import GoogleTranslator, MyMemoryTranslator

# MyMemory wants locale codes, not bare ISO-639-1.
_MYMEMORY_CODES = {"en": "en-US", "hi": "hi-IN", "pa": "pa-IN", "es": "es-ES",
                   "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}


def translate_text(text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
    """Translate `text` to `target_lang`. Raises the last exception if all
    providers fail; pipeline.translate_safe handles that."""
    if not text:
        return ""
    errors = []
    # Google first (better for our language pairs)
    try:
        return GoogleTranslator(source=source_lang or "auto", target=target_lang).translate(text)
    except Exception as exc:
        errors.append(f"google: {exc}")
    # MyMemory fallback (`auto` not supported -> skip detect step, use source)
    if source_lang and source_lang != "auto":
        try:
            return MyMemoryTranslator(
                source=_MYMEMORY_CODES.get(source_lang, source_lang),
                target=_MYMEMORY_CODES.get(target_lang, target_lang),
            ).translate(text)
        except Exception as exc:
            errors.append(f"mymemory: {exc}")
    raise RuntimeError(" | ".join(errors) if errors else "no translation provider available")
