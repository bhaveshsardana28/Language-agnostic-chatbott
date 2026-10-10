/**
 * GAIA Chat Machine — streaming, rendering, scroll, actions.
 * Pure vanilla, no framework dependencies.
 */
(function () {
  'use strict';

  const api = window.GAIA_API;
  const store = window.GAIA_STORE;

  // --- Wait for markdown functions ---
  function waitForMD() {
    return new Promise(resolve => {
      if (window.md && window.esc && window.speechText) return resolve({ md: window.md, esc: window.esc, speechText: window.speechText });
      const check = setInterval(() => {
        if (window.md && window.esc && window.speechText) { clearInterval(check); resolve({ md: window.md, esc: window.esc, speechText: window.speechText }); }
      }, 10);
    });
  }

  // --- State ---
  let streaming = false;
  let aborter = null;
  let speechBuf = '';
  let spokenSentences = 0;

  // --- DOM refs (lazy init) ---
  let feed, welcome, input, sendBtn, stopBtn, composer, chatEl, jumpBtn, charCount;

  // --- Native language names for chips/dividers ---
  const NATIVE = { en: 'English', hi: 'हिन्दी', pa: 'ਪੰਜਾਬੀ', es: 'Español', fr: 'Français', de: 'Deutsch', it: 'Italiano' };

  // --- Suggestions ---
  const SUGGESTIONS = [
    ['Ask anything', 'Explain quantum computing simply.'],
    ['Code', 'Write a Python function for binary search.'],
    ['Multilingual', 'मशीन लर्निंग कैसे काम करती है?'],
    ['Translate', 'Translate this into German.'],
    ['Documents', 'Summarize the uploaded document.'],
    ['Current info', 'What are the latest developments in AI?']
  ];

  // --- Utility ---
  function uid() { return Math.random().toString(36).slice(2, 10); }
  function relTime(ts) { const d = new Date(ts), now = new Date(), day = 864e5; const t = Math.floor((now - d) / day); if (t <= 0) return 'Today'; if (t === 1) return 'Yesterday'; if (t < 7) return `${t} days ago`; return d.toLocaleDateString(); }
  function groupOf(ts) { const d = new Date(ts); d.setHours(0,0,0,0); const n = new Date(); n.setHours(0,0,0,0); const diff = (n - d) / 864e5; if (diff === 0) return 'Today'; if (diff === 1) return 'Yesterday'; if (diff < 7) return 'Previous 7 days'; return 'Older'; }
  function friendly(err) { if (!err) return 'Something went wrong.'; if (/429|Rate limit/i.test(err)) return 'The assistant is busy — wait a few seconds.'; if (/API_KEY|not configured/i.test(err)) return 'AI not configured on server.'; if (/Failed to fetch|NetworkError/i.test(err)) return 'Unable to connect to the assistant.'; return 'Something went wrong.'; }

  // --- Toast ---
  function toast(t) {
    const container = getToastContainer();
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = t;
    container.appendChild(el);
    setTimeout(() => { el.classList.add('removing'); el.addEventListener('animationend', () => el.remove(), { once: true }); }, 3000);
  }
  function getToastContainer() {
    let c = document.getElementById('toast-container');
    if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.className = 'toast-container'; document.body.appendChild(c); }
    return c;
  }

  // --- Copy ---
  function copyText(t) { return navigator.clipboard?.writeText(t).catch(() => { const ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }); }

  // --- Scroll engine ---
  const NEAR_BOTTOM_PX = 120;
  function isNearBottom() { return chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight <= NEAR_BOTTOM_PX; }
  function scrollBottom() { chatEl.scrollTop = chatEl.scrollHeight; updateJump(); }
  let rafPending = false;
  function scheduleFollow() { if (rafPending) return; rafPending = true; requestAnimationFrame(() => { rafPending = false; if (isNearBottom()) chatEl.scrollTop = chatEl.scrollHeight; updateJump(); }); }
  function updateJump() { const has = feed.children.length > 0; jumpBtn.classList.toggle('show', has && !isNearBottom()); }
  function initScroll() { chatEl.addEventListener('scroll', updateJump, { passive: true }); jumpBtn.addEventListener('click', scrollBottom); }

  // --- Welcome cards ---
  function renderWelcomeCards() {
    const cardsEl = document.getElementById('welcome-cards');
    if (!cardsEl) return;
    cardsEl.innerHTML = '';
    SUGGESTIONS.forEach(([k, q]) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'welcome__card';
      btn.innerHTML = `<span class="welcome__card-label">${window.esc(k)}</span><span class="welcome__card-text">${window.esc(q)}</span>`;
      btn.addEventListener('click', () => send(q));
      cardsEl.appendChild(btn);
    });
  }

  // --- Greeting animation ---
  function startGreetingCycle() {
    const greetEl = document.getElementById('welcome-greeting');
    if (!greetEl || matchMedia('(prefers-reduced-motion: reduce)').matches || store.get('noMotion')) return;
    const GREET = ['Hello', 'नमस्ते', 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ', 'Hola', 'Bonjour', 'Hallo', 'Ciao'];
    let gi = 0;
    setInterval(() => {
      greetEl.style.opacity = '0';
      setTimeout(() => { gi = (gi + 1) % GREET.length; greetEl.textContent = GREET[gi]; greetEl.style.opacity = '1'; }, 260);
    }, 3000);
  }

  // --- Conversation management ---
  function newConv(activate = true) {
    const c = { id: uid(), title: 'New conversation', createdAt: Date.now(), updatedAt: Date.now(), messages: [] };
    store.conversations.unshift(c);
    if (activate) { store.currentId = c.id; }
    store.save();
    if (activate) openConv(c.id);
    renderSidebar();
    return c;
  }

  function openConv(id) {
    if (streaming && aborter) aborter.abort();
    store.currentId = id; store.save();
    const c = store.current;
    document.getElementById('chat-title').textContent = c.title;
    feed.innerHTML = '';
    welcome.classList.toggle('show', !c.messages.length);
    c.messages.forEach(m => paintMsg(m, c, false));
    scrollBottom();
    renderSidebar(); refreshDocs();
    if (innerWidth <= 900) closeDrawer();
  }

  // --- Message painting ---
  function paintMsg(m, c, live = false) {
    const wrap = document.createElement('div');
    wrap.className = `msg ${m.role === 'user' ? 'msg--user' : 'msg--assistant'} ${m.error ? 'msg--error' : ''} ${live ? (m.role === 'assistant' ? 'msg--thinking' : 'msg--streaming') : ''}`;
    wrap.dataset.id = m.ts;

    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble markdown';
    bubble.dir = 'auto';

    if (m.role === 'user') {
      bubble.textContent = m.content;
    } else if (live) {
      bubble.innerHTML = '<div class="skeleton skeleton-row long"></div><div class="skeleton skeleton-row med"></div><div class="skeleton skeleton-row short"></div>';
    } else {
      bubble.innerHTML = m.content_md || window.md(m.content);
    }

    // Language chip
    const lm = m.meta?.language_meta;
    if (m.role !== 'user' && !live && lm?.language) {
      const chip = document.createElement('span');
      chip.className = 'lang-chip';
      chip.textContent = `${NATIVE[lm.language] || lm.language} · ${lm.language_name || lm.language}`;
      if (lm.confidence != null && lm.confidence < 0.5) {
        chip.classList.add('low-conf');
        chip.title = `Detection confidence ${(lm.confidence * 100).toFixed(0)}% — verify language`;
      }
      bubble.prepend(chip);
    }

    // Language switch divider
    if (m.role === 'assistant' && lm?.language && !live) {
      const idx = c.messages.indexOf(m);
      for (let j = idx - 1; j >= 0; j--) {
        const prev = c.messages[j].meta?.language_meta?.language;
        if (c.messages[j].role === 'assistant' && prev && prev !== lm.language) {
          const div = document.createElement('div');
          div.className = 'lang-switch';
          div.innerHTML = `<span>Language switched: ${window.esc(NATIVE[prev] || prev)} → ${window.esc(NATIVE[lm.language] || lm.language)}</span>`;
          feed.appendChild(div);
          break;
        }
      }
    }

    // Day separator
    const prevMsg = c.messages[c.messages.indexOf(m) - 1];
    if (prevMsg && prevMsg.ts && m.ts && new Date(prevMsg.ts).toDateString() !== new Date(m.ts).toDateString()) {
      const dsep = document.createElement('div');
      dsep.className = 'day-sep';
      const g = groupOf(m.ts);
      dsep.innerHTML = `<span>${(g === 'Today' || g === 'Yesterday') ? g : new Date(m.ts).toLocaleDateString()}</span>`;
      feed.appendChild(dsep);
    }

    wrap.appendChild(bubble);

    if (m.role !== 'user' && !live) {
      if (m.sources && m.sources.length) wrap.appendChild(renderSources(m.sources));
      wrap.appendChild(renderActions(m, c));
      const dbg = renderDebug(m); if (dbg) wrap.appendChild(dbg);
      if (m.stopped) {
        const s = document.createElement('div'); s.className = 'msg__stopped'; s.textContent = '(stopped)'; wrap.appendChild(s);
      }
    }

    feed.appendChild(wrap);
    if (live) scheduleFollow();
    return wrap;
  }

  function renderSources(sources) {
    const div = document.createElement('div');
    div.className = 'sources';
    div.innerHTML = '<span class="sources__label">Sources</span>' + sources.map((s, i) => {
      if (s.url) return `<div class="sources__item"><span class="sources__num">${i + 1}.</span><a class="sources__link" href="${window.esc(s.url)}" target="_blank" rel="noopener">${window.esc(s.title || s.url)}</a></div>`;
      if (s.document) return `<div class="sources__item"><span class="sources__num">${i + 1}.</span><span class="sources__doc">${window.esc(s.document)} — chunk ${s.chunk}</span></div>`;
      return `<div class="sources__item"><span class="sources__num">${i + 1}.</span><span class="sources__doc">${window.esc(s.note || 'source')}</span></div>`;
    }).join('');
    return div;
  }

  function renderActions(m, c) {
    const div = document.createElement('div');
    div.className = 'msg__actions';

    if (m.ts) {
      const ts = document.createElement('span');
      ts.className = 'msg__timestamp';
      ts.textContent = new Date(m.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      ts.title = new Date(m.ts).toLocaleString();
      div.appendChild(ts);
    }

    const copyBtn = document.createElement('button');
    copyBtn.className = 'icon-btn';
    copyBtn.setAttribute('aria-label', 'Copy message');
    copyBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>`;
    copyBtn.addEventListener('click', () => copyText(m.content).then(() => toast('Copied')));
    div.appendChild(copyBtn);

    if (m.role === 'assistant') {
      const label = m.error ? 'Retry' : 'Regenerate';
      const act = m.error ? 'retry' : 'regen';
      const btn = document.createElement('button');
      btn.className = 'icon-btn';
      btn.setAttribute('aria-label', label);
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-3-6.7M21 4v5h-5"/></svg>`;
      btn.addEventListener('click', () => regenerate());
      div.appendChild(btn);
    } else {
      const btn = document.createElement('button');
      btn.className = 'icon-btn';
      btn.setAttribute('aria-label', 'Edit and resend');
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z"/></svg>`;
      btn.addEventListener('click', () => editMsg(m, c));
      div.appendChild(btn);
    }

    if (m.role === 'assistant' && !m.error) {
      const btn = document.createElement('button');
      btn.className = 'icon-btn listen-btn';
      btn.setAttribute('aria-label', 'Listen');
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12"/></svg>`;
      btn.addEventListener('click', () => speakMessage(m));
      div.appendChild(btn);
    }

    return div;
  }

  function renderDebug(m) {
    const lm = m.meta?.language_meta || {};
    if (!lm.language && !m.meta?.route && !m.latency) return null;
    const rows = [];
    if (lm.language) rows.push(`<b>Language:</b> ${window.esc(lm.language_name || lm.language)}${lm.confidence != null ? ` (${lm.confidence})` : ''}`);
    if (lm.secondary_languages?.length) rows.push(`<b>Secondary:</b> ${lm.secondary_languages.join(', ')}`);
    if (lm.code_switched) rows.push(`<b>Code-switched:</b> Yes${lm.mixed_script ? ' · mixed-script' : ''}`);
    if (lm.scripts && Object.keys(lm.scripts).length) rows.push(`<b>Scripts:</b> ${Object.keys(lm.scripts).join(' + ')}`);
    if (lm.detection_reason) rows.push(`<b>Detection:</b> ${window.esc(lm.detection_reason)}`);
    if (m.meta?.route) rows.push(`<b>Router:</b> ${window.esc(m.meta.route)}${m.meta.reason ? ` — ${window.esc(m.meta.reason)}` : ''}`);
    if (m.intent) rows.push(`<b>Intent:</b> ${window.esc(m.intent)} (${Math.round((m.confidence || 0) * 100)}%)`);
    if (m.model) rows.push(`<b>Model:</b> ${window.esc(m.model)}`);
    if (m.latency != null) rows.push(`<b>Latency:</b> ${Math.round(m.latency)} ms`);
    if (m.debug_error) rows.push(`<b>Technical:</b> ${window.esc(m.debug_error)}`);
    const d = document.createElement('div');
    d.className = 'debug-card';
    d.innerHTML = rows.join('<br>');
    return d;
  }

  // --- Send / Streaming ---
  async function send(text) {
    text = (text ?? input.value).trim();
    if (!text || streaming) return;
    if (text.length > 4000) { toast('Message too long (max 4,000 characters)'); input.value = text; autoGrow(); return; }
    stopSpeak();
    input.value = ''; autoGrow();

    let c = store.current;
    if (!c) c = newConv(true);

    welcome.classList.remove('show');
    const um = { role: 'user', content: text, ts: Date.now() };
    c.messages.push(um);
    paintMsg(um, c);

    if (c.title === 'New conversation') {
      c.title = text.split(/\s+/).slice(0, 6).join(' ').slice(0, 48);
      document.getElementById('chat-title').textContent = c.title;
    }
    c.updatedAt = Date.now(); store.save();

    await run(c, um);
  }

  async function run(c, um) {
    const am = { role: 'assistant', content: '', ts: Date.now(), meta: null };
    c.messages.push(am);
    speechBuf = ''; spokenSentences = 0;
    const w = paintMsg(am, c, true);
    streaming = true; sendBtn.hidden = true; stopBtn.classList.add('show');
    sendBtn.classList.add('morphing'); stopBtn.classList.add('morphing');
    aborter = new AbortController();
    const bubble = w.querySelector('.msg__bubble');
    let gotMeta = null, intent = null, conf = null;

    try {
      await api.chat(um.content, c.id, {
        meta(ev) { gotMeta = ev; am.meta = ev; const l = ev?.language_meta?.language; if (l && BCP[l]) { store.lastLang = l; store.save(); } },
        delta(ev) {
          am.content += ev.text;
          if (ev.intent !== undefined) { intent = ev.intent; conf = ev.confidence; }
          bubble.textContent = am.content;
          scheduleFollow();
          feedSpeech(ev.text, am.ts, (gotMeta?.response_lang) || (gotMeta?.language_meta?.language) || 'en');
        },
        error(ev) { am.error = true; am.debug_error = ev.message; am.content = am.content || friendly(ev.message); },
        done(ev) { am.latency = ev.latency_ms; am.model = ev.model; am.sources = ev.sources || []; if (ev.model === 'retrieval-gate') am.model = ev.model; }
      }, aborter.signal);
    } catch (err) {
      if (err.name === 'AbortError') { am.content = am.content || ''; am.stopped = true; }
      else { am.error = true; am.debug_error = String(err.message || err); am.content = am.content || friendly(am.debug_error); setOffline(true); }
    } finally {
      streaming = false; aborter = null;
      sendBtn.classList.remove('morphing'); stopBtn.classList.remove('morphing');
      sendBtn.hidden = false; stopBtn.classList.remove('show');

      if (!am.content && !am.error && !am.stopped) {
        am.error = true; am.content = 'The assistant returned an empty response. Please try again.';
      }
      am.content_md = window.md(am.content);
      am.intent = intent; am.confidence = conf;
      c.updatedAt = Date.now(); store.save();

      if (c.id === store.currentId && w.parentNode === feed) {
        feed.removeChild(w); paintMsg(am, c, false); scrollBottom();
      }
      renderSidebar(); refreshDocs();
    }
  }

  function regenerate() {
    if (streaming) return;
    const c = store.current; if (!c) return;
    while (c.messages.length && c.messages[c.messages.length - 1].role !== 'user') c.messages.pop();
    const um = c.messages[c.messages.length - 1];
    if (!um) return; store.save();
    openConv(c.id); run(c, um);
  }

  function editMsg(m, c) {
    if (streaming) return;
    const i = c.messages.indexOf(m);
    c.messages.splice(i); store.save(); openConv(c.id);
    input.value = m.content; autoGrow(); input.focus();
  }

  // --- Composer ---
  function autoGrow() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 200) + 'px'; }
  function updateCharCount() {
    const len = input.value.length;
    if (len > 3200) {
      charCount.textContent = `${len} / 4000`;
      charCount.className = 'char-count' + (len > 4000 ? ' over' : len > 3600 ? ' warn' : '');
      sendBtn.disabled = len > 4000;
    } else { charCount.textContent = ''; charCount.className = 'char-count'; sendBtn.disabled = false; }
  }

  // --- Voice output integration ---
  const BCP = { en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT' };
  let speakQueue = [], speakingTs = null, speakPaused = false;

  function voicesFor(lang) {
    const s = window.speechSynthesis; if (!s) return [];
    const base = (BCP[lang] || lang || 'en').split('-')[0].toLowerCase();
    return s.getVoices().filter(v => v.lang && v.lang.toLowerCase().startsWith(base));
  }

  function stopSpeak() {
    const s = window.speechSynthesis;
    if (s) s.cancel();
    speakQueue = []; speakingTs = null; speakPaused = false; updateListenUI();
  }

  function speakNext() {
    const s = window.speechSynthesis;
    if (!s || !speakQueue.length) { speakingTs = null; updateListenUI(); return; }
    const item = speakQueue.shift();
    const vs = voicesFor(item.lang);
    if (!vs.length) { toast(`No voice available for ${NATIVE[item.lang] || item.lang} on this device.`); return speakNext(); }
    const u = new SpeechSynthesisUtterance(item.text);
    u.voice = vs[0]; u.lang = vs[0].lang; u.rate = store.get('speakRate') || 1;
    u.onend = u.onerror = () => speakNext();
    s.speak(u);
  }

  function speakMessage(m) {
    if (speakingTs === m.ts) {
      const s = window.speechSynthesis;
      if (!s) { stopSpeak(); return; }
      if (speakPaused) { if (typeof s.resume === 'function') { s.resume(); speakPaused = false; } }
      else if (typeof s.pause === 'function') { s.pause(); speakPaused = true; }
      else { stopSpeak(); }
      updateListenUI(); return;
    }
    stopSpeak();
    const lang = m.meta?.language_meta?.language || 'en';
    const text = window.speechText(m.content);
    if (!text) { toast('Nothing to read aloud.'); return; }
    speakQueue = [{ text, lang }]; speakingTs = m.ts; speakPaused = false; updateListenUI(); speakNext();
  }

  function updateListenUI() {
    document.querySelectorAll('.listen-btn').forEach(b => {
      const ts = b.closest('.msg')?.dataset.id;
      const mine = ts && ts === String(speakingTs);
      b.classList.toggle('speaking', !!mine && !speakPaused);
      b.classList.toggle('paused', !!mine && speakPaused);
      b.setAttribute('aria-label', mine ? (speakPaused ? 'Resume reading' : 'Pause reading') : 'Listen');
    });
  }

  function feedSpeech(delta, ts, lang) {
    if (!store.get('autoRead') || !window.speechSynthesis) return;
    speechBuf += delta;
    const parts = window.speechText(speechBuf).split(/(?<=[.!?।])\s+/).filter(s => s.trim().length > 1);
    while (parts.length > spokenSentences) {
      const text = parts[spokenSentences++].trim();
      speakQueue.push({ text, lang });
      if (!speakingTs) { speakingTs = Number(ts); updateListenUI(); }
      speakNext();
    }
  }

  // --- Init ---
  async function init() {
    const { md: mdFn, esc: escFn, speechText: speechTextFn } = await waitForMD();
    window.md = mdFn; window.esc = escFn; window.speechText = speechTextFn;

    feed = document.getElementById('feed');
    welcome = document.getElementById('welcome');
    input = document.getElementById('input');
    sendBtn = document.getElementById('send');
    stopBtn = document.getElementById('stop');
    composer = document.getElementById('composer');
    chatEl = document.getElementById('chat');
    jumpBtn = document.getElementById('jump');
    charCount = document.getElementById('char-count');

    initScroll();
    renderWelcomeCards();
    startGreetingCycle();

    composer.addEventListener('submit', e => { e.preventDefault(); send(); });
    input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && store.get('enterSend')) { e.preventDefault(); send(); } });
    input.addEventListener('input', () => { autoGrow(); updateCharCount(); });
    stopBtn.addEventListener('click', () => aborter?.abort());
  }

  // Expose for other modules
  window.GAIA_CHAT = { send, openConv, newConv, paintMsg, toast, stopSpeak, speakMessage };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();