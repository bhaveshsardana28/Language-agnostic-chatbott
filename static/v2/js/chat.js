import { API_BASE } from '../config.js';
import { createConversation, deleteConversation as deleteServerConversation } from './api.js';
import { mockStream } from './mock.js';
import { renderMarkdown, plainText } from './markdown.js';
import { closeNavigation } from './shell.js';
import { toast, openOverlay, closeOverlay } from './ui.js';
import { loadHistory, newConversation, saveHistory, serializeMessage, titleFromMessage } from './history.js';

const MAX_CHARS = 4000;
const STREAM_TIMEOUT = 30000;
const mock = new URLSearchParams(location.search).get('mock') === '1';
const LANGUAGE_NAMES = Object.freeze({
  en: { native: 'English', english: 'English', script: 'Latin' },
  hi: { native: 'हिन्दी', english: 'Hindi', script: 'Devanagari' },
  pa: { native: 'ਪੰਜਾਬੀ', english: 'Punjabi', script: 'Gurmukhi' },
  es: { native: 'Español', english: 'Spanish', script: 'Latin' },
  fr: { native: 'Français', english: 'French', script: 'Latin' },
  de: { native: 'Deutsch', english: 'German', script: 'Latin' },
  it: { native: 'Italiano', english: 'Italian', script: 'Latin' },
  ja: { native: '日本語', english: 'Japanese', script: 'Japanese' },
  ar: { native: 'العربية', english: 'Arabic', script: 'Arabic' },
});

function localTimestamp(timestamp = Date.now()) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(timestamp));
}
function safeError(error) {
  if (error?.name === 'AbortError') return 'The request was stopped before it finished.';
  if (error?.status === 400) return 'Write a message before sending.';
  if (error?.status === 413) return 'That message is too long. Keep it under 4,000 characters.';
  return 'I could not complete that reply. Check the connection and try again.';
}
function languageInfo(code, meta = {}) {
  const known = LANGUAGE_NAMES[code] || { native: code || 'Unknown', english: code || 'Unknown', script: 'Unknown' };
  return {
    code,
    native: known.native,
    english: code === meta.language && meta.language_name ? meta.language_name : known.english,
    script: meta.script || known.script,
  };
}
function languageLabel(code, meta = {}) {
  const info = languageInfo(code, meta);
  return info.native === info.english ? info.english : `${info.native} · ${info.english}`;
}
function parseFrame(block) {
  const line = block.split('\n').find(item => item.startsWith('data:'));
  if (!line) return null;
  try { return JSON.parse(line.slice(5).trim()); } catch { return { type: 'error', message: 'The server sent an unreadable event.' }; }
}
async function readSSE(response, onFrame, signal) {
  if (!response.ok) { const error = new Error('request failed'); error.status = response.status; throw error; }
  if (!response.body) throw new Error('stream unavailable');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', sawDone = false;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) { const frame = parseFrame(block); if (frame) { onFrame(frame); if (frame.type === 'done') sawDone = true; } }
    if (done) break;
    if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
  }
  if (buffer.trim()) { const frame = parseFrame(buffer); if (frame) { onFrame(frame); if (frame.type === 'done') sawDone = true; } }
  if (!sawDone) throw new Error('The reply ended before completion.');
}

async function streamLive(message, conversationId, { signal, onFrame }) {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' }, credentials: 'include',
    body: JSON.stringify({ message, conversation_id: conversationId }), signal,
  });
  await readSSE(response, onFrame, signal);
}

