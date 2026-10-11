import { API_BASE } from '../config.js';

// All live HTTP calls live here. Chat/SSE/upload contracts are Phase 4/6 work.
export async function health({ signal } = {}) {
  const response = await fetch(`${API_BASE}/api/v1/health`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('Health request failed');
  const data = await response.json();
  if (!data || data.status !== 'ok' || typeof data.llm_ready !== 'boolean') {
    throw new Error('Invalid health response');
  }
  return { status: data.status, llm_ready: data.llm_ready };
}
