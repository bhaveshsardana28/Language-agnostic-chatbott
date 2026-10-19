"""Deterministic request router. Language ≠ intent ≠ domain.

Order of decisions (each logged via `reason`):
  1. explicit TRANSLATION request     -> route "translate" (+target lang)
  2. explicit language instruction    -> response_lang override ("answer in Hindi")
  3. campus domain                    -> route "campus_kb"  (FYP pivot pipeline;
     domain detection = campus keyword evidence + the trained classifier's
     confidence — non-campus goes to the general LLM, NOT to a hard refusal)
  4. recency / current-info keywords  -> route "web" (tool optional; degrades)
  5. session has uploaded documents   -> route "document" (when store is live)
  6. default                          -> route "general" (LLM)

Deterministic first, LLM never needed just to route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import config
from src import pipeline

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
# Campus evidence words, checked on the ENGLISH pivot form so one list
# covers every input language. The classifier ALONE over-claims on general
# text ("explain machine learning" scored 0.5+ on 'learning'), so the router
# demands BOTH a keyword hit AND classifier confidence >= gate.
_CAMPUS_KEYWORDS = (
    "exam", "exams", "midsem", "semester", "timetable", "class", "classes",
    "fee", "fees", "hostel", "library", "attendance", "placement",
    "canteen", "mess", "admission", "admissions", "erp", "club", "clubs",
    "campus", "scholarship", "result", "results", "cgpa", "sgpa",
    "professor", "lecture", "lectures", "tutorial", "college", "university",
    "registration", "transcript", "warden", "dean",
)


def _lang_instruction(text: str) -> Optional[str]:
    """Last explicit response-language instruction in the message, if any."""
    hit = None
    for pat in _LANG_INSTR_PATTERNS:
        for m in pat.finditer(text):
            hit = LANG_NAME_TO_CODE[m.group(1).lower()]
    return hit


def _campus_keyword_hit(english: str) -> bool:
    low = f" {english.lower()} "
    return any(f" {kw} " in low for kw in _CAMPUS_KEYWORDS)
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
    route: str                       # translate | campus_kb | web | document | general
    response_lang: str               # language the reply must be in
    reason: str = ""
    translate_target: Optional[str] = None
    translate_text: Optional[str] = None   # None => translate last assistant turn
    pivot: Optional[dict] = field(default=None)  # filled for campus_kb


def decide(text: str, lang_meta: dict, has_docs: bool = False) -> Route:
    user_lang = lang_meta.get("language") or "en"

    target, source = _translation_parts(text)
    if target:
        return Route("translate", user_lang, "explicit translation request",
                     translate_target=target, translate_text=source)

    response_lang = _lang_instruction(text) or user_lang

    # An explicit document request must win over incidental campus/recency words
    # (for example, "what does the uploaded document say about the 2026 exam?").
    # Otherwise a user can upload a document and have the same question routed to
    # the campus or web tool before retrieval gets a chance to run.
    if has_docs and _DOCUMENT_RE.search(text):
        return Route("document", response_lang, "explicit uploaded-document request")

    if _RECENCY_RE.search(text):
        return Route("web", response_lang, "recency/freshness keywords")

    english, conf = _campus_probe(text, user_lang)
    if english and _campus_keyword_hit(english) and conf >= config.INTENT_CONFIDENCE_THRESHOLD:
        return Route("campus_kb", response_lang,
                     f"campus domain (keyword + conf={conf:.3f} >= gate)")

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
        r"summari[sz]e it|explain it|what are the main points|give me the details)\s*[?.!]*\s*$",
        text or "", re.IGNORECASE,
    ))


def _campus_probe(text: str, user_lang: str) -> tuple[str, float]:
    """English pivot text (from cache/MT) + campus-model confidence.
    EN input costs nothing; non-EN costs one cached MT call."""
    english = text
    if user_lang != config.PIVOT_LANG:
        english = pipeline.translate_safe(text, config.PIVOT_LANG, user_lang, retries=2) or ""
    if not english:
        return "", 0.0
    _intent, conf = classifier_predict(english)
    return english, conf


def classifier_predict(english: str) -> tuple[str, float]:
    from src import classifier
    return classifier.predict(pipeline._load_model(), english)
