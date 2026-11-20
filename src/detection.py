"""
Language detection v2 — script-aware, segment-level, code-switching capable.

Layers (in order):
  1. greeting maps (deterministic, unchanged from v1)
  2. script analysis + token segmentation  (script != language!)
  3. non-Latin-dominant messages: primary = langdetect on the dominant
     script's segments (reliable); Latin residue analyzed for secondary
     languages / romanized-Indic markers / tech terms (never for primary)
  4. Latin-only messages: langdetect on tech-stripped text first (one tech
     word must not flip a language); if that still says English, check
     romanized Hindi/Punjabi marker lexicons, then European function-word
     rescue ("Quiero mejorar my English" -> es)
  5. confidence: real computed values only — share(script) x langdetect
     probability for script-dominant cases, or a DOCUMENTED heuristic
     score for lexicon-based calls (never presented as a probability)

Legacy API preserved: detect_language() returns exactly what the FYP
pipeline and its tests expect for pure-language input.
"""

from typing import Optional
import unicodedata

from langdetect import DetectorFactory, detect_langs

import config

DetectorFactory.seed = 0

# --------------------------------------------------------------------------
# Lexicons (lowercase). Deliberately small; every entry must earn its place.
# --------------------------------------------------------------------------
_TECH_TERMS = {
    "python", "javascript", "java", "typescript", "react", "node", "django",
    "chatgpt", "gpt", "openai", "claude", "gemini", "ai", "agi", "llm",
    "api", "rest", "graphql", "sql", "html", "css", "docker", "kubernetes",
    "github", "git", "linux", "windows", "macos", "android", "ios",
    "gpu", "cpu", "ssd", "wifi", "http", "https", "json", "yaml",
}

# Romanized Hindi function/content words. STRONG = near-unambiguous.
_HI_STRONG = {
    "mujhe", "mujhko", "mujh", "chahiye", "nahin", "nahi", "kaise", "kitna",
    "kitne", "kitni", "kyun", "kyu", "kahan", "kaun", "hoon", "ho", "raha",
    "rahe", "rahi", "gaya", "gayi", "lagta", "matlab", "zaroor", "seekhna",
    "seekhni", "seekhne", "sikhna", "sikhni", "samajh", "samajhna", "yaar",
    "batao", "kaunsa", "kaunsi", "bhai", "accha", "thik", "theek", "banda", "dosti", "shukriya",
}
_HI_WEAK = {
    "hai", "hain", "mein", "main", "kya", "kar", "karna", "karne", "karo",
    "ko", "ke", "ki", "ka", "se", "par", "aur", "mera", "meri", "hum",
    "tum", "aap", "lena", "dena", "hona", "jaana", "ja",
}
# Punjabi-specific romanized markers (win over Hindi when present)
_PA_STRONG = {"mainu", "tainu", "kihda", "kitho", "kithon", "assi", "tussi",
              "haanji", "kiddan", "jatt"}

# English function/content words — used ONLY as code-switch evidence inside
# an already-primary-other-language message, never to claim English primary.
_EN_EVIDENCE = {
    "the", "is", "are", "am", "was", "what", "how", "when", "where", "which",
    "who", "this", "that", "these", "those", "my", "your", "you", "we",
    "they", "don", "t", "can", "will", "need", "want", "new", "time", "word",
    "language", "know", "start", "learn", "good", "bad", "please", "thanks",
    "but", "not", "just", "like", "get", "make", "help", "improve",
}
# European function words — rescue when langdetect wrongly says "en"
_ES_EVIDENCE = {"quiero", "puedo", "como", "donde", "cuando", "para", "por",
                "pero", "porque", "aprender", "hablar", "mejorar", "mucho",
                "gracias", "esta", "eso"}
_FR_EVIDENCE = {"je", "suis", "sont", "comment", "apprendre", "parler",
                "merci", "beaucoup", "peux", "veux", "c'est", "est"}
_DE_EVIDENCE = {"ich", "kann", "muss", "lernen", "sprechen", "nicht", "gut",
                "danke", "meine", "mein", "verbessern", "wissen"}
_IT_EVIDENCE = {"sono", "posso", "imparare", "parlare", "quando", "dove",
                "grazie", "molto", "come"}

