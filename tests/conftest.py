"""Keep test collection and test requests away from the developer's runtime state."""
import os
from tempfile import TemporaryDirectory

import pytest


def pytest_configure(config):
    directory = TemporaryDirectory(prefix="gaia-tests-")
    config.add_cleanup(directory.cleanup)
    env = pytest.MonkeyPatch()
    config.add_cleanup(env.undo)
    env.setenv("GAIA_DB_PATH", os.path.join(directory.name, "gaia.db"))
    env.setenv("DOCUMENT_STORAGE_DIR", os.path.join(directory.name, "uploads"))
    env.setenv("LLM_API_KEY", "")
    env.setenv("HF_HUB_OFFLINE", "1")
    env.setenv("LLM_PROVIDER", "groq")


@pytest.fixture(autouse=True)
def isolated_translation(monkeypatch, tmp_path):
    from src import pipeline
    monkeypatch.setattr(pipeline, "CACHE_PATH", str(tmp_path / "translations.json"))
    monkeypatch.setattr(pipeline, "_cache", {})
    # Individual MT-specific tests supply their own translations.
    monkeypatch.setattr(pipeline, "translate_text", lambda *args, **kwargs: None)
