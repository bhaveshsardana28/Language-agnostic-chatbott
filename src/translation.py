"""Bounded HTTPS requests to the Google Translate mobile page and MyMemory."""
import html
import re

import requests
from bs4 import BeautifulSoup

_TIMEOUT = (3, 8)
_LOCALES = {"en": "en-US", "hi": "hi-IN", "pa": "pa-IN", "es": "es-ES",
            "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
_LITERAL = re.compile(r"```[\s\S]*?```|`[^`\n]+`|https?://[^\s<>]+")


def _google(text, source, target):
    response = requests.get("https://translate.google.com/m",
                            params={"sl": source, "tl": target, "q": text}, timeout=_TIMEOUT)
    response.raise_for_status()
    element = BeautifulSoup(response.text, "html.parser").select_one("div.result-container, div.t0")
    return element.get_text(strip=True) if element else ""


def _mymemory(text, source, target):
    if source == "auto" or len(text.encode("utf-8")) > 500:
        return ""
    pair = f"{_LOCALES.get(source, source)}|{_LOCALES.get(target, target)}"
    response = requests.get("https://api.mymemory.translated.net/get",
                            params={"q": text, "langpair": pair}, timeout=_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if str(data.get("responseStatus")) != "200" or data.get("quotaFinished"):
        return ""
    return html.unescape(data["responseData"]["translatedText"])


def translate_text(text: str, target_lang: str, source_lang: str | None = None) -> str:
    if not text or source_lang == target_lang or _LITERAL.fullmatch(text):
        return text
    # Keep literals outside machine translation. A provider can transliterate
    # placeholder tokens and silently corrupt otherwise valid code.
    parts = _LITERAL.split(text)
    literals = _LITERAL.findall(text)
    if len(parts) > 16:
        raise ValueError("too many separate translation segments")
    result = []
    for index, part in enumerate(parts):
        if part.strip():
            for provider in (_google, _mymemory):
                try:
                    translated = provider(part.strip(), source_lang or "auto", target_lang)
                    if translated:
                        result.append(part[:len(part)-len(part.lstrip())] + translated.strip()
                                      + part[len(part.rstrip()):])
                        break
                except (requests.RequestException, ValueError, TypeError, KeyError):
                    continue
            else:
                raise RuntimeError("translation services unavailable")
        else:
            result.append(part)
        if index < len(literals):
            result.append(literals[index])
    return "".join(result)
