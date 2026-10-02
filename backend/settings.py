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


def llm_ready() -> tuple[bool, str]:
    """(can-we-call-an-llm, human-readable reason if not)."""
    if LLM_PROVIDER == "ollama":
        return True, ""
    if not LLM_API_KEY:
        return False, f"LLM_API_KEY not set for provider '{LLM_PROVIDER}'"
    return True, ""
