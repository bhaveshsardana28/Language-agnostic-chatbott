"use strict";

// All transport and API-contract choices live here. No credentials are needed.
const CONFIG = Object.freeze({
  endpoint: "/chat",
  method: "POST",
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  timeoutMs: 45000,
  requestBody: (message, language) => ({ message, language: language || null }),
  fields: {
    reply: "reply", language: "detected_language", confidence: "confidence", intent: "intent",
    // Compatibility with this workspace's unchanged Flask response.
    legacyLanguage: "lang", legacyMetadata: "language_meta"
  }
});

const LANGUAGES = {
  en: {
    name: "English", native: "English", greeting: "Hello. नमस्ते. Hola.",
    subtitle: "What would you like to explore? Ask in your language.",
    placeholder: "Ask a question in your language…",
    prompts: ["Why is the sky blue?", "Help me plan my week.", "How do I write a clear email?", "Explain recursion with an example."]
  },
  hi: {
    name: "Hindi", native: "हिन्दी", greeting: "नमस्ते। कुछ पूछिए।",
    subtitle: "क्या जानना चाहेंगे? अपनी भाषा में पूछिए।",
    placeholder: "अपना सवाल यहाँ लिखिए…",
    prompts: ["आसमान नीला क्यों है?", "मेरा सप्ताह व्यवस्थित करने में मदद करें।", "एक छोटा ईमेल कैसे लिखूँ?", "मुझे एक कहानी सुनाइए।"]
  },
  pa: {
    name: "Punjabi", native: "ਪੰਜਾਬੀ", greeting: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ। ਗੱਲ ਕਰੀਏ।",
    subtitle: "ਤੁਸੀਂ ਕੀ ਜਾਣਨਾ ਚਾਹੁੰਦੇ ਹੋ? ਆਪਣੀ ਭਾਸ਼ਾ ਵਿੱਚ ਪੁੱਛੋ।",
    placeholder: "ਆਪਣਾ ਸਵਾਲ ਇੱਥੇ ਲਿਖੋ…",
    prompts: ["ਅਸਮਾਨ ਨੀਲਾ ਕਿਉਂ ਹੈ?", "ਮੇਰਾ ਹਫ਼ਤਾ ਯੋਜਨਾਬੱਧ ਕਰਨ ਵਿੱਚ ਮਦਦ ਕਰੋ।", "ਇੱਕ ਛੋਟੀ ਈਮੇਲ ਕਿਵੇਂ ਲਿਖਾਂ?", "ਮੈਨੂੰ ਇੱਕ ਕਹਾਣੀ ਸੁਣਾਓ।"]
  },
  es: {
    name: "Spanish", native: "Español", greeting: "Hola. Hablemos.",
    subtitle: "¿Qué te gustaría explorar? Pregunta en tu idioma.",
    placeholder: "Escribe tu pregunta aquí…",
    prompts: ["¿Por qué el cielo es azul?", "Ayúdame a planificar mi semana.", "¿Cómo escribo un correo claro?", "Cuéntame una historia corta."]
  },
  fr: {
    name: "French", native: "Français", greeting: "Bonjour. Parlons ensemble.",
    subtitle: "Que souhaitez-vous explorer ? Posez votre question dans votre langue.",
    placeholder: "Écrivez votre question ici…",
    prompts: ["Pourquoi le ciel est-il bleu ?", "Aidez-moi à planifier ma semaine.", "Comment écrire un courriel clair ?", "Racontez-moi une histoire courte."]
  },
  de: {
    name: "German", native: "Deutsch", greeting: "Hallo. Reden wir miteinander.",
    subtitle: "Was möchtest du erkunden? Frag in deiner Sprache.",
    placeholder: "Schreibe deine Frage hier…",
    prompts: ["Warum ist der Himmel blau?", "Hilf mir, meine Woche zu planen.", "Wie schreibe ich eine klare E-Mail?", "Erzähl mir eine kurze Geschichte."]
  }
};

// Session memory only: never write messages or preferences to browser storage.
const state = { turns: [], request: null, composing: false, theme: "system" };
const ui = Object.fromEntries([
  "chat-form", "message-input", "send-button", "language-select", "messages",
  "chat-scroll", "welcome", "welcome-title", "welcome-subtitle", "suggestions",
  "typing-indicator", "composer-status", "clear-chat", "theme-toggle", "theme-label", "announcer"
].map(id => [id, document.getElementById(id)]));
const timeFormat = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

// Rendering: every dynamic string goes through textContent, never HTML parsing.
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function languageName(code) {
  const language = LANGUAGES[code?.split("-")[0]];
  if (!language) return code || "Not available";
  return language.name === language.native ? language.name : `${language.name} · ${language.native}`;
}

function percentage(value) {
  return value === null ? "Not provided" : `${Math.round(value * 100)}%`;
}

