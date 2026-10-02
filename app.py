"""Flask entry point — pivot-translation multilingual chatbot.

GET  /      -> chat UI
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

os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(config.LOG_PATH), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pivot-chatbot")

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", langs=config.SUPPORTED_LANGS)


@app.get("/api/v1/health")
def health():
    return jsonify({"status": "ok", "model": config.MODEL_PATH,
                    "languages": len(config.SUPPORTED_LANGS)})


@app.get("/api/v1/languages")
def languages():
    return jsonify(config.SUPPORTED_LANGS)


@app.get("/api/v1/intents")
def intents():
    return jsonify(sorted(pipeline._load_responses().keys()))


@app.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("message", "")).strip()
    if not text:
        return jsonify({"error": "empty message"}), 400

    result = pipeline.respond(text)
    logger.info(
        "chat: lang=%s intent=%s conf=%.2f degraded=%s total=%sms",
        result["lang"], result["intent"], result["confidence"],
        result["degraded"], result["timings"]["total_ms"],
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