_SCRIPT_HINTS = [
    ("DEVANAGARI", "Deva"), ("GURMUKHI", "Guru"), ("ARABIC", "Arab"),
    ("CYRILLIC", "Cyrl"), ("CJK", "Hani"), ("HIRAGANA", "Jpan"),
    ("KATAKANA", "Jpan"), ("HANGUL", "Kore"), ("THAI", "Thai"),
    ("BENGALI", "Beng"), ("TAMIL", "Taml"), ("TELUGU", "Telu"),
    ("GUJARATI", "Gujr"), ("GREEK", "Grek"),
]
_SCRIPT_FALLBACK_LANG = {"Deva": "hi", "Guru": "pa", "Arab": "ar",
                         "Cyrl": "ru", "Beng": "bn", "Taml": "ta",
                         "Telu": "te", "Gujr": "gu", "Thai": "th",
                         "Hani": "zh", "Jpan": "ja", "Kore": "ko"}


# --------------------------------------------------------------------------
# Script utilities
# --------------------------------------------------------------------------

def _char_script(ch: str) -> Optional[str]:
    # combining vowel signs (category Mn, e.g. Gurmukhi ੈ ੂ) are NOT
    # isalpha() but carry script identity — count them or Gurmukhi loses
    # its own script to a few Latin words (live-caught bug).
    if not (ch.isalpha() or unicodedata.category(ch).startswith("M")):
        return None
    name = unicodedata.name(ch, "")
    for hint, code in _SCRIPT_HINTS:
        if hint in name:
            return code
    return "Latn" if ch.isalpha() else None


def _tokenize(text: str) -> list[tuple[str, Optional[str]]]:
    """(token, dominant_script) — punctuation-only tokens carry None."""
    out = []
    for tok in text.split():
        scripts = [s for ch in tok if (s := _char_script(ch))]
        out.append((tok, max(set(scripts), key=scripts.count) if scripts else None))
    return out