export function initChat() {
  const form = document.getElementById('composer-form');
  const input = document.getElementById('message-input');
  const send = document.getElementById('send-button');
  const main = document.getElementById('main-content');
  const welcome = document.getElementById('welcome');
  const chatView = document.getElementById('conversation-view');
  const log = document.getElementById('message-log');
  const counter = document.getElementById('message-count');
  const composerNote = document.getElementById('shell-scope');
  const historyList = document.getElementById('history-list');
  const historyEmpty = document.getElementById('history-empty');
  const historySearch = document.getElementById('history-search');
  const historyNoResults = document.getElementById('history-no-results');
  const renameDialog = document.getElementById('rename-dialog');
  const renameForm = document.getElementById('rename-form');
  const renameInput = document.getElementById('rename-input');
  const renameError = document.getElementById('rename-error');
  const deleteDialog = document.getElementById('delete-dialog');
  const deleteForm = document.getElementById('delete-form');
  const deleteCopy = document.getElementById('delete-copy');
  const navigationDrawer = document.getElementById('navigation-drawer');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const desktop = matchMedia('(min-width: 64rem)');
  let conversationId = null;
  let active = null;
  let assistant = null;
  let requestNumber = 0;
  let historyResult = loadHistory();
  let historyState = historyResult.state;
  let currentRecord = null;
  let storageWarningShown = false;
  let pendingRecord = null;
  let documentProcessing = false;
  const messages = [];

  function persistHistory() {
    if (saveHistory(historyState)) return true;
    if (!storageWarningShown) {
      storageWarningShown = true;
      toast('Browser history storage is unavailable. This chat will remain for this tab.');
    }
    return false;
  }
  function recordFor(id = historyState.currentId) {
    return historyState.conversations.find(item => item.id === id) || null;
  }
  function currentConversation() {
    return currentRecord || recordFor();
  }
  function setHeading(title) {
    document.getElementById('conversation-heading').textContent = title || 'New conversation';
  }
  function formatHistoryDate(timestamp) {
    const date = new Date(timestamp);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) return localTimestamp(timestamp);
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date);
  }
  function historyMatches(record, query) {
    if (!query) return true;
    const haystack = [record.title, ...record.messages.map(message => message.text)].join('\n').toLocaleLowerCase();
    return haystack.includes(query.toLocaleLowerCase());
  }
  function matchingSnippet(record, query) {
    if (!query) return null;
    const lowerQuery = query.toLocaleLowerCase();
    const source = record.messages.find(message => message.text.toLocaleLowerCase().includes(lowerQuery));
    if (!source) return null;
    const lowerText = source.text.toLocaleLowerCase();
    const index = lowerText.indexOf(lowerQuery);
    const start = Math.max(0, index - 28);
    const end = Math.min(source.text.length, index + query.length + 52);
    return `${source.role === 'user' ? 'You' : 'GAIA'}: ${start ? '…' : ''}${source.text.slice(start, end)}${end < source.text.length ? '…' : ''}`;
  }
  function appendHighlighted(parent, text, query) {
    if (!query) { parent.textContent = text; return; }
    const lowerText = text.toLocaleLowerCase();
    const lowerQuery = query.toLocaleLowerCase();
    let cursor = 0;
    let index = lowerText.indexOf(lowerQuery);
    while (index !== -1) {
      parent.append(document.createTextNode(text.slice(cursor, index)));
      const mark = document.createElement('mark');
      mark.textContent = text.slice(index, index + query.length);
      parent.append(mark);
      cursor = index + query.length;
      index = lowerText.indexOf(lowerQuery, cursor);
    }
    parent.append(document.createTextNode(text.slice(cursor)));
  }
  function historyGroup(timestamp) {
    const date = new Date(timestamp);
    const today = new Date();
    const start = value => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
    const days = Math.floor((start(today) - start(date)) / 86400000);
    if (days <= 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days <= 7) return 'Previous 7 days';
    return 'Older';
  }
  function renderHistory() {
    const query = historySearch.value.trim();
    const allConversations = historyState.conversations.slice().sort((a, b) => b.updatedAt - a.updatedAt);
    const conversations = allConversations.filter(record => historyMatches(record, query));
    historyEmpty.hidden = allConversations.length > 0;
    historyNoResults.hidden = !query || conversations.length > 0;
    historyList.replaceChildren();
    const groups = [];
    conversations.forEach(record => {
      const label = historyGroup(record.updatedAt);
      let group = groups.find(item => item.label === label);
      if (!group) { group = { label, records: [] }; groups.push(group); }
      group.records.push(record);
    });
    groups.forEach(groupData => {
      const group = document.createElement('section');
      group.className = 'history-group';
      const heading = document.createElement('h3');
      heading.className = 'history-group-title';
      heading.textContent = groupData.label;
      group.append(heading);
      groupData.records.forEach(record => {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.setAttribute('role', 'listitem');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'history-row sidebar-action';
      button.dataset.historyId = record.id;
      button.setAttribute('aria-current', String(record.id === historyState.currentId));
      const title = document.createElement('strong');
      appendHighlighted(title, record.title, query);
      const detail = document.createElement('span');
      detail.className = query && matchingSnippet(record, query) ? 'history-snippet' : 'field-note';
      const snippet = matchingSnippet(record, query);
      if (snippet) appendHighlighted(detail, snippet, query);
      else detail.textContent = `${record.messages.length} ${record.messages.length === 1 ? 'message' : 'messages'} · ${formatHistoryDate(record.updatedAt)}`;
      button.append(title, detail);
      const actions = document.createElement('div');
      actions.className = 'history-actions';
      [['rename', 'Rename conversation'], ['export', 'Export conversation'], ['delete', 'Delete conversation']].forEach(([action, label]) => {
        const control = document.createElement('button');
        control.type = 'button';
        control.className = 'icon-button icon-button--quiet';
        control.dataset.historyAction = action;
        control.dataset.recordId = record.id;
        control.setAttribute('aria-label', label);
        control.title = label;
        actions.append(control);
      });
      item.append(button, actions);
      group.append(item);
      });
      historyList.append(group);
    });
  }
  function ensureConversation() {
    if (currentConversation()) return currentConversation();
    const record = newConversation();
    historyState.conversations.push(record);
    historyState.currentId = record.id;
    currentRecord = record;
    persistHistory();
    renderHistory();
    return record;
  }
  async function ensureServerConversationId() {
    const record = ensureConversation();
    if (record.serverId) {
      conversationId = record.serverId;
      return record.serverId;
    }
    record.serverId = mock ? 'mock-document-conversation' : await createConversation();
    conversationId = record.serverId;
    record.updatedAt = Date.now();
    persistHistory();
    renderHistory();
    return record.serverId;
  }
  function persistMessage(message) {
    const record = currentConversation();
    if (!record || !message) return;
    const stored = serializeMessage(message);
    const index = record.messages.findIndex(item => item.id === stored.id);
    if (index === -1) record.messages.push(stored); else record.messages[index] = stored;
    record.updatedAt = Date.now();
    persistHistory();
    renderHistory();
  }
  function attachCodeCopy(article) {
    article.querySelectorAll('.code-copy').forEach(button => {
      if (button.dataset.bound === 'true') return;
      button.dataset.bound = 'true';
      button.addEventListener('click', async () => {
        const code = button.closest('.code-block').querySelector('code').innerText;
        try { await navigator.clipboard.writeText(code); toast('Code block copied.'); }
        catch { toast('Clipboard unavailable. Select the code and copy it manually.'); }
      });
    });
  }

  if (mock) {
    document.documentElement.dataset.mock = 'true';
    const banner = document.getElementById('mock-banner');
    banner.hidden = false;
    banner.textContent = 'Simulation mode · delayed fixture stream · no backend request';
    composerNote.textContent = 'Mock chat only · no backend request or server memory.';
    document.getElementById('conversation-mode').textContent = 'Simulated stream';
  }
  function scrollLatest() { main.scrollTo({ top: main.scrollHeight, behavior: document.documentElement.dataset.motion === 'reduced' ? 'auto' : 'smooth' }); }
  function updateInput() {
    const length = input.value.length;
    counter.textContent = `${length.toLocaleString()} / ${MAX_CHARS.toLocaleString()}`;
    counter.dataset.state = length > MAX_CHARS ? 'over' : length > 3600 ? 'warn' : '';
    send.disabled = active ? false : documentProcessing || !input.value.trim() || length > MAX_CHARS;
    input.setAttribute('aria-invalid', String(length > MAX_CHARS));
  }
  function appendLanguageChip(head, code, meta, { detected = false } = {}) {
    if (!code) return;
    const info = languageInfo(code, meta);
    const chip = document.createElement('span');
    chip.className = 'chip language-chip';
    chip.dataset.chatMeta = 'language';
    chip.dataset.language = code;
    chip.dataset.script = info.script;
    chip.textContent = languageLabel(code, meta);
    chip.setAttribute('aria-label', `${info.english}, ${info.script} script${detected ? ' detected from your message' : ' reply language'}`);
    if (detected && meta.confidence != null && meta.confidence < 0.5) {
      chip.classList.add('language-chip--low');
      chip.title = `Detection confidence ${(meta.confidence * 100).toFixed(0)}% — verify language`;
    } else {
      chip.title = `${info.english} · ${info.script} script`;
    }
    head.append(chip);
    const script = document.createElement('span');
    script.className = 'chip chip--quiet script-chip';
    script.dataset.chatMeta = 'script';
    script.textContent = `${info.script} script`;
    script.setAttribute('aria-label', `${info.script} script`);
    head.append(script);
  }
  function applyMessageLanguage(message) {
    if (!message?.article) return;
    const head = message.article.querySelector('.chat-message-head');
    head.querySelectorAll('[data-chat-meta]').forEach(item => item.remove());
    const meta = message.meta || {};
    const detected = meta.language_meta || {};
    const code = message.role === 'user' ? detected.language : (meta.response_lang || detected.language);
    if (message.role === 'user') appendLanguageChip(head, code, detected, { detected: true });
    else appendLanguageChip(head, code, meta.response_lang === detected.language ? detected : {}, { detected: false });
    if (code) {
      const info = languageInfo(code, message.role === 'user' ? detected : (meta.response_lang === detected.language ? detected : {}));
      message.article.dataset.script = info.script;
      message.article.lang = code;
      message.body.dir = 'auto';
      message.body.lang = code;
    }
  }
  function applyAssistantRoute(message) {
    if (message.role !== 'assistant') return;
    const head = message.article.querySelector('.chat-message-head');
    head.querySelectorAll('[data-chat-meta="route"]').forEach(item => item.remove());
    if (!message.meta?.route) return;
    const route = document.createElement('span');
    route.className = 'chat-route';
    route.dataset.chatMeta = 'route';
    route.textContent = message.meta.route;
    route.title = message.meta.reason || 'Response route';
    head.insertBefore(route, head.querySelector('time'));
  }
  function safeHttpUrl(value) {
    try {
      const url = new URL(String(value));
      return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  }
  function renderSources(message) {
    if (message.role !== 'assistant' || message.article.querySelector('.chat-sources')) return;
    const sources = message.meta?.done?.sources;
    if (!Array.isArray(sources) || !sources.length) return;
    const section = document.createElement('section');
    section.className = 'chat-sources';
    section.setAttribute('aria-label', 'Sources');
    const heading = document.createElement('strong');
    heading.className = 'chat-sources-title';
    heading.textContent = 'Sources';
    section.append(heading);
    sources.forEach((source, index) => {
      if (!source || typeof source !== 'object') return;
      const item = document.createElement('div');
      item.className = 'chat-source';
      const number = document.createElement('span');
      number.className = 'chat-source-number';
      number.textContent = `${index + 1}.`;
      item.append(number);
      if (typeof source.url === 'string') {
        const url = safeHttpUrl(source.url);
        if (url) {
          const link = document.createElement('a');
          link.href = url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = source.title || url;
          item.append(link);
        } else {
          const text = document.createElement('span');
          text.textContent = source.title || 'Unverified web source';
          item.append(text);
        }
      } else if (typeof source.document === 'string') {
        const text = document.createElement('span');
        const page = Number.isFinite(Number(source.page)) ? ` · page ${Number(source.page)}` : '';
        text.textContent = `${source.document} · chunk ${Number.isFinite(Number(source.chunk)) ? Number(source.chunk) + 1 : '—'}${page}`;
        item.append(text);
        if (Number.isFinite(Number(source.score))) {
          const score = document.createElement('small');
          score.textContent = `match ${Number(source.score).toFixed(2)}`;
          item.append(score);
        }
      } else if (typeof source.note === 'string') {
        const text = document.createElement('span');
        text.textContent = source.note;
        item.append(text);
      }
      if (item.children.length > 1) section.append(item);
    });
    if (section.querySelector('.chat-source')) message.article.append(section);
  }
  function addMessage(role, text, meta = {}, { timestamp = Date.now(), id = null, restored = false } = {}) {
    const article = document.createElement('article');
    article.className = `chat-message chat-message--${role}`;
    article.dataset.role = role;
    article.dir = 'auto';
    const head = document.createElement('div'); head.className = 'chat-message-head';
    const name = document.createElement('strong'); name.textContent = role === 'user' ? 'You' : 'GAIA'; head.append(name);
    const time = document.createElement('time'); time.textContent = localTimestamp(timestamp); time.dateTime = new Date(timestamp).toISOString(); head.append(time);
    const body = document.createElement('div'); body.className = 'chat-message-body';
    body.dir = 'auto';
    if (role === 'user') body.textContent = text;
    else body.innerHTML = renderMarkdown(text);
    article.append(head, body);
    log.append(article);
    const message = { id: id || `message-${timestamp}-${messages.length}`, role, text, timestamp, article, body, meta };
    messages.push(message);
    applyMessageLanguage(message);
    applyAssistantRoute(message);
    if (role === 'assistant') {
      attachCodeCopy(article);
      renderSources(message);
      if (restored) insertLanguageDivider(message);
    }
    return message;
  }
  function previousAssistantLanguage(message) {
    const index = messages.indexOf(message);
    return messages.slice(0, index).reverse().find(item => item.role === 'assistant' && item.meta?.response_lang)?.meta.response_lang;
  }
  function insertLanguageDivider(message) {
    const current = message.meta?.response_lang;
    const previous = previousAssistantLanguage(message);
    if (!current || !previous || current === previous || message.switchDivider) return;
    const divider = document.createElement('div');
    divider.className = 'language-switch';
    divider.setAttribute('role', 'separator');
    divider.textContent = `Language switched: ${languageLabel(previous)} → ${languageLabel(current)}`;
    log.insertBefore(divider, message.article);
    message.switchDivider = divider;
  }
  function setAssistantMeta(meta) {
    if (!assistant) return;
    assistant.meta = { ...assistant.meta, ...meta };
    assistant.sourceUser.meta = { ...assistant.sourceUser.meta, language_meta: meta.language_meta };
    const record = currentConversation();
    if (record && meta.conversation_id) record.serverId = meta.conversation_id;
    applyMessageLanguage(assistant.sourceUser);
    applyMessageLanguage(assistant);
    applyAssistantRoute(assistant);
    insertLanguageDivider(assistant);
    persistMessage(assistant.sourceUser);
    if (record) {
      record.updatedAt = Date.now();
      persistHistory();
      renderHistory();
    }
  }
  function addInsightRow(list, label, value) {
    if (value === undefined || value === null || value === '') return;
    const term = document.createElement('dt'); term.textContent = label;
    const detail = document.createElement('dd'); detail.textContent = String(value);
    list.append(term, detail);
  }
  function insightsFor(message) {
    if (message.article.querySelector('.chat-insights')) return;
    const meta = message.meta || {};
    const lm = meta.language_meta || {};
    const done = meta.done || {};
    const details = document.createElement('details');
    details.className = 'chat-insights';
    details.dataset.chatMeta = 'insights';
    const summary = document.createElement('summary'); summary.textContent = 'Insights'; details.append(summary);
    const list = document.createElement('dl');
    addInsightRow(list, 'Detected language', lm.language ? languageLabel(lm.language, lm) : null);
    addInsightRow(list, 'Response language', meta.response_lang ? languageLabel(meta.response_lang, meta.response_lang === lm.language ? lm : {}) : null);
    addInsightRow(list, 'Detection confidence', lm.confidence == null ? null : `${Math.round(lm.confidence * 100)}%`);
    addInsightRow(list, 'Secondary languages', Array.isArray(lm.secondary_languages) && lm.secondary_languages.length
      ? lm.secondary_languages.map(code => languageLabel(code)).join(', ') : null);
    addInsightRow(list, 'Code switching', lm.code_switched ? `Yes${lm.mixed_script ? ' · mixed script' : ''}` : 'No');
    addInsightRow(list, 'Scripts', lm.scripts ? Object.entries(lm.scripts).map(([script, share]) => `${script} ${Math.round(Number(share) * 100)}%`).join(', ') : null);
    addInsightRow(list, 'Detection reason', lm.detection_reason);
    addInsightRow(list, 'Route', meta.route ? `${meta.route}${meta.reason ? ` · ${meta.reason}` : ''}` : null);
    addInsightRow(list, 'Intent', meta.intent ? `${meta.intent}${meta.confidence == null ? '' : ` · ${Math.round(meta.confidence * 100)}%`}` : null);
    addInsightRow(list, 'Model', done.model);
    addInsightRow(list, 'Latency', done.latency_ms == null ? null : `${Math.round(done.latency_ms)} ms`);
    addInsightRow(list, 'Technical state', meta.technical_error || (meta.error ? 'Reply error' : null));
    details.append(list);
    message.article.append(details);
  }
  function updateAssistant() {
    if (!assistant) return;
    assistant.body.innerHTML = renderMarkdown(assistant.text);
    attachCodeCopy(assistant.article);
    scrollLatest();
  }
  function retryMessage(message) {
    if (active || !message?.sourceUser) return;
    const index = messages.indexOf(message);
    if (index !== -1) messages.splice(index, 1);
    message.article.remove();
    const record = currentConversation();
    if (record) {
      record.messages = record.messages.filter(item => item.id !== message.id);
      record.updatedAt = Date.now();
      persistHistory();
      renderHistory();
    }
    sendMessage(message.sourceUser.text, { existingUser: message.sourceUser });
  }
  function actionsFor(article, message) {
    if (article.querySelector('.chat-actions')) return;
    const actions = document.createElement('div'); actions.className = 'chat-actions';
    if (message.role === 'assistant') {
      const copy = document.createElement('button'); copy.type = 'button'; copy.className = 'icon-button icon-button--quiet'; copy.textContent = 'Copy'; copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(plainText(message.text)); toast('Reply copied as text.'); } catch { toast('Clipboard unavailable. Select the reply and copy it manually.'); } }); actions.append(copy);
      const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'button button--quiet'; retry.textContent = 'Retry'; retry.addEventListener('click', () => retryMessage(message)); actions.append(retry);
    } else {
      const edit = document.createElement('button'); edit.type = 'button'; edit.className = 'button button--quiet'; edit.textContent = 'Edit'; edit.addEventListener('click', () => { input.value = message.text; updateInput(); input.focus(); }); actions.append(edit);
    }
    article.append(actions);
  }
  function setSendButton(label, danger = false) {
    const icon = send.querySelector('.icon');
    send.replaceChildren(document.createTextNode(label));
    if (icon) send.append(icon);
    send.classList.toggle('button--danger', danger);
  }
  function finishMessage() {
    if (!assistant) return;
    assistant.article.setAttribute('aria-busy', 'false');
    persistMessage(assistant);
    renderSources(assistant);
    actionsFor(assistant.article, assistant);
    insightsFor(assistant);
    assistant = null;
  }
  function restoreConversation(id, { persistCurrent = true } = {}) {
    requestNumber += 1;
    if (active) active.controller.abort();
    active = null;
    assistant = null;
    const record = recordFor(id);
    if (!record) return;
    currentRecord = record;
    historyState.currentId = record.id;
    conversationId = record.serverId || null;
    messages.length = 0;
    log.replaceChildren();
    input.value = '';
    let sourceUser = null;
    record.messages.forEach(stored => {
      const message = addMessage(stored.role, stored.text, stored.meta || {}, {
        timestamp: stored.timestamp,
        id: stored.id,
        restored: true,
      });
      if (message.role === 'user') {
        sourceUser = message;
        actionsFor(message.article, message);
      } else {
        message.sourceUser = sourceUser;
        actionsFor(message.article, message);
        insightsFor(message);
      }
    });
    const hasMessages = messages.length > 0;
    welcome.hidden = hasMessages;
    chatView.hidden = !hasMessages;
    setHeading(record.title);
    renderHistory();
    if (persistCurrent) persistHistory();
    main.scrollTop = main.scrollHeight;
    updateInput();
    document.dispatchEvent(new CustomEvent('v2conversationchange', { detail: { serverId: record.serverId } }));
  }
  function openRename(record, opener) {
    pendingRecord = record;
    renameInput.value = record.title === 'New conversation' ? '' : record.title;
    renameError.hidden = true;
    renameError.textContent = '';
    openOverlay('rename-dialog', opener);
    renameInput.focus();
    renameInput.select();
  }
  function saveRename() {
    if (!pendingRecord) return;
    const title = renameInput.value.trim();
    if (!title) {
      renameError.textContent = 'Add a title before saving.';
      renameError.hidden = false;
      renameInput.focus();
      return;
    }
    pendingRecord.title = title.slice(0, 80);
    pendingRecord.updatedAt = Date.now();
    persistHistory();
    renderHistory();
    if (pendingRecord.id === historyState.currentId) setHeading(pendingRecord.title);
    pendingRecord = null;
    closeOverlay(renameDialog);
  }
  function safeFilename(title) {
    const cleaned = String(title || 'conversation').normalize('NFKD').replace(/[^\w\s-]/g, '')
      .trim().replace(/\s+/g, '-').replace(/-+/g, '-').slice(0, 60);
    return `${cleaned || 'conversation'}.md`;
  }
  function exportConversation(record) {
    const lines = [`# ${record.title}`, ''];
    record.messages.forEach(message => {
      const meta = message.meta || {};
      const language = meta.response_lang || meta.language_meta?.language;
      lines.push(`## ${message.role === 'user' ? 'You' : 'GAIA'} · ${new Date(message.timestamp).toISOString()}`);
      if (language) lines.push(`_Language: ${language}_`, '');
      lines.push(message.text, '');
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = safeFilename(record.title);
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
    toast('Conversation exported as Markdown.');
  }
  function clearActiveView() {
    requestNumber += 1;
    if (active) active.controller.abort();
    active = null; assistant = null; conversationId = null; currentRecord = null;
    historyState.currentId = null;
    messages.length = 0;
    log.replaceChildren(); chatView.hidden = true; welcome.hidden = false;
    setHeading('New conversation');
    persistHistory();
    renderHistory();
    setSendButton('Send'); updateInput();
    document.dispatchEvent(new CustomEvent('v2conversationchange', { detail: { serverId: null } }));
  }
  async function confirmDelete(record, opener = document.activeElement) {
    if (!record) return;
    pendingRecord = record;
    deleteCopy.textContent = record.serverId
      ? 'This removes the saved conversation here and asks the server to delete its conversation data.'
      : 'This removes the saved conversation from this browser.';
    openOverlay('delete-dialog', opener);
  }
  async function removeConversation() {
    const record = pendingRecord;
    pendingRecord = null;
    if (!record) return;
    const wasCurrent = record.id === historyState.currentId;
    let serverFailed = false;
    if (record.serverId && !mock) {
      try { await deleteServerConversation(record.serverId); }
      catch { serverFailed = true; }
    }
    historyState.conversations = historyState.conversations.filter(item => item.id !== record.id);
    if (wasCurrent) {
      const next = historyState.conversations.slice().sort((a, b) => b.updatedAt - a.updatedAt)[0];
      if (next) restoreConversation(next.id);
      else clearActiveView();
    } else {
      persistHistory();
      renderHistory();
    }
    if (serverFailed) toast('Conversation removed locally, but server cleanup failed.');
    else toast('Conversation deleted.');
  }
  async function sendMessage(value = input.value, { existingUser = null } = {}) {
    const message = value.trim();
    if (!message || message.length > MAX_CHARS || active) return;
    requestNumber += 1;
    const owner = requestNumber;
    if (!existingUser) {
      input.value = '';
      updateInput();
    }
    welcome.hidden = true; chatView.hidden = false;
    const record = ensureConversation();
    setHeading(record.title);
    const userMessage = existingUser || addMessage('user', message);
    if (!existingUser) {
      if (record.title === 'New conversation') record.title = titleFromMessage(message);
      setHeading(record.title);
      persistMessage(userMessage);
      actionsFor(userMessage.article, userMessage);
    }
    assistant = addMessage('assistant', '', { pending: true });
    assistant.sourceUser = userMessage;
    assistant.article.setAttribute('aria-busy', 'true');
    assistant.body.innerHTML = '<div class="thinking-lines" aria-hidden="true"><span></span><span></span><span></span></div><span class="sr-only">GAIA is preparing a reply</span>';
    setSendButton('Stop', true); send.disabled = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), STREAM_TIMEOUT);
    active = { controller, timeout, owner };
    let sawError = false, sawDelta = false;
    const onFrame = frame => {
      if (!active || active.owner !== owner) return;
      if (frame.type === 'meta') { conversationId = frame.conversation_id || conversationId; setAssistantMeta(frame); }
      if (frame.type === 'delta') {
        sawDelta = true;
        assistant.text += frame.text || '';
        if (frame.intent !== undefined) assistant.meta = { ...assistant.meta, intent: frame.intent, confidence: frame.confidence, degraded: frame.degraded };
        updateAssistant();
      }
      if (frame.type === 'error') {
        sawError = true;
        assistant.meta = { ...assistant.meta, error: true, technical_error: frame.message || 'stream error' };
        assistant.text = frame.message || 'The assistant returned an error.';
        updateAssistant();
      }
      if (frame.type === 'done') assistant.meta = { ...assistant.meta, done: frame };
    };
    try {
      if (mock) await mockStream(message, { signal: controller.signal, onFrame });
      else await streamLive(message, conversationId, { signal: controller.signal, onFrame });
      if (!sawDelta && !sawError) { assistant.text = 'The assistant returned an empty reply.'; sawError = true; updateAssistant(); }
      finishMessage();
    } catch (error) {
      if (active?.owner === owner) {
        assistant.text = error.name === 'AbortError' && assistant.text
          ? `${assistant.text}\n\n*Reply stopped before completion.*`
          : safeError(error);
        assistant.meta = { ...assistant.meta, error: true, technical_error: error.name === 'AbortError' ? 'Reply stopped' : safeError(error) };
        updateAssistant();
        finishMessage();
        if (error.name !== 'AbortError') toast(safeError(error));
      }
    } finally {
      clearTimeout(timeout);
      if (active?.owner === owner) { active = null; setSendButton('Send'); updateInput(); }
    }
  }
  input.addEventListener('input', updateInput);
  historySearch.addEventListener('input', renderHistory);
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); form.requestSubmit(); } });
  form.addEventListener('submit', event => { event.preventDefault(); sendMessage(); });
  document.addEventListener('v2documentstate', event => {
    documentProcessing = Boolean(event.detail?.processing);
    if (documentProcessing) composerNote.textContent = 'Document processing… wait until it is ready before asking about it.';
    else if (!mock) composerNote.textContent = 'Documents are ready when the panel says Ready.';
    updateInput();
  });
  renameForm.addEventListener('submit', event => { event.preventDefault(); saveRename(); });
  deleteForm.addEventListener('submit', async event => {
    event.preventDefault();
    await closeOverlay(deleteDialog);
    await removeConversation();
  });
  send.addEventListener('click', () => { if (active) active.controller.abort(); else sendMessage(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && active) { event.preventDefault(); active.controller.abort(); } });
  document.addEventListener('click', async event => {
    const action = event.target.closest('[data-history-action]');
    if (action) {
      const record = recordFor(action.dataset.recordId);
      if (!record) return;
      const fromMobileNavigation = !desktop.matches && navigationDrawer.contains(action);
      if (fromMobileNavigation) await closeNavigation();
      const opener = fromMobileNavigation ? sidebarToggle : action;
      if (action.dataset.historyAction === 'rename') openRename(record, opener);
      if (action.dataset.historyAction === 'export') exportConversation(record);
      if (action.dataset.historyAction === 'delete') confirmDelete(record, opener);
      return;
    }
    const saved = event.target.closest('[data-history-id]');
    if (saved) {
      if (!desktop.matches && navigationDrawer.contains(saved)) await closeNavigation();
      restoreConversation(saved.dataset.historyId);
      return;
    }
    const fresh = event.target.closest('[data-new-chat]');
    if (fresh) {
      clearActiveView();
    }
  });
  composerNote.textContent = mock
    ? 'Mock chat only · no backend request or server memory.'
    : 'Phase 6 chat · conversations stay in this browser.';
  renderHistory();
  if (historyResult.status === 'unavailable') toast('Browser history storage is unavailable. This chat will remain for this tab.');
  if (historyState.currentId) restoreConversation(historyState.currentId, { persistCurrent: false });
  updateInput();
  return {
    ensureServerConversationId,
    getServerConversationId: () => currentConversation()?.serverId || null,
    getLastDetectedLanguage: () => messages.slice().reverse().find(item => item.role === 'user' && item.meta?.language_meta?.language)?.meta.language_meta.language || null,
  };
}
