"""Deterministic request router. Language ≠ intent ≠ domain.

Order of decisions (each logged via `reason`):
  1. explicit TRANSLATION request     -> route "translate" (+target lang)
  2. choose reply language, then prefer explicit uploaded-document questions
  3. recency keywords -> web
  4. remaining questions with uploaded files -> document
  5. default -> general

Deterministic first, LLM never needed just to route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Display/native name -> ISO code, for language instructions & translation targets
LANG_NAME_TO_CODE = {
    "english": "en", "hindi": "hi", "हिंदी": "hi", "हिन्दी": "hi",
    "punjabi": "pa", "ਪੰਜਾਬੀ": "pa", "spanish": "es", "español": "es", "espanol": "es",
    "french": "fr", "français": "fr", "german": "de", "deutsch": "de",
    "italian": "it", "italiano": "it", "japanese": "ja", "日本語": "ja",
}

_LANG_ALT = "|".join(LANG_NAME_TO_CODE)
# "Translate <text> to/into <lang>" (indic order: "<text> <lang> में अनुवाद करो")
_TRANSLATE_RE = re.compile(
    rf"^(?:translate|traduc\w*|tradu\w*|übersetz\w*)\b\s*(?P<src>.*?)\s*"
    rf"\b(?:to|into|in|mein|को|al|en|zu)\s+(?P<tl>{_LANG_ALT})\b[.?!…\s]*$",
    re.IGNORECASE | re.DOTALL,
)
_TRANSLATE_INDIC_RE = re.compile(
    rf"^(?P<src>.*?)\s+(?P<tl>{_LANG_ALT})\s+में\s+अनुवाद\s+कर(?:ो|ें)\s*[.?!…]*$",
    re.IGNORECASE | re.DOTALL,
)
_LANG_INSTR_PATTERNS = [
    re.compile(rf"\b(?:in|auf|en)\s+({_LANG_ALT})\b", re.IGNORECASE),       # "answer in Hindi"
    re.compile(rf"\b({_LANG_ALT})\s+(?:mein|में|ਵਿੱਚ)\b", re.IGNORECASE),  # "hindi mein"
]
def _lang_instruction(text: str) -> Optional[str]:
    """Last explicit response-language instruction in the message, if any."""
    hits = [match for pattern in _LANG_INSTR_PATTERNS for match in pattern.finditer(text)]
    return LANG_NAME_TO_CODE[max(hits, key=lambda m: m.start()).group(1).lower()] if hits else None


_DEMONSTRATIVES = {"", "this", "it", "that", "इसे", "यह", "eso", "cela", "das", "lo"}


def _translation_parts(text: str) -> tuple[Optional[str], Optional[str]]:
    """(target_code, source_text) or (None, None). Empty/demonstrative source => None
    (caller substitutes the last assistant turn)."""
    for pat in (_TRANSLATE_RE, _TRANSLATE_INDIC_RE):
        m = pat.match(text.strip())
        if m:
            target = LANG_NAME_TO_CODE[m.group("tl").lower()]
            src = m.group("src").strip().strip("\"'“”‘’").strip()
            if src.lower() in _DEMONSTRATIVES:
                src = None
            return target, src
    return None, None
_RECENCY_RE = re.compile(
    r"\b(latest|today'?s?|current|news|price of|who won|right now|2026)\b", re.IGNORECASE
)
_DOCUMENT_RE = re.compile(
    r"\b(?:document|file|uploaded|upload|pdf|docx|markdown|attachment|"
    r"summari[sz]e|summary|main points|key points|what is in|what's in|"
    r"according to|from the|in the|page\s+\d+|"
    r"documento|archivo|resumen|página|document|fichier|résumé|page|"
    r"dokument|datei|zusammenfassung|seite|documento|file|riassunto|pagina|"
    r"दस्तावेज़|दस्तावेज|फ़ाइल|फाइल|अपलोड|सारांश|मुख्य\s+बिंदु|पृष्ठ|"
    r"ਦਸਤਾਵੇਜ਼|ਫਾਈਲ|ਸੰਖੇਪ|ਪੰਨਾ)\b",
    re.IGNORECASE,
)
_DOCUMENT_OVERVIEW_RE = re.compile(
    r"\b(?:what(?:'s| is) in|summari[sz]e|summary|main points|key points|"
    r"overview|give me the gist|tell me about (?:this|the) (?:document|file)|"
    r"tell me about (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"give me (?:some )?(?:information|info|details) about (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"explain (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"read (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"extract (?:all )?(?:the )?(?:text|content) (?:from|of) (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"what(?:'s| is) (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image) about|"
    r"what(?:'s| is) (?:the )?(?:content|text|information) (?:of|in|from) (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"what is written (?:in|on) (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"what(?:'s| is) (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image)|"
    r"what does (?:(?:this|the|that|my|your|an|a)\s+)?(?:uploaded|attached|scanned)?\s*(?:document|file|pdf|attachment|image) contain|"
    r"resumen|résumé|zusammenfassung|riassunto|सारांश|ਸੰਖੇਪ)\b",
    re.IGNORECASE,
)
_GENERIC_DOCUMENT_OVERVIEW_RE = re.compile(
    r"\b(?:important|key|main|essential|relevant)\s+(?:details|facts|points|information|info)|"
    r"\b(?:list|show|give|provide|share)\s+(?:me\s+)?(?:the\s+)?(?:facts|details|points|information|info|content)|"
    r"\bwhat\s+(?:information|info|content|details|facts|points)\b|"
    r"\b(?:tell|explain|describe)\s+me\s+(?:about|what)\b",
    re.IGNORECASE,
)


@dataclass
class Route:
    route: str                       # translate | web | document | general
    response_lang: str               # language the reply must be in
    reason: str = ""
    translate_target: Optional[str] = None
    translate_text: Optional[str] = None   # None => translate last assistant turn


def decide(text: str, lang_meta: dict, has_docs: bool = False) -> Route:
    user_lang = lang_meta.get("language") or "en"

    target, source = _translation_parts(text)
    if target:
        return Route("translate", target, "explicit translation request",
                     translate_target=target, translate_text=source)

    response_lang = _lang_instruction(text) or user_lang

    # Explicit document questions take precedence over incidental recency words.
    if has_docs and _DOCUMENT_RE.search(text):
        return Route("document", response_lang, "explicit uploaded-document request")

    if _RECENCY_RE.search(text):
        return Route("web", response_lang, "recency/freshness keywords")

    if has_docs:
        return Route("document", response_lang, "session has uploaded documents")

    return Route("general", response_lang, "no special trigger")


def is_document_overview(text: str) -> bool:
    """Whether retrieval should sample the document broadly, not gate one hit."""
    return bool(_DOCUMENT_OVERVIEW_RE.search(text) or _GENERIC_DOCUMENT_OVERVIEW_RE.search(text))


def is_document_followup(text: str) -> bool:
    """Whether a short, context-dependent question asks for a broad read."""
    return bool(re.search(
        r"^\s*(?:what does it say|what is it about|tell me more|read it|"
        r"summari[sz]e it|explain(?: it)?|what are the main points|give me the details)\s*[?.!]*\s*$",
        text or "", re.IGNORECASE,
    ))
