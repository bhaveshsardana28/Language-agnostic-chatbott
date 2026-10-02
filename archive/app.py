"""
Aikya (ऐक्य) — Multilingual LLM Chatbot
=========================================

ChatGPT-style Streamlit app with:
  • Multi-provider LLM support (OpenAI, Gemini, Claude, DeepSeek, Groq,
    Perplexity, Ollama) with token streaming
  • Adaptive model routing by query complexity
  • Voice input (browser mic via Web Speech API) + TTS output (gTTS)
  • Document chat (PDF/DOCX/TXT) with chunk retrieval + citations
  • Web search (DuckDuckGo, no API key) with Perplexity-style citations
  • Conversation history (SQLite), rename/archive/delete, search
  • Chat export (Markdown / JSON)
  • Language detection + translation, 100+ response languages

Run:
    streamlit run app.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import datetime
import logging
from typing import Optional

import streamlit as st

# Inject project root so "from src import ..." works when running streamlit
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src import db  # noqa: E402
from src.chatbot import get_response, stream_response, generate_title, score_complexity, route_model  # noqa: E402
from src.translation import translate_text  # noqa: E402
from src.detection import detect_language  # noqa: E402
from src import documents as doc_mod  # noqa: E402
from src import web_search  # noqa: E402
from src import voice  # noqa: E402
from src import export  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.expanduser("~"), ".aikya_chatbot")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "app.log")

for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("aikya")

# ---------------------------------------------------------------------------
# Config / settings persistence (local JSON file, no env plumbing required)
# ---------------------------------------------------------------------------
SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".language_agnostic_chatbot", "settings.json"
)

DEFAULT_SETTINGS = {
    "backend": "ollama",
    "model": "llama3.1",
    "target_lang": "auto",
    "auto_route": True,
}


def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            s = {**DEFAULT_SETTINGS, **json.load(f)}
        return s
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(s: dict) -> None:
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("save_settings failed: %s", exc)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Aikya — Multilingual AI",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
      --bg: #0B0D10;
      --surface: #14161B;
      --surface-raised: #1A1C23;
      --surface-hover: #22242D;
      --border: rgba(255,255,255,0.08);
      --text-primary: #F0F2F5;
      --text-secondary: #8B90A0;
      --text-muted: #5C6070;
      --accent: #3B82F6;
      --success: #10B981;
      --warning: #F59E0B;
      --error: #EF4444;
    }

    html, body, .stApp { background-color: var(--bg) !important; font-family: 'Inter', sans-serif !important; }

    [data-testid="stSidebar"] {
        background-color: var(--surface) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 10px;
        border: 1px solid var(--border);
        color: var(--text-primary);
        background: var(--surface-raised);
        transition: all 0.2s ease;
        font-weight: 500;
        padding: 0.55rem 1rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background: var(--surface-hover); }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--accent) !important; color: white !important; border: none !important;
    }

    .stTextInput > div > div > input,
    .stTextArea textarea, .stSelectbox > div > div, .stFileUploader {
        background: var(--surface-raised) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
    }

    .conv-item:hover { background: var(--surface-hover); }
    .conv-item-active {
        background: rgba(59,130,246,0.15) !important;
        border-left: 3px solid var(--accent);
    }

    .ctx-badge {
        display:inline-block; background: rgba(16,185,129,0.15);
        color: var(--success); border: 1px solid rgba(16,185,129,0.3);
        padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; margin-left:6px;
    }
    .ctx-badge.web { background: rgba(59,130,246,0.15); color: #93c5fd; border-color: rgba(59,130,246,0.3); }
    .ctx-badge.doc { background: rgba(245,158,11,0.15); color: #fcd34d; border-color: rgba(245,158,11,0.3); }

    .sources {
        margin-top: 0.5rem; padding: 0.6rem 0.8rem; border-radius: 8px;
        background: var(--surface-raised); border: 1px solid var(--border);
        font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;
    }
    .sources a { color: #93c5fd; text-decoration: none; }
    .sources a:hover { text-decoration: underline; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
persisted = load_settings()


def _init_state():
    defaults = {
        "conversation_id": None,
        "messages": [],
        "search_query": "",
        "backend": persisted["backend"],
        "model": persisted["model"],
        "target_lang": persisted["target_lang"],
        "auto_route": persisted["auto_route"],
        # per-conversation ephemeral context
        "doc_chunks": [],       # List[str] from the last uploaded doc
        "doc_name": None,
        "last_search_hits": [], # List[dict] for displaying citations
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_LANGS = ["auto", "en", "hi", "es", "ja", "fr", "de", "zh", "ar", "it", "pt", "ru", "ko"]
_BACKENDS = ["ollama", "openai", "gemini", "claude", "deepseek", "groq", "perplexity"]


def _provider_available(name: str) -> Optional[str]:
    """If the configured provider has what it needs, return its model; else None."""
    if name == "ollama":
        return st.session_state.model or "llama3.1"
    env = {
        "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
        "claude": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY", "perplexity": "PERPLEXITY_API_KEY",
    }.get(name)
    if env and os.getenv(env):
        return st.session_state.model
    return None


def _available_models() -> dict:
    return {b: _provider_available(b) for b in _BACKENDS if _provider_available(b)}


def _maybe_route(user_input: str) -> tuple:
    """Return (backend, model) either auto-routed or as the user configured."""
    if st.session_state.auto_route:
        avail = _available_models()
        if not avail:
            return "ollama", st.session_state.model or "llama3.1"
        b, m = route_model(user_input, avail)
        return b, m or st.session_state.model
    return st.session_state.backend, st.session_state.model


def _augment_prompt(user_input: str) -> tuple:
    """Return (augmented_prompt, citations_md, badges_html).

    Augments the user prompt with web search results and/or document context.
    """
    citations = ""
    badges = ""
    extra = []

    # Web search: trigger when user asks a factual/recent question without docs.
    looks_factual = any(
        k in user_input.lower()
        for k in ("latest", "today", "news", "current", "2024", "2025", "2026", "now")
    ) or user_input.strip().endswith("?")
    do_web = st.session_state.get("force_web", False) or (
        looks_factual and not st.session_state.doc_chunks
    )
    hits = []
    if do_web:
        try:
            hits = web_search.web_search(user_input, max_results=4)
        except Exception as exc:
            logger.warning("web_search err: %s", exc)
        if hits:
            ctx = web_search.search_context(user_input, max_results=4)
            extra.append(
                "Use these web search results to inform your answer. "
                "Cite them inline as [1], [2], etc.\n\n" + ctx
            )
            citations = web_search.citations_md(hits)
            badges += '<span class="ctx-badge web">🌐 Web</span>'
            st.session_state.last_search_hits = hits

    # Document context
    if st.session_state.doc_chunks:
        doc_ctx, idxs = doc_mod.build_context(
            user_input, st.session_state.doc_chunks, top_k=4
        )
        if doc_ctx:
            extra.append(
                "Answer using the following document excerpts where relevant. "
                "Cite them as [D1], [D2], etc.\n\n" + doc_ctx
            )
            badges += '<span class="ctx-badge doc">📄 Doc</span>'

    if extra:
        augmented = user_input + "\n\n---\nContext:\n\n" + "\n\n".join(extra)
    else:
        augmented = user_input
    return augmented, citations, badges


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<h1 style='font-size: 1.4rem; margin-bottom: 0.8rem;'>💬 Aikya</h1>"
        "<div style='color:#8B90A0; font-size:0.78rem; margin-bottom:1rem;'>"
        "One AI · Every language</div>",
        unsafe_allow_html=True,
    )
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.session_state.doc_chunks = []
        st.session_state.doc_name = None
        st.session_state.last_search_hits = []
        st.rerun()

    search = st.text_input(
        "🔍 Search", value=st.session_state.search_query,
        placeholder="Filter conversations…", label_visibility="collapsed",
    )
    st.session_state.search_query = search

    active = db.get_conversations(
        search=search if search else None, limit=50, include_archived=False
    )
    for conv_id, title, updated_at, _is_arch in active:
        is_current = st.session_state.conversation_id == conv_id
        active_cls = "conv-item-active" if is_current else ""
        col_main, col_act = st.columns([5, 1])
        with col_main:
            if st.button(
                f"💬 {title}", key=f"load_{conv_id}",
                use_container_width=True, help=str(updated_at),
            ):
                st.session_state.conversation_id = conv_id
                st.session_state.messages = [
                    {"role": r, "content": c}
                    for r, c in db.load_conversation_messages(conv_id)
                ]
                st.session_state.doc_chunks = []
                st.session_state.doc_name = None
                st.session_state.last_search_hits = []
                st.rerun()
        with col_act:
            with st.popover("⋯", use_container_width=True):
                new_title = st.text_input("Rename", value=title, key=f"rn_{conv_id}")
                if st.button("Save", key=f"sv_{conv_id}", use_container_width=True):
                    db.rename_conversation(conv_id, new_title.strip() or title)
                    if st.session_state.conversation_id == conv_id:
                        st.rerun()
                st.markdown("---")
                if st.button("📂 Archive", key=f"ar_{conv_id}", use_container_width=True):
                    db.archive_conversation(conv_id)
                    if st.session_state.conversation_id == conv_id:
                        st.session_state.conversation_id = None
                        st.session_state.messages = []
                    st.rerun()
                if st.button("🗑 Delete", key=f"dl_{conv_id}", use_container_width=True):
                    db.delete_conversation(conv_id)
                    if st.session_state.conversation_id == conv_id:
                        st.session_state.conversation_id = None
                        st.session_state.messages = []
                    st.rerun()

    # ---- Settings ----
    with st.expander("⚙️ Settings", expanded=False):
        st.session_state.auto_route = st.checkbox(
            "🧭 Adaptive model routing", value=st.session_state.auto_route,
            help="Auto-pick the best model per query by complexity.",
        )
        backend = st.selectbox(
            "Backend", _BACKENDS,
            index=_BACKENDS.index(st.session_state.backend)
            if st.session_state.backend in _BACKENDS else 0,
        )
        st.session_state.backend = backend

        model = st.text_input("Model", value=st.session_state.model)
        st.session_state.model = model

        target_lang = st.selectbox(
            "Response language", _LANGS,
            index=_LANGS.index(st.session_state.target_lang)
            if st.session_state.target_lang in _LANGS else 0,
        )
        st.session_state.target_lang = target_lang

        st.subheader("API Keys")
        for name, key in [
            ("OpenAI", "OPENAI_API_KEY"),
            ("Gemini", "GEMINI_API_KEY"),
            ("Claude", "ANTHROPIC_API_KEY"),
            ("DeepSeek", "DEEPSEEK_API_KEY"),
            ("Groq", "GROQ_API_KEY"),
            ("Perplexity", "PERPLEXITY_API_KEY"),
        ]:
            val = st.text_input(name, type="password", key=f"key_{key}")
            if val:
                os.environ[key] = val
        st.caption("Ollama uses localhost:11434 — no key needed.")

        if st.button("💾 Save settings", use_container_width=True):
            save_settings({
                "backend": st.session_state.backend,
                "model": st.session_state.model,
                "target_lang": st.session_state.target_lang,
                "auto_route": st.session_state.auto_route,
            })
            st.toast("Settings saved")

    # ---- Document upload ----
    with st.expander("📄 Document chat", expanded=False):
        uploaded = st.file_uploader(
            "Upload PDF / DOCX / TXT", type=["pdf", "docx", "txt", "md"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            try:
                raw = uploaded.read()
                text = doc_mod.extract_text(raw, uploaded.name)
                chunks = doc_mod.chunk_text(text)
                st.session_state.doc_chunks = chunks
                st.session_state.doc_name = uploaded.name
                st.success(
                    f"Loaded **{uploaded.name}** — {len(chunks)} chunks "
                    f"({len(text)} chars). Ask questions below."
                )
            except Exception as exc:
                logger.exception("doc upload failed")
                st.error(f"❌ {exc}")
        if st.session_state.doc_name:
            st.caption(f"Active: {st.session_state.doc_name}")
            if st.button("Clear document", use_container_width=True):
                st.session_state.doc_chunks = []
                st.session_state.doc_name = None
                st.rerun()

    # ---- Web search toggle ----
    st.session_state.force_web = st.checkbox(
        "🌐 Force web search", value=False,
        help="Always include live web results in the answer.",
    )

    # ---- Export ----
    if st.session_state.messages:
        with st.expander("⬇️ Export chat", expanded=False):
            title = "Aikya Chat"
            conv = st.session_state.conversation_id
            if conv:
                convs = [c for c in db.get_conversations(limit=200) if c[0] == conv]
                if convs:
                    title = convs[0][1]
            md = export.to_markdown(title, st.session_state.messages)
            js = export.to_json(title, st.session_state.messages)
            st.download_button("⬇ Markdown", md, f"{title}.md", "text/markdown")
            st.download_button("⬇ JSON", js, f"{title}.json", "application/json")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
backend = st.session_state.backend
model = st.session_state.model
target_lang = st.session_state.target_lang

# Welcome screen
if st.session_state.conversation_id is None and not st.session_state.messages:
    st.markdown(
        """
        <div style="display:flex; flex-direction:column; align-items:center;
                    justify-content:center; min-height:65vh; text-align:center;">
            <div style="font-size:3rem; margin-bottom:0.5rem;">🕊️</div>
            <div style="font-size:2rem; font-weight:700;
                        color:#F0F2F5; margin-bottom:0.5rem;">Aikya</div>
            <div style="font-size:1.05rem; color:#8B90A0; max-width:520px;
                        margin-bottom:0.4rem;">
                One AI · Every language · One conversation at a time.
            </div>
            <div style="font-size:0.82rem; color:#5C6070;">
                Type below, upload a document, toggle web search, or use the 🎤 mic.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Display existing messages with optional source citations
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.markdown(
                f'<div class="sources">{msg["sources"]}</div>',
                unsafe_allow_html=True,
            )
        if msg["role"] == "assistant":
            col_play, _ = st.columns([1, 6])
            if col_play.button("🔊 Play", key=f"tts_{i}", help="Text-to-speech"):
                try:
                    path = voice.text_to_speech(
                        msg["content"], lang=target_lang if target_lang != "auto" else "en"
                    )
                    if path:
                        with open(path, "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
                except Exception as exc:
                    logger.warning("TTS failed: %s", exc)
                    st.toast(f"TTS failed: {exc}")

# ---------------------------------------------------------------------------
# Mic input (browser Web Speech API, no extra dep)
# ---------------------------------------------------------------------------
mic_html = """
<div style="margin-bottom:0.4rem;">
  <button id="aikya_mic" type="button"
    style="background:#1A1C23; border:1px solid rgba(255,255,255,0.08);
           color:#F0F2F5; border-radius:10px; padding:0.45rem 0.8rem;
           cursor:pointer; font-size:0.85rem;">
    🎤 Speak
  </button>
  <span id="aikya_status" style="color:#5C6070; margin-left:0.6rem; font-size:0.78rem;"></span>
</div>
<script>
(function () {
  const btn = document.getElementById('aikya_mic');
  const status = document.getElementById('aikya_status');
  if (!btn) return;
  let listening = false;
  const RC = window.webkitSpeechRecognition || window.SpeechRecognition;
  if (!RC) {
    btn.disabled = true;
    status.textContent = 'Voice not supported in this browser';
    return;
  }
  const rec = new RC();
  rec.lang = '';
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  btn.addEventListener('click', function () {
    if (listening) { rec.stop(); return; }
    // Pass transcript back via a hidden text input that Streamlit can read.
    rec.start();
    listening = true;
    btn.textContent = '⏹ Stop';
    status.textContent = 'Listening…';
  });
  rec.onresult = function (e) {
    const text = e.results[0][0].transcript;
    const ta = parent.document.querySelector('textarea[data-baseweb="textarea-area"]');
    if (ta) {
      // append to the chat input
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      ).set;
      setter.call(ta, (ta.value ? ta.value + ' ' : '') + text);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };
  rec.onerror = function (e) { status.textContent = 'Error: ' + e.error; };
  rec.onend = function () {
    listening = false;
    btn.textContent = '🎤 Speak';
    status.textContent = '';
  };
})();
</script>
"""
st.components.v1.html(mic_html, height=70)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Message Aikya…")
if user_input:
    try:
        detected_lang = detect_language(user_input) or "en"

        # First-time conversation creation
        if st.session_state.conversation_id is None:
            new_conv_id = db.create_conversation(user_input)
            st.session_state.conversation_id = new_conv_id
            st.session_state.messages = [
                {"role": r, "content": c}
                for r, c in db.load_conversation_messages(new_conv_id)
            ]
            conv_id = new_conv_id
        else:
            conv_id = st.session_state.conversation_id
            db.add_message(conv_id, "user", user_input)
            st.session_state.messages.append({"role": "user", "content": user_input})

        # Show the user's newly added message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        # Decide model (auto-route or fixed)
        chosen_backend, chosen_model = _maybe_route(user_input)
        if st.session_state.auto_route and chosen_backend != backend:
            logger.info("routed %s -> %s/%s", backend, chosen_backend, chosen_model)

        # Augment prompt with web/docs context
        augmented, citations, badges = _augment_prompt(user_input)

        # Build chat history (for context window) excluding the just-added user msg,
        # since most providers re-add the latest user message themselves.
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]

        # Generate (stream if supported, else single-shot)
        with st.chat_message("assistant"):
            status_badge = f'<span class="ctx-badge">{chosen_backend}:{chosen_model}</span>'
            with st.empty():
                try:
                    chunks = []
                    for tok in stream_response(
                        augmented, detected_lang,
                        backend=chosen_backend, model=chosen_model,
                        target_lang=target_lang, history=history,
                    ):
                        chunks.append(tok)
                    reply = "".join(chunks)
                except Exception:
                    logger.warning("stream unsupported/failed; single-shot fallback")
                    reply = get_response(
                        augmented, detected_lang,
                        backend=chosen_backend, model=chosen_model,
                        target_lang=target_lang, history=history,
                    )
                # Translation if user forced a different output language
                if target_lang != "auto" and target_lang != detected_lang:
                    try:
                        translated = translate_text(
                            reply, target_lang=target_lang, source_lang=detected_lang
                        )
                        if translated:
                            reply = translated
                    except Exception as exc:
                        logger.warning("translate failed: %s", exc)

                st.markdown(reply)
                if citations:
                    st.markdown(
                        f'<div class="sources"><b>Sources</b><br/>{citations}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(status_badge + badges, unsafe_allow_html=True)

        # Persist
        db.add_message(conv_id, "assistant", reply)
        st.session_state.messages.append(
            {"role": "assistant", "content": reply, "sources": citations}
        )

        # Auto-title on the first exchange
        convs = db.get_conversations(limit=500, include_archived=False)
        cur = [c for c in convs if c[0] == conv_id]
        if cur and cur[0][1] == "Untitled":
            try:
                title = generate_title(user_input, backend=chosen_backend, model=chosen_model)
                db.update_conversation_title(conv_id, title)
            except Exception as exc:
                logger.warning("title gen failed: %s", exc)

        st.rerun()
    except Exception as exc:
        logging.exception("chat processing failed")
        st.error(f"❌ Error: {exc}")
