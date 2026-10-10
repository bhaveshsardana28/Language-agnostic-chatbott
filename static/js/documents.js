/**
 * GAIA Documents — upload, list, clear, document strip UI.
 */
(function () {
  'use strict';

  const api = window.GAIA_API;
  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;

  let strip, fileInput, uploading = false;

  function docChip(name, status, cls) {
    const d = document.createElement('span');
    d.className = 'chip ' + cls;
    d.innerHTML = `<svg class="chip__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>${window.esc(name)} <span class="chip__status">${window.esc(status)}</span>`;
    strip.appendChild(d);
    return d;
  }

  async function refreshDocs() {
    const c = store.current; strip.innerHTML = '';
    if (!c) { strip.classList.remove('show'); return; }
    try {
      const r = await api.listDocuments(c.id);
      if (!r.documents.length) { strip.classList.remove('show'); return; }
      strip.classList.add('show');
      r.documents.forEach(d => docChip(d.document, `${d.chunks} chunks · Ready`, 'ok'));
      const n = r.documents.length;
      const lbl = document.createElement('span');
      lbl.className = 'chip__status';
      lbl.style.cssText = 'color:var(--text-subtle);font-size:var(--fs-xs);align-self:center';
      lbl.textContent = `${n} document${n > 1 ? 's' : ''} — ask questions about them`;
      strip.appendChild(lbl);
      const cl = document.createElement('button');
      cl.id = 'clear-docs'; cl.className = 'doc-strip__clear'; cl.textContent = 'Clear documents';
      cl.addEventListener('click', async () => { await api.clearDocuments(c.id).catch(() => {}); refreshDocs(); });
      strip.appendChild(cl);
    } catch { strip.classList.remove('show'); }
  }

  function init() {
    strip = document.getElementById('doc-strip');
    fileInput = document.getElementById('file-input');

    document.getElementById('attach-btn').addEventListener('click', () => document.getElementById('docs-btn').click());
    document.getElementById('docs-btn').addEventListener('click', () => {
      const c = store.current; if (!c) chat.newConv(true);
      if (!store.current || uploading) return; fileInput.click();
    });

    fileInput.addEventListener('change', async e => {
      const f = e.target.files[0]; e.target.value = ''; if (!f) return;
      let c = store.current; if (!c) c = chat.newConv(true);
      uploading = true;
      const chip = docChip(f.name, 'Processing…', '');
      try {
        const r = await api.uploadDocument(c.id, f);
        chip.querySelector('.chip__status').textContent = `Ready — ${r.chunks} chunks`; chip.classList.add('ok');
        chat.toast('Document ready');
      } catch (err) { chip.querySelector('.chip__status').textContent = 'Failed — try again'; chip.classList.add('err'); }
      uploading = false; refreshDocs();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();