/**
 * GAIA API Client — single entry point for all backend calls.
 * Supports ?mock=1 URL flag or localStorage.mockMode for offline development.
 */
(function () {
  'use strict';

  const MOCK_MODE = new URLSearchParams(window.location.search).has('mock') ||
                    localStorage.getItem('gaia.mockMode') === '1';

  const API_BASE = '';

  function mockDelay(ms = 300) {
    return new Promise(r => setTimeout(r, ms));
  }

  function mockSSE(frames, signal) {
    return new ReadableStream({
      async start(controller) {
        for (const frame of frames) {
          if (signal?.aborted) return;
          await mockDelay(50 + Math.random() * 100);
          controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(frame)}\n\n`));
        }
        controller.close();
      }
    });
  }

  const mockFrames = {
    general: [
      { type: 'meta', conversation_id: 'mock-1', language_meta: { language: 'en', language_name: 'English', script: 'Latn', confidence: 0.99, secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latn: 1 }, detection_reason: 'mock' }, route: 'general', reason: 'mock', response_lang: 'en' },
      { type: 'delta', text: 'This is a ' },
      { type: 'delta', text: 'mocked ' },
      { type: 'delta', text: 'streaming ' },
      { type: 'delta', text: 'response. ' },
      { type: 'delta', text: 'It works offline! 🎉' },
      { type: 'done', latency_ms: 123, model: 'mock:offline', sources: [] }
    ],
    translate: [
      { type: 'meta', conversation_id: 'mock-1', language_meta: { language: 'es', language_name: 'Spanish', script: 'Latn', confidence: 0.95, secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latn: 1 }, detection_reason: 'mock' }, route: 'translate', reason: 'translation requested', response_lang: 'es' },
      { type: 'delta', text: 'Esta es una respuesta de traducción simulada.' },
      { type: 'done', latency_ms: 98, model: 'mt:en', sources: [] }
    ],
    campus_kb: [
      { type: 'meta', conversation_id: 'mock-1', language_meta: { language: 'en', language_name: 'English', script: 'Latn', confidence: 0.99, secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latn: 1 }, detection_reason: 'mock' }, route: 'campus_kb', reason: 'matched intent', response_lang: 'en' },
      { type: 'delta', text: 'Campus KB answer: The exam schedule is available on the student portal.', intent: 'exam_schedule', confidence: 0.92 },
      { type: 'done', latency_ms: 45, model: 'tfidf+logreg (pivot)', sources: [] }
    ],
    error: [
      { type: 'meta', conversation_id: 'mock-1', language_meta: { language: 'en', language_name: 'English', script: 'Latn', confidence: 0.99, secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latn: 1 }, detection_reason: 'mock' }, route: 'general', reason: 'mock error', response_lang: 'en' },
      { type: 'error', message: 'This is a mocked error for testing.' }
    ]
  };

  async function fetchJson(url, options = {}) {
    if (MOCK_MODE) { throw new Error('MOCK_MODE: use mock functions'); }
    const res = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
    if (!res.ok) { const j = await res.json().catch(() => ({})); throw new Error(j.error || `HTTP ${res.status}`); }
    return res.json();
  }

  const api = {
    isMock: () => MOCK_MODE,

    health: async () => {
      if (MOCK_MODE) { await mockDelay(); return { status: 'ok', llm_provider: 'mock', llm_model: 'offline', llm_ready: true, llm_note: 'Mock mode active', languages: 7 }; }
      return fetchJson('/api/v1/health');
    },

    newConversation: async () => {
      if (MOCK_MODE) { await mockDelay(); return { conversation_id: 'mock-' + Date.now() }; }
      return fetchJson('/api/v1/conversations', { method: 'POST' });
    },

    deleteConversation: async (id) => {
      if (MOCK_MODE) { await mockDelay(); return { deleted: true, documents_deleted: 0 }; }
      return fetchJson(`/api/v1/chat/${id}`, { method: 'DELETE' });
    },

    listDocuments: async (cid) => {
      if (MOCK_MODE) { await mockDelay(); return { conversation_id: cid, documents: [] }; }
      return fetchJson(`/api/v1/documents/${cid}`);
    },

    clearDocuments: async (cid) => {
      if (MOCK_MODE) { await mockDelay(); return { deleted: true }; }
      return fetchJson(`/api/v1/documents/${cid}`, { method: 'DELETE' });
    },

    uploadDocument: async (cid, file) => {
      if (MOCK_MODE) { await mockDelay(800); return { conversation_id: cid, chunks: Math.floor(Math.random() * 20) + 5, document: file.name }; }
      const fd = new FormData(); fd.append('file', file); fd.append('conversation_id', cid);
      const res = await fetch('/api/v1/documents', { method: 'POST', body: fd });
      const j = await res.json(); if (!res.ok) throw new Error(j.error || res.status); return j;
    },

    /**
     * SSE chat stream — the ONLY place that talks to /api/v1/chat
     * handlers: { meta, delta, error, done }
     */
    chat: async (message, cid, handlers, signal) => {
      if (MOCK_MODE) {
        // Pick mock based on message content
        let frames = mockFrames.general;
        const lower = message.toLowerCase();
        if (lower.includes('translate') || lower.includes('traduce') || lower.includes('traducir')) frames = mockFrames.translate;
        else if (lower.includes('exam') || lower.includes('schedule') || lower.includes('campus')) frames = mockFrames.campus_kb;
        else if (lower.includes('error') || lower.includes('fail')) frames = mockFrames.error;

        const stream = mockSSE(frames, signal);
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let buf = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let i;
          while ((i = buf.indexOf('\n\n')) >= 0) {
            const line = buf.slice(0, i).trim().replace(/^data:\s*/, '');
            buf = buf.slice(i + 2);
            if (!line) continue;
            let ev; try { ev = JSON.parse(line); } catch { continue; }
            if (ev.type === 'meta') handlers.meta?.(ev);
            else if (ev.type === 'delta') handlers.delta?.(ev);
            else if (ev.type === 'error') handlers.error?.(ev);
            else if (ev.type === 'done') handlers.done?.(ev);
          }
        }
        return;
      }

      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, conversation_id: cid }),
        signal
      });

      if (!res.ok) { const j = await res.json().catch(() => ({})); throw new Error(j.error || `HTTP ${res.status}`); }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).trim().replace(/^data:\s*/, '');
          buf = buf.slice(i + 2);
          if (!line) continue;
          let ev; try { ev = JSON.parse(line); } catch { continue; }
          if (ev.type === 'meta') handlers.meta?.(ev);
          else if (ev.type === 'delta') handlers.delta?.(ev);
          else if (ev.type === 'error') handlers.error?.(ev);
          else if (ev.type === 'done') handlers.done?.(ev);
        }
      }
    }
  };

  // Expose globally
  window.GAIA_API = api;
})();