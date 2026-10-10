/**
 * GAIA Main — Boot, wiring, global event handlers.
 * Loads all modules and initializes the app.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const api = window.GAIA_API;
  const chat = window.GAIA_CHAT;
  const sidebar = window.GAIA_SIDEBAR;
  const settings = window.GAIA_SETTINGS;
  const components = window.GAIA_COMPONENTS;

  // --- Offline banner ---
  function setOffline(off) {
    const banner = document.getElementById('offline');
    const dot = document.getElementById('topbar-dot');
    const txt = document.getElementById('topbar-status');
    banner.classList.toggle('show', off);
    dot.classList.toggle('offline', off);
    txt.textContent = off ? 'Offline' : 'Online';
  }
  document.getElementById('retry-btn')?.addEventListener('click', () => {
    setOffline(false);
    api.health().then(() => setOffline(false)).catch(() => setOffline(true));
  });

  // --- Debug toggle ---
  document.body.classList.toggle('debug', store.get('debug'));
  document.getElementById('debug-btn')?.setAttribute('aria-pressed', store.get('debug'));

  // --- Mock mode toggle (for development) ---
  if (store.get('mockMode')) {
    document.documentElement.classList.add('mock-mode');
    console.log('[GAIA] Mock mode enabled — API calls will return simulated data');
  }

  // --- Welcome background animation ---
  function initWelcomeBg() {
    const welcome = document.getElementById('welcome');
    if (!welcome) return;
    const bg = document.createElement('div');
    bg.className = 'welcome-bg';
    bg.innerHTML = '<div class="welcome-bg__blob"></div><div class="welcome-bg__blob"></div><div class="welcome-bg__blob"></div>';
    welcome.insertBefore(bg, welcome.firstChild);
  }

  // --- Boot sequence ---
  async function boot() {
    // 1. Apply theme immediately (pre-paint)
    settings.applyTheme();

    // 2. Initialize modules
    chat.init?.();
    sidebar.init?.();
    window.GAIA_DOCS?.init?.();
    settings.init?.();
    window.GAIA_VOICE_INPUT?.init?.();
    window.GAIA_VOICE_OUTPUT?.init?.();
    window.GAIA_VOICE_MODE?.init?.();

    // 3. Check backend health
    try {
      const h = await api.health();
      setOffline(false);
      if (h.llm_ready === false) {
        console.warn('[GAIA] LLM not ready:', h.llm_note);
      }
    } catch {
      setOffline(true);
    }

    // 4. Restore conversation or show welcome
    if (store.conversations.length) {
      chat.openConv(store.currentId || store.conversations[0].id);
    } else {
      document.getElementById('welcome').classList.add('show');
    }
    sidebar.renderSidebar?.();
    window.GAIA_DOCS?.refreshDocs?.();

    // 5. Focus composer
    document.getElementById('input')?.focus();

    // 6. Init welcome background
    initWelcomeBg();

    console.log('[GAIA] App initialized');
  }

  // --- Global error handling ---
  window.addEventListener('error', e => console.error('[GAIA] Uncaught error:', e.error));
  window.addEventListener('unhandledrejection', e => console.error('[GAIA] Unhandled rejection:', e.reason));

  // --- Visibility change (pause animations when tab hidden) ---
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) document.body.classList.add('tab-hidden');
    else document.body.classList.remove('tab-hidden');
  });

  // Start
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  // Expose helpers
  window.GAIA_APP = { boot, setOffline };
})();