function scrollToLatest() {
  requestAnimationFrame(() => ui["chat-scroll"].scrollTo({
    top: ui["chat-scroll"].scrollHeight,
    behavior: reducedMotion.matches ? "instant" : "smooth"
  }));
}

function renderDetails(data) {
  const details = element("details", "translation-details");
  details.dir = "ltr";
  details.lang = "en";
  details.append(element("summary", "", "Show translation details"));
  const list = element("dl", "details-grid");
  for (const [label, value] of [
    ["Detected language", languageName(data.language)],
    ["Detection confidence", percentage(data.confidence)],
    ["Intent", data.intent || "Not provided"]
  ]) {
    const description = element("dd", "", value);
    description.dir = "auto";
    list.append(element("dt", "", label), description);
  }
  details.append(list);
  return details;
}

function renderMessage(role, text, data = null, language = null) {
  const article = element("article", `message message--${role}`);
  article.dataset.role = role;
  const name = role === "user" ? "You" : role === "assistant" ? "LANGUAGE AGNOSTIC CHATBOT" : "Connection notice";
  const meta = element("div", "message-meta");
  const now = new Date();
  const time = element("time", "", timeFormat.format(now));
  time.dateTime = now.toISOString();
  time.title = now.toLocaleString();
  meta.append(element("strong", "", name), time);
  const bubble = element("div", "bubble");
  bubble.dir = "auto";
  const content = element("p", "message-text", text);
  content.dir = "auto";
  if (language) content.lang = language;
  bubble.append(content);
  if (data) {
    const score = data.confidence === null ? "" : ` (${percentage(data.confidence)})`;
    const badge = element("span", "language-badge", `Detected: ${languageName(data.language)}${score}`);
    badge.dir = "ltr";
    bubble.append(badge, renderDetails(data));
  }
  article.append(meta, bubble);
  return article;
}

function showResponse(turn, article) {
  // A retry replaces its own error in place, even after later conversation turns.
  if (turn.responseElement) turn.responseElement.replaceWith(article);
  else ui.messages.append(article);
  turn.responseElement = article;
  scrollToLatest();
}

function renderError(turn, message) {
  const article = renderMessage("error", message);
  const retry = element("button", "retry-button", "Retry");
  retry.type = "button";
  retry.setAttribute("aria-label", "Retry this message");
  retry.addEventListener("click", () => {
    ui["message-input"].focus({ preventScroll: true });
    runTurn(turn);
  });
  article.querySelector(".bubble").append(retry);
  showResponse(turn, article);
}

// API boundary: reject invalid responses; never display raw server errors.
function normalizeReply(data) {
  const fields = CONFIG.fields;
  if (!data || typeof data !== "object" || Array.isArray(data) ||
      typeof data[fields.reply] !== "string" || !data[fields.reply].trim()) {
    throw new Error("Invalid chat response");
  }
  const canonical = Object.prototype.hasOwnProperty.call(data, fields.language);
  const rawLanguage = data[canonical ? fields.language : fields.legacyLanguage];
  // Legacy top-level confidence measures INTENT, not language detection.
  const rawConfidence = canonical ? data[fields.confidence] : data[fields.legacyMetadata]?.[fields.confidence];
  return {
    reply: data[fields.reply],
    responseLanguage: typeof data.response_language === "string" ? data.response_language : null,
    language: typeof rawLanguage === "string" && /^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/i.test(rawLanguage)
      ? rawLanguage.toLowerCase() : null,
    confidence: typeof rawConfidence === "number" && Number.isFinite(rawConfidence) &&
      rawConfidence >= 0 && rawConfidence <= 1 ? rawConfidence : null,
    intent: typeof data[fields.intent] === "string" ? data[fields.intent].trim() : null
  };
}

async function requestReply(payload, signal) {
  const response = await fetch(CONFIG.endpoint, {
    method: CONFIG.method, headers: CONFIG.headers,
    body: JSON.stringify(payload), signal, credentials: "same-origin", cache: "no-store"
  });
  if (!response.ok) throw new Error("Chat request failed");
  return normalizeReply(await response.json());
}

// State transitions: one in-flight turn; drafts remain editable while waiting.
async function runTurn(turn) {
  if (state.request || !state.turns.includes(turn)) return;
  const request = { controller: new AbortController(), timedOut: false };
  state.request = request;
  syncControls();
  scrollToLatest();
  const timeout = window.setTimeout(() => {
    request.timedOut = true;
    request.controller.abort();
  }, CONFIG.timeoutMs);
  try {
    const data = await requestReply(turn.payload, request.controller.signal);
    if (state.request !== request) return;
    showResponse(turn, renderMessage("assistant", data.reply, data, data.responseLanguage || data.language));
  } catch {
    // Clear-chat invalidates the request before aborting; stale results vanish.
    if (state.request !== request) return;
    renderError(turn, request.timedOut
      ? "That reply is taking longer than expected. Please try again."
      : "Sorry, we couldn't get a reply. Check your connection and try again.");
  } finally {
    window.clearTimeout(timeout);
    if (state.request === request) {
      state.request = null;
      syncControls();
    }
  }
}

