import { API_BASE } from '../config.js';

export async function health({ signal } = {}) {
  const response = await fetch(`${API_BASE}/api/v1/health`, { signal, cache: 'no-store', credentials: 'include' });
  if (!response.ok) throw new Error('Health request failed');
  const data = await response.json();
  if (!data || data.status !== 'ok' || typeof data.llm_ready !== 'boolean') {
    throw new Error('Invalid health response');
  }
  globalThis.gaiaDocumentCapabilities = data;
  return { status: data.status, llm_ready: data.llm_ready,
    max_upload_bytes: data.max_upload_bytes, max_document_pages: data.max_document_pages,
    supported_document_suffixes: data.supported_document_suffixes };
}

export async function createConversation({ signal } = {}) {
  const response = await fetch(`${API_BASE}/api/v1/conversations`, { method: 'POST', signal, credentials: 'include' });
  if (!response.ok) throw new Error('Could not create a conversation');
  const data = await response.json();
  if (!data.conversation_id) throw new Error('Server returned no conversation ID');
  return data.conversation_id;
}

export async function deleteConversation(conversationId, { signal } = {}) {
  const response = await fetch(`${API_BASE}/api/v1/chat/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
    signal,
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Could not delete the server conversation');
  return response.json();
}

async function documentResponse(response, fallback) {
  if (response.ok) return response.json();
  const error = new Error(fallback);
  error.status = response.status;
  const payload = await response.json().catch(() => ({}));
  error.message = payload.error || fallback;
  throw error;
}

export async function uploadDocument(file, conversationId, { signal } = {}) {
  const form = new FormData();
  form.append('file', file);
  form.append('conversation_id', conversationId);
  return documentResponse(await fetch(`${API_BASE}/api/v1/documents`, {
    method: 'POST', body: form, signal, credentials: 'include',
  }), 'Could not upload that document.');
}

export async function listDocuments(conversationId, { signal } = {}) {
  return documentResponse(await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(conversationId)}`, {
    signal, cache: 'no-store', credentials: 'include',
  }), 'Could not load documents.');
}

export async function getDocumentReport(conversationId, documentId, { signal } = {}) {
  return documentResponse(await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(conversationId)}/${encodeURIComponent(documentId)}`, {
    signal, cache: 'no-store', credentials: 'include',
  }), 'Could not load the extracted document text.');
}

export async function deleteDocument(conversationId, documentId, { signal } = {}) {
  return documentResponse(await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(conversationId)}/${encodeURIComponent(documentId)}`, {
    method: 'DELETE', signal, credentials: 'include',
  }), 'Could not remove that document.');
}

export async function clearDocuments(conversationId, { signal } = {}) {
  return documentResponse(await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE', signal, credentials: 'include',
  }), 'Could not clear documents.');
}
