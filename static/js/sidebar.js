/**
 * GAIA Sidebar — conversation history, search, CRUD, drawer.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;

  let listEl, searchEl, sidebar, scrim, menuBtn, inputEl;

  function renderSidebar() {
    const q = searchEl.value.trim().toLowerCase();
    const cs = store.conversations.filter(c =>
      !q || c.title.toLowerCase().includes(q) ||
      c.messages.some(m => m.content.toLowerCase().includes(q))
    );
    listEl.innerHTML = '';
    if (!cs.length) {
      listEl.innerHTML = `<p class="sidebar__empty">${q ? 'No matching chats.' : 'No conversations yet.'}</p>`;
      return;
    }
    let lastG = null;
    [...cs].sort((a, b) => b.updatedAt - a.updatedAt).forEach(c => {
      const g = groupOf(c.updatedAt);
      if (g !== lastG) {
        lastG = g;
        const h = document.createElement('div');
        h.className = 'sidebar__group';
        h.textContent = g;
        listEl.appendChild(h);
      }
      let snip = '';
      if (q) {
        const hit = c.messages.find(m => m.content.toLowerCase().includes(q));
        if (hit && !c.title.toLowerCase().includes(q)) {
          const at = hit.content.toLowerCase().indexOf(q);
          snip = window.esc((at > 25 ? '…' : '') + hit.content.slice(Math.max(0, at - 25), at + 45).trim() + (hit.content.length > at + 45 ? '…' : ''));
        }
      }
      const item = document.createElement('div');
      item.innerHTML = `<div class="sidebar__item${c.id === store.currentId ? ' active' : ''}" role="button" tabindex="0" aria-label="Open chat: ${window.esc(c.title)}" title="${window.esc(c.title)}">
        <span class="sidebar__item-title">${window.esc(c.title)}${snip ? `<span class="sidebar__item-snippet">${snip}</span>` : ''}</span>
        <span class="sidebar__item-actions">
          <button class="icon-btn" aria-label="Export chat" data-action="export"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M7 10l5 5 5-5M4 19h16"/></svg></button>
          <button class="icon-btn" aria-label="Rename chat" data-action="rename"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z"/></svg></button>
          <button class="icon-btn" aria-label="Delete chat" data-action="delete"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg></button>
        </span></div>`;
      const row = item.querySelector('.sidebar__item');
      row.addEventListener('click', e => {
        if (e.target.closest('[data-action]')) return;
        chat.openConv(c.id); closeDrawer();
      });
      row.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); chat.openConv(c.id); closeDrawer(); } });
      item.querySelector('[data-action="export"]').addEventListener('click', () => exportConv(c));
      item.querySelector('[data-action="rename"]').addEventListener('click', () => renameConv(c));
      item.querySelector('[data-action="delete"]').addEventListener('click', async () => {
        if (!await confirmModal('Delete chat?', `"${c.title.slice(0, 40)}" and its server-side documents will be deleted.`)) return;
        api.deleteConversation(c.id).catch(() => {});
        store.conversations = store.conversations.filter(x => x.id !== c.id);
        if (store.currentId === c.id) { store.currentId = null; feed.innerHTML = ''; welcome.classList.add('show'); document.getElementById('chat-title').textContent = 'New conversation'; document.getElementById('doc-strip').classList.remove('show'); }
        store.save(); renderSidebar();
      });
      listEl.appendChild(item);
    });
  }

  function groupOf(ts) {
    const d = new Date(ts); d.setHours(0,0,0,0);
    const n = new Date(); n.setHours(0,0,0,0);
    const diff = (n - d) / 864e5;
    if (diff === 0) return 'Today'; if (diff === 1) return 'Yesterday'; if (diff < 7) return 'Previous 7 days'; return 'Older';
  }

  function exportConv(c) {
    const lines = [`# ${c.title}`, '', ...c.messages.map(m => {
      const who = m.role === 'user' ? '**You**' : '**GAIA**';
      const when = m.ts ? ` _(${new Date(m.ts).toLocaleString()})_` : '';
      const lang = m.meta?.language_meta?.language ? ` _[${m.meta.language_meta.language}]_` : '';
      return `${who}${when}${lang}:\n\n${m.content}`;
    })];
    const blob = new Blob([lines.join('\n\n---\n\n')], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = c.title.replace(/[^\w\u0900-\u097F\u0A00-\u0A7F -]/g, '').trim().slice(0, 60) + '.md';
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    chat.toast('Chat exported');
  }

  function renameConv(c) {
    const html = `<header><h2 id="modal-h">Rename chat</h2><button class="icon-btn" data-close aria-label="Close"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6 6 18"/></svg></button></header>
      <div class="dialog__body"><input id="rn-input" class="input" style="width:100%" value="${window.esc(c.title)}" maxlength="80" aria-label="Chat title">
      <div class="dialog__footer"><button class="btn btn--ghost" data-x>Cancel</button><button class="btn btn--primary" data-y>Save</button></div></div>`;
    const m = modal(html);
    const inp = m.el.querySelector('#rn-input'); inp.focus(); inp.select();
    const save = () => { const t = inp.value.trim(); if (t) { c.title = t.slice(0, 80); store.save(); renderSidebar(); if (store.current?.id === c.id) document.getElementById('chat-title').textContent = c.title; chat.toast('Chat renamed'); } m.close(); };
    m.el.querySelector('[data-y]').onclick = save;
    m.el.querySelector('[data-x]').onclick = () => m.close();
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') save(); });
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

  function closeDrawer() {
    sidebar.classList.remove('open');
    scrim.classList.remove('open');
    inputEl?.focus();
  }

  function applyShell() {
    const app = document.querySelector('.app');
    const desktop = innerWidth > 900;
    app.classList.toggle('sidebar-collapsed', desktop && store.get('sideCollapsed'));
    menuBtn.setAttribute('aria-label', desktop ? (store.get('sideCollapsed') ? 'Show sidebar' : 'Hide sidebar') : 'Open conversations menu');
  }

  function init() {
    listEl = document.getElementById('conv-list');
    searchEl = document.getElementById('search');
    sidebar = document.getElementById('sidebar');
    scrim = document.getElementById('scrim');
    menuBtn = document.getElementById('menu-btn');
    inputEl = document.getElementById('input');

    searchEl.addEventListener('input', renderSidebar);

    document.getElementById('new-chat').addEventListener('click', () => { if (window.GAIA_CHAT.streaming) return; chat.newConv(true); inputEl.focus(); closeDrawer(); });

    menuBtn.addEventListener('click', () => {
      if (innerWidth <= 900) { sidebar.classList.add('open'); scrim.classList.add('open'); document.getElementById('new-chat').focus(); }
      else { store.set('sideCollapsed', !store.get('sideCollapsed')); applyShell(); }
    });

    addEventListener('resize', applyShell);
    scrim.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });

    applyShell();
  }

  // Expose
  window.GAIA_SIDEBAR = { renderSidebar, closeDrawer, exportConv, renameConv, confirmModal, modal };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();