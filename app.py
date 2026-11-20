"""Application entry point.

Running this file starts the new GAIA V2 FastAPI app. The original Flask
application remains importable for tests and is available explicitly with
``python app.py --legacy``.

Legacy Flask routes:
GET  /      -> old chat UI
POST /chat  -> {"message": str} -> {lang, intent, confidence, reply, degraded, timings}
"""

from __future__ import annotations

import logging
import os
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # importable from any cwd

import config
from src import pipeline
from backend import settings

os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(config.LOG_PATH), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pivot-chatbot")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.get("/")
def index():
    return render_template("index.html", langs=config.SUPPORTED_LANGS)


@app.get("/api/v1/health")
def health():
    return jsonify({"status": "ok", "model": settings.LLM_MODEL,
                    "languages": len(config.SUPPORTED_LANGS)})


@app.get("/api/v1/languages")
def languages():
    return jsonify(config.SUPPORTED_LANGS)


@app.get("/api/v1/intents")
def intents():
    return jsonify([])


@app.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    result, status = pipeline.legacy_reply(payload)
    if status != 200:
        return jsonify(result), status
    logger.info(
        "chat: lang=%s degraded=%s total=%sms",
        result["lang"], result["degraded"], result["timings"]["total_ms"],
    )
    return jsonify(result)


if __name__ == "__main__":
    if "--legacy" in sys.argv:
        app.run(host="127.0.0.1", port=5000)
    else:
        import uvicorn
        uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