function submitMessage() {
  const text = ui["message-input"].value.trim();
  if (!text || state.request || state.composing) return;
  const language = ui["language-select"].value || null;
  const turn = { payload: CONFIG.requestBody(text, language), responseElement: null };
  state.turns.push(turn);
  ui.messages.append(renderMessage("user", text, null, language));
  ui["message-input"].value = "";
  resizeInput();
  ui["message-input"].focus({ preventScroll: true });
  runTurn(turn);
}

function clearConversation() {
  const request = state.request;
  state.request = null;
  request?.controller.abort();
  state.turns = [];
  state.composing = false;
  ui.messages.replaceChildren();
  ui["message-input"].value = "";
  resizeInput();
  syncControls();
  ui["announcer"].textContent = "Conversation cleared. Start a new chat.";
  ui["message-input"].focus({ preventScroll: true });
}

function resizeInput() {
  const input = ui["message-input"];
  input.style.height = "auto";
  input.style.height = `${Math.min(160, Math.max(52, input.scrollHeight))}px`;
}

function syncControls() {
  const busy = Boolean(state.request);
  const hasDraft = Boolean(ui["message-input"].value.trim());
  ui["send-button"].disabled = busy || state.composing || !hasDraft;
  ui["clear-chat"].disabled = !state.turns.length && !hasDraft;
  ui["typing-indicator"].hidden = !busy;
  ui.welcome.hidden = state.turns.length > 0;
  ui["chat-form"].setAttribute("aria-busy", String(busy));
  const language = LANGUAGES[ui["language-select"].value];
  ui["composer-status"].textContent = busy ? "Waiting for a reply…"
    : language ? `${language.name} selected` : "Auto-detect enabled";
  for (const button of ui.messages.querySelectorAll(".retry-button")) button.disabled = busy;
}

function updateLanguage() {
  const code = ui["language-select"].value || "en";
  const language = LANGUAGES[code];
  for (const [id, text] of [["welcome-title", language.greeting], ["welcome-subtitle", language.subtitle]]) {
    ui[id].textContent = text;
    ui[id].lang = code;
    ui[id].dir = "auto";
  }
  ui["message-input"].placeholder = language.placeholder;
  if (ui["language-select"].value) ui["message-input"].lang = code;
  else ui["message-input"].removeAttribute("lang");
  ui.suggestions.replaceChildren();
  for (const prompt of language.prompts) {
    const chip = element("button", "prompt-chip");
    chip.type = "button";
    chip.lang = code;
    chip.dir = "auto";
    const arrow = element("span", "prompt-arrow", "↗");
    arrow.setAttribute("aria-hidden", "true");
    chip.append(element("span", "", prompt), arrow);
    chip.addEventListener("click", () => {
      ui["message-input"].value = prompt;
      resizeInput();
      syncControls();
      ui["message-input"].focus();
    });
    ui.suggestions.append(chip);
  }
  resizeInput();
  syncControls();
}

function cycleTheme() {
  const themes = ["system", "light", "dark"];
  const index = (themes.indexOf(state.theme) + 1) % themes.length;
  state.theme = themes[index];
  document.documentElement.dataset.theme = state.theme;
  ui["theme-label"].textContent = state.theme[0].toUpperCase() + state.theme.slice(1);
  ui["theme-toggle"].setAttribute("aria-label", `Theme: ${state.theme}. Switch to ${themes[(index + 1) % themes.length]} theme`);
}

// UI events: a native form plus IME-aware Enter handling.
function initialize() {
  for (const [code, language] of Object.entries(LANGUAGES)) {
    const label = language.native === language.name ? language.name : `${language.native} — ${language.name}`;
    const option = element("option", "", label);
    option.value = code;
    option.lang = code;
    ui["language-select"].append(option);
  }
  ui["language-select"].value = "";
  ui["message-input"].value = "";
  ui["chat-form"].addEventListener("submit", event => {
    event.preventDefault();
    submitMessage();
  });
  ui["message-input"].addEventListener("input", () => { resizeInput(); syncControls(); });
  ui["message-input"].addEventListener("compositionstart", () => { state.composing = true; syncControls(); });
  ui["message-input"].addEventListener("compositionend", () => { state.composing = false; syncControls(); });
  ui["message-input"].addEventListener("keydown", event => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing || state.composing || event.keyCode === 229) return;
    event.preventDefault();
    ui["chat-form"].requestSubmit();
  });
  ui["language-select"].addEventListener("change", updateLanguage);
  ui["clear-chat"].addEventListener("click", clearConversation);
  ui["theme-toggle"].addEventListener("click", cycleTheme);
  window.addEventListener("resize", resizeInput);
  updateLanguage();
}

initialize();
