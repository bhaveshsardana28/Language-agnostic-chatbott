/**
 * GAIA Settings — theme, chat behavior, speech, privacy, about.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;
  const api = window.GAIA_API;

  function openSettings() {
    const html = `<header><h2 id="modal-h">Settings</h2><button class="icon-btn" data-close aria-label="Close"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6 6 18"/></svg></button></header>
    <div class="dialog__body">
      <div class="settings__sect"><h3>Appearance</h3>
        <div class="tabs" id="theme-tabs" role="tablist">
          <button class="tabs__btn" role="tab" data-t="dark" aria-selected="false">Dark</button>
          <button class="tabs__btn" role="tab" data-t="light" aria-selected="false">Light</button>
          <button class="tabs__btn" role="tab" data-t="system" aria-selected="false">System</button>
        </div></div>

      <div class="settings__sect"><h3>Chat</h3>
        <label class="checkbox"><input type="checkbox" id="set-enter-send"><span class="checkbox__box"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg></span>Enter key sends message</label>
        <label class="checkbox" style="margin-top:var(--sp-2)"><input type="checkbox" id="set-reduce-motion"><span class="checkbox__box"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg></span>Reduce motion (disable animations)</label>

        <div class="settings__row" style="margin-top:var(--sp-3)">
          <label for="set-speech-lang" style="font-size:var(--fs-sm)">Speech language</label>
          <select id="set-speech-lang" class="select" aria-label="Speech language">
            <option value="auto">Auto (last chat language)</option>
            <option value="en-IN">English</option>
            <option value="hi-IN">हिन्दी — Hindi</option>
            <option value="pa-IN">ਪੰਜਾਬੀ — Punjabi</option>
            <option value="es-ES">Español</option>
            <option value="fr-FR">Français</option>
            <option value="de-DE">Deutsch</option>
            <option value="it-IT">Italiano</option>
          </select>
        </div>

        <label class="checkbox" style="margin-top:var(--sp-3)"><input type="checkbox" id="set-auto-read"><span class="checkbox__box"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L19 7"/></svg></span>Read replies aloud</label>

        <div class="settings__row" style="margin-top:var(--sp-2)">
          <label for="set-speak-rate" style="font-size:var(--fs-sm)">Speech rate</label>
          <select id="set-speak-rate" class="select" aria-label="Speech rate">
            <option value="0.75">0.75×</option>
            <option value="1">1.0×</option>
            <option value="1.25">1.25×</option>
            <option value="1.5">1.5×</option>
          </select>
        </div>
      </div>

      <div class="settings__sect"><h3>Privacy</h3>
        <p style="color:var(--text-subtle);font-size:var(--fs-xs);line-height:var(--lh-relaxed)">No login required. Conversations live in this browser only; uploaded documents are scoped to each chat and deleted with it. Voice input uses your browser's speech recognition — this app stores no audio.</p>
        <button class="btn btn--danger" id="set-delete-all">Delete all local data</button>
      </div>

      <div class="settings__sect"><h3>About</h3><div id="settings-about" style="color:var(--text-subtle);font-size:var(--fs-xs);line-height:var(--lh-relaxed)">Loading…</div></div>
    </div>`;

    const m = modal(html);
    const tabsEl = m.el.querySelector('#theme-tabs');
    const syncTabs = () => tabsEl.querySelectorAll('.tabs__btn').forEach(b => {
      const active = b.dataset.t === store.get('theme');
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active);
    });
    syncTabs();
    tabsEl.querySelectorAll('.tabs__btn').forEach(b => b.addEventListener('click', () => { store.set('theme', b.dataset.t); applyTheme(); syncTabs(); }));

    m.el.querySelector('#set-enter-send').checked = store.get('enterSend');
    m.el.querySelector('#set-enter-send').addEventListener('change', e => { store.set('enterSend', e.target.checked); });

    m.el.querySelector('#set-reduce-motion').checked = store.get('noMotion');
    m.el.querySelector('#set-reduce-motion').addEventListener('change', e => { store.set('noMotion', e.target.checked); applyMotion(); });

    const slang = m.el.querySelector('#set-speech-lang');
    slang.value = store.get('speechLang') || 'auto';
    slang.addEventListener('change', e => { store.set('speechLang', e.target.value); });

    m.el.querySelector('#set-auto-read').checked = store.get('autoRead');
    m.el.querySelector('#set-auto-read').addEventListener('change', e => { store.set('autoRead', e.target.checked); if (!e.target.checked) chat.stopSpeak(); });

    const srate = m.el.querySelector('#set-speak-rate');
    srate.value = String(store.get('speakRate') || '1');
    srate.addEventListener('change', e => { store.set('speakRate', parseFloat(e.target.value)); });

    m.el.querySelector('#set-delete-all').addEventListener('click', () => { m.close(); deleteAllData(); });

    api.health().then(h => {
      m.el.querySelector('#settings-about').innerHTML = `<b>Global Multilingual AI Assistant</b> v2.0<br>
        Multilingual chat · cross-language RAG · translation · web search<br>
        Provider: <b>${window.esc(h.llm_provider)}</b> · Model: <b>${window.esc(h.llm_model)}</b> · LLM ready: ${h.llm_ready ? 'yes' : 'no'}<br>
        Tested languages: English, Hindi, Punjabi, Spanish, French, German, Italian`;
    }).catch(() => { m.el.querySelector('#settings-about').textContent = 'Backend unreachable.'; });
  }

  function modal(html, onClose) {
    const ov = document.getElementById('overlay-m');
    ov.innerHTML = `<div class="dialog" role="dialog" aria-modal="true" aria-labelledby="modal-h">${html}</div>`;
    ov.classList.add('open');
    const close = () => { ov.classList.remove('open'); document.removeEventListener('keydown', escFn); if (onClose) onClose(); };
    const escFn = e => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', escFn);
    ov.onclick = e => { if (e.target === ov) close(); };
    ov.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', close));
    ov.querySelector('button')?.focus();
    return { el: ov.firstElementChild, close };
  }

  function applyTheme() {
    const t = store.get('theme');
    document.documentElement.dataset.theme = (t === 'system') ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : t;
    store.save();
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => { if (store.get('theme') === 'system') applyTheme(); });

  function applyMotion() {
    document.body.classList.toggle('reduce-motion', store.get('noMotion'));
  }

  async function deleteAllData() {
    if (!await confirmModal('Delete everything?', 'All local chats will be removed. Server-side conversation data for the current chat will also be deleted.')) return;
    if (store.current) api.deleteConversation(store.current.id).catch(() => {});
    localStorage.removeItem('gaia.store.v1');
    store.data = { conversations: [], currentId: null, theme: 'dark', enterSend: true, debug: false, speechLang: 'auto', lastLang: 'en', noMotion: false, autoRead: false, speakRate: 1, sideCollapsed: false, mockMode: false };
    document.body.classList.remove('debug'); document.getElementById('debug-btn')?.setAttribute('aria-pressed', 'false');
    applyTheme(); applyMotion(); store.save();
    document.getElementById('feed').innerHTML = ''; document.getElementById('welcome').classList.add('show');
    document.getElementById('chat-title').textContent = 'New conversation'; window.GAIA_SIDEBAR.renderSidebar(); window.GAIA_DOCS?.refreshDocs();
    chat.toast('All local data deleted');
  }

  function confirmModal(title, body) {
    return new Promise(res => {
const html = `<header><h2 id="modal-h">${window.esc(title)}</h2><button class="icon-btn" data-close aria-label="Close"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6 6 18"/></svg></button></header>
      <div class="dialog__body"><p>${window.esc(body)}</p><div class="dialog__footer"><button class="btn btn--ghost" data-x>Cancel</button><button class="btn btn--danger" data-y>Delete</button></div></div>`;
      const m = modal(html, () => res(false));
      m.el.querySelector('[data-y]').onclick = () => { m.close(); res(true); };
      m.el.querySelector('[data-x]').onclick = () => { m.close(); res(false); };
    });
  }

  function init() {
    document.getElementById('settings-btn').addEventListener('click', openSettings);
    document.getElementById('hdr-settings').addEventListener('click', openSettings);
    document.getElementById('del-all-side').addEventListener('click', deleteAllData);

    document.getElementById('theme-btn').addEventListener('click', () => {
      const cur = document.documentElement.dataset.theme;
      store.set('theme', cur === 'dark' ? 'light' : 'dark'); applyTheme();
    });

    document.getElementById('debug-btn').addEventListener('click', () => {
      store.set('debug', !store.get('debug'));
      document.body.classList.toggle('debug', store.get('debug'));
      document.getElementById('debug-btn').setAttribute('aria-pressed', store.get('debug'));
    });

    applyTheme(); applyMotion();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // Expose for sidebar
  window.GAIA_SETTINGS = { openSettings, confirmModal, modal, applyTheme, applyMotion };
})();