def _scripts_of(text: str) -> dict[str, float]:
    """Share of alphabetic characters per script."""
    counts: dict[str, int] = {}
    for ch in text:
        s = _char_script(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    total = sum(counts.values())
    return {s: c / total for s, c in counts.items()} if total else {}


def _langdetect(text: str, fallback: Optional[str] = None) -> tuple[Optional[str], float]:
    try:
        langs = detect_langs(text)
        if langs:
            return langs[0].lang, float(langs[0].prob)
    except Exception:
        pass
    return fallback, 0.0


def _lower_tokens(tokens: list[tuple[str, Optional[str]]], script: str) -> list[str]:
    return [t.lower().strip(".,!?;:()'\"") for t, s in tokens if s == script]


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def detect_language(text: str) -> Optional[str]:
    return detect_meta(text)["language"]


def detect_meta(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        return _meta(None, 0.0, [], False, False, {}, "empty input")

    lang, conf, source = _greeting_map(stripped)
    if lang:
        m = _meta(lang, conf, [], False, False, _scripts_of(stripped), source)
        return m

    scripts = _scripts_of(stripped)
    if not scripts:
        return _meta(None, 0.0, [], False, False, {}, "no language-bearing characters")
    tokens = _tokenize(stripped)

    # Non-Latin scripts are decisive: people code-switch INTO Latin (tech
    # terms, English clauses), not accidentally INTO Devanagari. Char share
    # alone is wrong — an English clause can out-char a Hindi sentence
    # (live-caught: "मैं Python सीखना चाहता हूँ, but I don't know where to start.").
    for s, share in scripts.items():
        n_tokens = sum(1 for _, ts in tokens if ts == s)
        if s != "Latn" and (share >= 0.2 or n_tokens >= 2):
            return _meta_non_latin_dominant(tokens, scripts, s, stripped)

    return _meta_latin_only(tokens, scripts, stripped)


# --------------------------------------------------------------------------
# Branches
# --------------------------------------------------------------------------

def _meta_non_latin_dominant(tokens, scripts, dominant, text) -> dict:
    # Primary: langdetect over the dominant script's own tokens
    seg_tokens = [t for t, s in tokens if s == dominant]
    seg_text = " ".join(seg_tokens)
    lang, prob = _langdetect(seg_text, fallback=_SCRIPT_FALLBACK_LANG.get(dominant))
    primary = lang or _SCRIPT_FALLBACK_LANG.get(dominant)

    # Latin residue: markers / English evidence / secondary language
    lat = [t for t in _lower_tokens(tokens, "Latn")]
    residue = [t for t in lat if t and t not in _TECH_TERMS]
    hi_markers = {t for t in residue if t in _HI_STRONG or t in _HI_WEAK}
    pa_markers = {t for t in residue if t in _PA_STRONG}
    en_evidence = {t for t in residue if t in _EN_EVIDENCE}

    secondary: list[str] = []
    # a real second language needs >=3 non-tech Latin words with confident detection
    if len(residue) - len(hi_markers) >= 3:
        sec_lang, sec_prob = _langdetect(" ".join(t for t in residue if t not in hi_markers))
        if sec_lang and sec_lang != primary and sec_prob >= 0.8:
            secondary.append(sec_lang)

    code_switched = bool(hi_markers or pa_markers or en_evidence or secondary)
    mixed_script = sum(1 for s, f in scripts.items() if f >= 0.05) >= 2
    conf = round(scripts[dominant] * (prob if prob > 0 else 0.99), 4)
    reason = f"segment: {dominant} share={scripts[dominant]:.2f} prob={prob:.2f}"
    if hi_markers or pa_markers:
        reason += f" + romanized-indic markers {sorted(hi_markers | pa_markers)}"
    return _meta(primary, conf, secondary, code_switched, mixed_script, scripts, reason)


def _meta_latin_only(tokens, scripts, text) -> dict:
    lat = [t for t in _lower_tokens(tokens, "Latn") if t]

    # 1) langdetect on tech-stripped text — but ONLY trust it for known
    #    Latin-script languages. On Hinglish it happily returns Estonian/
    #    Swahili/etc. with high "confidence" (live-caught); garbage must
    #    fall through to the lexicons below, never be accepted.
    core = [t for t in lat if t not in _TECH_TERMS] or lat
    lang, prob = _langdetect(" ".join(core))
    if lang in ("es", "fr", "de", "it", "pt", "nl") and prob >= 0.5:
        return _meta(lang, round(prob, 4), [], False, False, scripts,
                     f"latin detect on tech-stripped text (prob={prob:.2f})")

    # 2) romanized-Indic lexicons ("Mujhe new language seekhne mein...")
    strong = {t for t in lat if t in _HI_STRONG or t in _PA_STRONG}
    weak = {t for t in lat if t in _HI_WEAK}
    if len(strong) >= 2 or (len(strong) >= 1 and len(weak) >= 2):
        primary = "pa" if strong & _PA_STRONG else "hi"
        residue = [t for t in lat
                   if t not in _HI_STRONG and t not in _PA_STRONG
                   and t not in _HI_WEAK and t not in _TECH_TERMS]
        en_evidence = [t for t in residue if t in _EN_EVIDENCE]
        code_switched = bool(en_evidence)
        secondary = ["en"] if code_switched else []
        # documented heuristic score (NOT a probability): evidence-count based
        conf = round(min(0.9, 0.5 + 0.1 * min(len(strong), 3) + 0.05 * min(len(weak), 2)), 4)
        reason = f"romanized-{'punjabi' if primary == 'pa' else 'hindi'} lexicon: strong={sorted(strong)} weak={sorted(weak)}"
        return _meta(primary, conf, secondary, code_switched, False, scripts, reason)

    # 3) European function-word rescue ("Quiero mejorar my English.")
    for code, lex in (("es", _ES_EVIDENCE), ("fr", _FR_EVIDENCE),
                      ("de", _DE_EVIDENCE), ("it", _IT_EVIDENCE)):
        hits = {t for t in lat if t in lex}
        if len(hits) >= 2:
            return _meta(code, 0.65, ["en"] if {t for t in lat if t in _EN_EVIDENCE} else [],
                         False, False, scripts,
                         f"euro function-word rescue: {sorted(hits)}")

    # 4) accept langdetect's answer (incl. en); legacy ASCII low-conf rule kept
    lang, prob = _langdetect(text)
    if lang is None or (prob < 0.8 and text.isascii()):
        lang, prob = "en", prob if prob > 0 else 0.5
    return _meta(lang, round(prob, 4), [], False, False, scripts, "latin whole-text detect")


def _greeting_map(text: str):
    low = text.lower()
    english_short = {"hello", "hi", "hey", "ok", "okay", "thanks", "thank",
                     "yes", "no", "bye", "good", "goodbye", "please"}
    if low in english_short:
        return "en", 0.99, "greeting map"
    gm = {"hola": "es", "bonjour": "fr", "hallo": "de", "ciao": "it",
          "namaste": "hi", "नमस्ते": "hi"}
    if low in gm:
        return gm[low], 0.99, "greeting map"
    return None, 0.0, None


def _meta(primary, conf, secondary, code_switched, mixed_script, scripts, reason) -> dict:
    return {
        "language": primary,                       # compat key = primary
        "primary_language": primary,
        "language_name": config.SUPPORTED_LANGS.get(primary, primary),
        "secondary_languages": secondary,
        "code_switched": code_switched,
        "mixed_script": mixed_script,
        "scripts": {k: round(v, 3) for k, v in scripts.items()},
        "script": max(scripts, key=scripts.get) if scripts else None,
        "confidence": round(conf, 4),
        "detection_reason": reason,
    }
