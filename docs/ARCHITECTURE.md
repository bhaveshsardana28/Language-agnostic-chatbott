# GAIA V2 architecture

The main entry point serves static HTML, CSS and native JavaScript modules from FastAPI. The browser sends a message and optional conversation ID to `POST /api/v1/chat`. Workspace-cookie checks scope stored messages and documents to the conversation owner.

1. `src/detection.py` identifies the language of each message, including mixed-script signals.
2. `backend/router.py` honors explicit translation requests, reply-language instructions, document questions and recency signals. Other messages use general chat, or the existing document route when the conversation has uploads.
3. `backend/main.py` builds the relevant provider messages. General chat uses the original text and recent conversation history. Document chat adds retrieved excerpts. Web chat adds search results. Explicit translation uses the cached translation helper.
4. `backend/llm.py` streams the configured provider. Successful turns are recorded in SQLite. The browser renders text, metadata and returned sources.

The separate legacy form submits stateless JSON to `/chat` on Flask or FastAPI. Both use the same compatibility adapter and general assistant instructions. Trained intent models, bundled FAQ data and classifier evaluation scripts have no role in startup, live routing or document indexing.

See [API](API.md), [models](MODELS.md), and [deployment](DEPLOYMENT.md).
