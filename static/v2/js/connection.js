import { health } from './api.js';
import { HEALTH_TIMEOUT_MS } from '../config.js';

export function initConnection() {
  const status = document.getElementById('service-status');
  const detail = document.getElementById('service-detail');
  const banner = document.getElementById('offline-banner');
  const title = document.getElementById('offline-title');
  const explanation = document.getElementById('offline-detail');
  const retry = document.getElementById('health-retry');
  let active = null;
  let sequence = 0;

  function cancel() {
    sequence++;
    if (active) { clearTimeout(active.timer); active.controller.abort(); active = null; }
  }
  function unavailable(offline = false, timedOut = false) {
    status.dataset.state = 'unavailable';
    status.textContent = offline ? 'Browser offline' : 'Service unavailable';
    detail.textContent = 'Your draft stays in this tab.';
    banner.hidden = false;
    title.textContent = status.textContent;
    explanation.textContent = timedOut ? 'The health check timed out. Use Retry connection to try again.'
      : 'Your draft stays here. Use Retry connection to check again.';
    retry.disabled = false;
    retry.textContent = 'Retry connection';
  }
  async function check() {
    cancel();
    if (!navigator.onLine) { unavailable(true); return; }
    if (document.hidden) return;
    const request = { controller: new AbortController(), timer: null, timedOut: false };
    const owner = sequence;
    active = request;
    status.dataset.state = 'checking';
    status.textContent = 'Checking service…';
    detail.textContent = 'Checking API reachability only.';
    // Keep an existing offline warning until a successful response proves recovery.
    retry.disabled = true;
    retry.textContent = 'Checking…';
    request.timer = setTimeout(() => { request.timedOut = true; request.controller.abort(); }, HEALTH_TIMEOUT_MS);
    try {
      const result = await health({ signal: request.controller.signal });
      if (owner !== sequence) return;
      status.dataset.state = 'available';
      status.textContent = 'API reachable';
      detail.textContent = result.llm_ready ? 'Provider configured · reply generation not tested.'
        : 'Provider not configured · general replies unavailable.';
      banner.hidden = true;
      retry.textContent = 'Check service';
    } catch {
      if (owner === sequence) unavailable(!navigator.onLine, request.timedOut);
    } finally {
      clearTimeout(request.timer);
      if (owner === sequence) { active = null; retry.disabled = false; }
    }
  }
  retry.addEventListener('click', check);
  window.addEventListener('offline', () => { cancel(); unavailable(true); });
  window.addEventListener('online', check);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      const wasChecking = Boolean(active);
      cancel();
      if (wasChecking) {
        status.dataset.state = 'paused';
        status.textContent = 'Service check paused';
        detail.textContent = 'The check resumes when this tab is visible.';
        retry.disabled = false;
        retry.textContent = 'Check service';
      }
    } else check();
  });
  window.addEventListener('pagehide', cancel);
  window.addEventListener('pageshow', event => { if (event.persisted) check(); });
  check();
}
