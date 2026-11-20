const LANGUAGE_NAMES = Object.freeze({
  en: 'English', hi: 'Hindi', pa: 'Punjabi', es: 'Spanish', fr: 'French',
  de: 'German', it: 'Italian', ja: 'Japanese', ar: 'Arabic',
});

function languageLabel(code, meta = {}) {
  if (!code) return '—';
  const name = meta.language_name || LANGUAGE_NAMES[code] || code;
  return `${name} · ${code}`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value == null || value === '' ? '—' : String(value);
}

function setState(id, value) {
  setText(id, value);
}

function setStep(name, state) {
  const step = document.querySelector(`#intelligence-steps [data-step="${name}"]`);
  if (step) step.dataset.state = state;
}

function safeHttpUrl(value) {
  try {
    const url = new URL(String(value));
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function renderSources(sources = []) {
  const container = document.getElementById('intelligence-sources');
  const empty = document.getElementById('intelligence-sources-empty') || document.createElement('p');
  empty.id = 'intelligence-sources-empty';
  empty.className = 'intelligence-empty';
  empty.textContent = 'Sources appear here when a response cites them.';
  const count = document.getElementById('intelligence-source-count');
  if (!container) return;
  container.replaceChildren();
  const valid = sources.filter(source => source && typeof source === 'object' &&
    (source.document || source.url || source.note));
  if (count) count.textContent = String(valid.length);
  if (!valid.length) {
    if (empty) {
      empty.hidden = false;
      container.append(empty);
    }
    return;
  }
  if (empty) empty.hidden = true;
  valid.forEach((source, index) => {
    const item = document.createElement('article');
    item.className = 'intelligence-source';
    const number = document.createElement('span');
    number.className = 'intelligence-source-number';
    number.textContent = String(index + 1).padStart(2, '0');
    const content = document.createElement('div');
    content.className = 'intelligence-source-content';
    const title = document.createElement('strong');
    const detail = document.createElement('span');
    if (typeof source.url === 'string' && safeHttpUrl(source.url)) {
      const link = document.createElement('a');
      link.href = safeHttpUrl(source.url);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = source.title || source.url;
      title.append(link);
      detail.textContent = 'Web source';
    } else if (typeof source.document === 'string') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'intelligence-source-button';
      button.textContent = source.document;
      button.addEventListener('click', () => document.dispatchEvent(new CustomEvent('v2sourceopen', {
        detail: { document: source.document, document_id: source.document_id, page: source.page,
          chunk: source.chunk, excerpt: source.excerpt },
      })));
      title.append(button);
      const chunk = Number.isFinite(source.chunk) ? `Chunk ${Number(source.chunk) + 1}` : 'Document source';
      const page = Number.isFinite(source.page) ? ` · page ${source.page}` : '';
      const score = Number.isFinite(source.score) ? ` · match ${Number(source.score).toFixed(2)}` : '';
      detail.textContent = `${chunk}${page}${score}`;
    } else {
      title.textContent = source.note || 'Source note';
      detail.textContent = 'Service note';
    }
    content.append(title, detail);
    item.append(number, content);
    container.append(item);
  });
}

function resetPanel() {
  setState('intelligence-query-state', 'Waiting');
  setState('intelligence-retrieval-state', 'Idle');
  setState('intelligence-generation-state', 'No active response');
  setText('intelligence-language', '—');
  setText('intelligence-response-language', '—');
  setText('intelligence-route', '—');
  setText('intelligence-model', '—');
  setText('intelligence-latency', '—');
  setText('intelligence-retrieval-note', 'Retrieval metadata will appear when the backend reports it.');
  ['language', 'route', 'sources'].forEach(step => setStep(step, 'idle'));
  renderSources([]);
}

export function initIntelligence() {
  const panel = document.getElementById('intelligence-panel');
  const toggle = document.getElementById('intelligence-toggle');
  const close = document.getElementById('intelligence-close');
  if (!panel || !toggle || !close) return;
  const desktop = matchMedia('(min-width: 80rem)');
  let open = false;

  function sync() {
    panel.inert = !open;
    document.documentElement.dataset.intelligence = open ? "open" : "closed";
    panel.dataset.open = String(open);
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', `${open ? 'Hide' : 'Show'} intelligence panel`);
    toggle.title = `${open ? 'Hide' : 'Show'} intelligence panel`;
    close.setAttribute('aria-label', 'Hide intelligence panel');
  }
  toggle.addEventListener('click', () => { open = !open; sync(); if (open && !desktop.matches) close.focus(); });
  close.addEventListener('click', () => { open = false; sync(); toggle.focus(); });
  const dismissOutside = event => {
    if (open && !desktop.matches && !panel.contains(event.target) && !toggle.contains(event.target)) {
      open = false;
      sync();
    }
  };
  document.addEventListener('pointerdown', dismissOutside);
  document.addEventListener('focusin', dismissOutside);
  desktop.addEventListener('change', () => { open = false; sync(); });
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape' && open) { open = false; sync(); toggle.focus(); }
  });
  document.addEventListener('v2conversationchange', resetPanel);
  document.addEventListener('v2intelligence', event => {
    const detail = event.detail || {};
    if (detail.type === 'reset') { resetPanel(); return; }
    if (detail.type === 'start') {
      setState('intelligence-query-state', 'Analyzing');
      setState('intelligence-retrieval-state', 'Awaiting metadata');
      setState('intelligence-generation-state', 'Preparing');
      setText('intelligence-retrieval-note', 'The service will report the route and any sources it used.');
      ['language', 'route', 'sources'].forEach(step => setStep(step, 'idle'));
      renderSources([]);
      return;
    }
    if (detail.type === 'meta') {
      const frame = detail.frame || {};
      const meta = frame.language_meta || {};
      setState('intelligence-query-state', 'Metadata received');
      setText('intelligence-language', languageLabel(meta.language, meta));
      setText('intelligence-response-language', languageLabel(frame.response_lang));
      setText('intelligence-route', frame.route ? `${frame.route}${frame.reason ? ` · ${frame.reason}` : ''}` : '—');
      setState('intelligence-retrieval-state', frame.route === 'document' ? 'Document route' : 'Route selected');
      setText('intelligence-retrieval-note', frame.route === 'document'
        ? 'Document retrieval was selected by the service. Sources will be listed when generation completes.'
        : 'No retrieval progress event was returned by the service.');
      setState('intelligence-generation-state', 'Streaming');
      setStep('language', 'complete'); setStep('route', 'complete');
      return;
    }
    if (detail.type === 'done') {
      const frame = detail.frame || {};
      const sources = Array.isArray(frame.sources) ? frame.sources : [];
      if (document.getElementById('intelligence-generation-state')?.textContent === 'Reply interrupted') return;
      setState('intelligence-query-state', 'Complete');
      setState('intelligence-retrieval-state', sources.length ? 'Sources returned' : 'No sources returned');
      setState('intelligence-generation-state', 'Complete');
      setText('intelligence-model', frame.model || '—');
      setText('intelligence-latency', Number.isFinite(frame.latency_ms) ? `${frame.latency_ms} ms` : '—');
      setText('intelligence-retrieval-note', sources.length
        ? `${sources.length} source${sources.length === 1 ? '' : 's'} returned by the service.`
        : 'The service returned no sources for this response.');
      setStep('language', 'complete'); setStep('route', 'complete'); setStep('sources', sources.length ? 'complete' : 'empty');
      renderSources(sources);
      return;
    }
    if (detail.type === 'error') {
      setState('intelligence-query-state', 'Needs attention');
      setState('intelligence-generation-state', 'Reply interrupted');
      setText('intelligence-retrieval-note', 'The response ended with an error or interruption.');
    }
  });
  resetPanel();
  sync();
}
