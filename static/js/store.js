/**
 * GAIA Store — localStorage wrapper with single source of truth.
 * No accounts by design; everything lives in this browser.
 */
(function () {
  'use strict';

  const KEY = 'gaia.store.v1';

  const DEFAULTS = {
    conversations: [],
    currentId: null,
    theme: 'system',        // 'dark' | 'light' | 'system'
    enterSend: true,        // Enter sends, Shift+Enter newline
    debug: false,           // Debug drawer
    speechLang: 'auto',     // 'auto' | BCP-47 code
    lastLang: 'en',         // last detected chat language
    noMotion: false,        // Reduce motion setting
    autoRead: false,        // Auto-read replies aloud
    speakRate: 1,           // Speech rate 0.75-1.5
    sideCollapsed: false,   // Desktop sidebar collapsed
    mockMode: false         // Mock API mode
  };

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return { ...DEFAULTS };
      const parsed = JSON.parse(raw);
      return { ...DEFAULTS, ...parsed };
    } catch {
      return { ...DEFAULTS };
    }
  }

  const store = {
    data: load(),

    get(key) { return this.data[key]; },

    set(key, value) {
      this.data[key] = value;
      this.save();
    },

    setMany(obj) {
      Object.assign(this.data, obj);
      this.save();
    },

    save() {
      try {
        localStorage.setItem(KEY, JSON.stringify(this.data));
      } catch (e) {
        console.warn('Storage quota exceeded', e);
        if (!this._warned || Date.now() - this._warned > 60000) {
          this._warned = Date.now();
          if (window.GAIA_TOAST) window.GAIA_TOAST('Storage full — export and delete old chats to save new ones.');
        }
      }
    },

    clear() {
      localStorage.removeItem(KEY);
      this.data = { ...DEFAULTS };
    },

    // Conversation helpers
    get conversations() { return this.data.conversations; },
    set conversations(v) { this.data.conversations = v; this.save(); },

    get currentId() { return this.data.currentId; },
    set currentId(v) { this.data.currentId = v; this.save(); },

    get current() { return this.data.conversations.find(c => c.id === this.data.currentId); },

    addConversation(conv) {
      this.data.conversations.unshift(conv);
      this.data.currentId = conv.id;
      this.save();
    },

    deleteConversation(id) {
      this.data.conversations = this.data.conversations.filter(c => c.id !== id);
      if (this.data.currentId === id) {
        this.data.currentId = this.data.conversations[0]?.id || null;
      }
      this.save();
    },

    updateConversation(id, patch) {
      const idx = this.data.conversations.findIndex(c => c.id === id);
      if (idx >= 0) {
        Object.assign(this.data.conversations[idx], patch);
        this.save();
      }
    }
  };

  window.GAIA_STORE = store;
})();