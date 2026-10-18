"""v2 settings: env-driven, no secrets in code. .env is loaded by hand
(five lines, no python-dotenv dependency). FYP config.py is untouched."""

from __future__ import annotations

import os


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_COMPAT_BASE_URL = os.getenv(
    "OPENAI_COMPAT_BASE_URL",
    {
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "openai": "https://api.openai.com/v1",
    }.get(LLM_PROVIDER, "https://api.groq.com/openai/v1"),
)

MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "4000"))
MEMORY_TURNS = int(os.getenv("MEMORY_TURNS", "10"))
GAIA_DB_PATH = os.getenv("GAIA_DB_PATH", os.path.join("data", "gaia.db"))
SQLITE_TIMEOUT = float(os.getenv("SQLITE_TIMEOUT", "5"))
OCR_ENABLED = os.getenv("OCR_ENABLED", "1").lower() not in {"0", "false", "no", "off"}
OCR_LANG = os.getenv("OCR_LANG", "eng")
OCR_MIN_TEXT_CHARS = int(os.getenv("OCR_MIN_TEXT_CHARS", "24"))
MAX_DOCUMENT_PAGES = int(os.getenv("MAX_DOCUMENT_PAGES", "100"))
DOCUMENT_STORAGE_DIR = os.getenv("DOCUMENT_STORAGE_DIR", os.path.join("data", "uploads"))
OCR_DPI = int(os.getenv("OCR_DPI", "200"))
OCR_TIMEOUT_SECONDS = float(os.getenv("OCR_TIMEOUT_SECONDS", "30"))
OCR_TARGET_WIDTH = int(os.getenv("OCR_TARGET_WIDTH", "1600"))
OCR_MAX_SCALE = float(os.getenv("OCR_MAX_SCALE", "3"))
OCR_CONTRAST = float(os.getenv("OCR_CONTRAST", "1.35"))
OCR_CONFIG = os.getenv("OCR_CONFIG", "--psm 6")
OCR_REVIEW_CONFIDENCE = float(os.getenv("OCR_REVIEW_CONFIDENCE", "60"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "40000000"))
MAX_ARCHIVE_ENTRIES = int(os.getenv("MAX_ARCHIVE_ENTRIES", "100"))
MAX_ARCHIVE_UNCOMPRESSED_BYTES = int(os.getenv("MAX_ARCHIVE_UNCOMPRESSED_BYTES", str(100 * 1024 * 1024)))
MAX_RENDER_PIXELS = int(os.getenv("MAX_RENDER_PIXELS", str(20 * 1000 * 1000)))
WORKSPACE_COOKIE_SECURE = os.getenv("WORKSPACE_COOKIE_SECURE", "0").lower() in {"1", "true", "yes", "on"}


def llm_ready() -> tuple[bool, str]:
    """(can-we-call-an-llm, human-readable reason if not)."""
    if LLM_PROVIDER == "ollama":
        return True, ""
    if not LLM_API_KEY:
        return False, f"LLM_API_KEY not set for provider '{LLM_PROVIDER}'"
    return True, ""
