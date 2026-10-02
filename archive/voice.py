"""
Voice — Text-to-Speech via Google Translate TTS (gTTS).

ponytail: gTTS needs no API key and gets ~any language for free.
Upgrade path: Coqui/Piper for offline natural voices when quality matters.

Speech-to-text is handled in the browser via the Web Speech API (see app.py),
so this module only needs to provide TTS for now.
"""

from __future__ import annotations

import io
import os
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(
    os.path.expanduser("~"), ".language_agnostic_chatbot", "tts_cache"
)


def text_to_speech(text: str, lang: str = "en") -> Optional[str]:
    """Synthesize `text` to an MP3 file and return its path.

    Returns None on failure. `lang` is an ISO 639-1 code.
    """
    if not text or not text.strip():
        return None
    try:
        from gtts import gTTS
    except ImportError:
        logger.warning("gTTS not installed; TTS unavailable")
        return None

    os.makedirs(_CACHE_DIR, exist_ok=True)
    # ponytail: naive filename hashing. Replace with a hash of (lang,text) if collisions appear.
    safe = text[:40].replace("/", "_").replace(" ", "_")
    path = os.path.join(_CACHE_DIR, f"{lang}_{safe}.mp3")
    if not os.path.exists(path):
        try:
            gTTS(text=text, lang=lang).save(path)
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
            return None
    return path
