// V2-only browser history. This is deliberately separate from legacy gaia.store.v1.
export const HISTORY_KEY = 'gaia.history.v2';
const VERSION = 1;
const MAX_CONVERSATIONS = 50;
const ROLES = new Set(['user', 'assistant']);

const emptyState = () => ({ version: VERSION, currentId: null, conversations: [] });
const finite = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;

function copyLanguageMeta(meta) {
  if (!meta || typeof meta !== 'object') return undefined;
  const allowed = ['language', 'primary_language', 'language_name', 'secondary_languages',
    'code_switched', 'mixed_script', 'scripts', 'script', 'confidence', 'detection_reason'];
  const copy = {};
  allowed.forEach(key => {
    const value = meta[key];
    if (Array.isArray(value)) copy[key] = value.filter(item => typeof item === 'string').slice(0, 20);
    else if (value && typeof value === 'object') copy[key] = Object.fromEntries(
      Object.entries(value).filter(([, item]) => Number.isFinite(Number(item))).slice(0, 20),
    );
    else if (typeof value === 'string' || typeof value === 'boolean' || typeof value === 'number') copy[key] = value;
  });
  return copy;
}

function copyDone(done) {
  if (!done || typeof done !== 'object') return undefined;
  const copy = {};
  if (typeof done.model === 'string') copy.model = done.model;
  if (Number.isFinite(Number(done.latency_ms))) copy.latency_ms = Number(done.latency_ms);
  if (Array.isArray(done.sources)) copy.sources = done.sources.slice(0, 20).map(source => {
    if (!source || typeof source !== 'object') return null;
    return Object.fromEntries(Object.entries(source).filter(([, value]) =>
      typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'));
  }).filter(Boolean);
  return copy;
}

export function serializeMessage(message) {
  const meta = message?.meta || {};
  const cleanMeta = {};
  const languageMeta = copyLanguageMeta(meta.language_meta);
  if (languageMeta) cleanMeta.language_meta = languageMeta;
  ['response_lang', 'route', 'reason', 'intent', 'technical_error'].forEach(key => {
    if (typeof meta[key] === 'string') cleanMeta[key] = meta[key];
  });
  ['confidence', 'degraded'].forEach(key => {
    if (typeof meta[key] === 'number' || typeof meta[key] === 'boolean') cleanMeta[key] = meta[key];
  });
  if (meta.error === true) cleanMeta.error = true;
  const done = copyDone(meta.done);
  if (done) cleanMeta.done = done;
  return {
    id: typeof message?.id === 'string' ? message.id : `message-${Date.now()}`,
    role: ROLES.has(message?.role) ? message.role : 'assistant',
    text: typeof message?.text === 'string' ? message.text : '',
    timestamp: finite(message?.timestamp, Date.now()),
    meta: cleanMeta,
  };
}

function normalizeMessage(raw) {
  if (!raw || typeof raw !== 'object' || !ROLES.has(raw.role)) return null;
  return serializeMessage({
    id: typeof raw.id === 'string' ? raw.id : undefined,
    role: raw.role,
    text: raw.text,
    timestamp: raw.timestamp,
    meta: raw.meta,
  });
}

function normalizeConversation(raw) {
  if (!raw || typeof raw !== 'object' || typeof raw.id !== 'string' || !raw.id) return null;
  const now = Date.now();
  const messages = Array.isArray(raw.messages) ? raw.messages.map(normalizeMessage).filter(Boolean) : [];
  return {
    id: raw.id,
    serverId: typeof raw.serverId === 'string' ? raw.serverId : null,
    title: typeof raw.title === 'string' && raw.title.trim() ? raw.title.trim().slice(0, 80) : 'New conversation',
    createdAt: finite(raw.createdAt, now),
    updatedAt: finite(raw.updatedAt, now),
    messages,
  };
}

function normalizeState(raw) {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.conversations)) return null;
  const conversations = raw.conversations.map(normalizeConversation).filter(Boolean)
    .sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_CONVERSATIONS);
  const currentId = typeof raw.currentId === 'string' && conversations.some(item => item.id === raw.currentId)
    ? raw.currentId : null;
  return { version: VERSION, currentId, conversations };
}

export function loadHistory() {
  let raw;
  try {
    raw = localStorage.getItem(HISTORY_KEY);
  } catch {
    return { state: emptyState(), status: 'unavailable' };
  }
  if (!raw) return { state: emptyState(), status: 'empty' };
  try {
    const state = normalizeState(JSON.parse(raw));
    return state ? { state, status: 'ok' } : { state: emptyState(), status: 'malformed' };
  } catch {
    return { state: emptyState(), status: 'malformed' };
  }
}

export function saveHistory(state) {
  try {
    const value = {
      version: VERSION,
      currentId: state.currentId || null,
      conversations: state.conversations.slice().sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_CONVERSATIONS),
    };
    localStorage.setItem(HISTORY_KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function newConversation(now = Date.now()) {
  const random = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
  return { id: `v2-${now}-${random}`, serverId: null, title: 'New conversation', createdAt: now, updatedAt: now, messages: [] };
}

export function titleFromMessage(text) {
  const title = String(text || '').trim().replace(/\s+/g, ' ');
  return title.slice(0, 80) || 'New conversation';
}
