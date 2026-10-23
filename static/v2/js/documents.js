import { clearDocuments, getDocumentReport, listDocuments, uploadDocument } from './api.js';
import { openOverlay, toast } from './ui.js';

const DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(['.pdf', '.docx', '.txt', '.md', '.csv', '.json', '.py', '.js', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp', '.heic', '.heif']);
const mock = new URLSearchParams(location.search).get('mock') === '1';

function extensionOf(name) {
  const dot = String(name || '').lastIndexOf('.');
  return dot === -1 ? '' : String(name).slice(dot).toLowerCase();
}

function uploadError(error) {
  if (error.status === 415) return error.message || 'That file type is not supported.';
  if (error.status === 413) return error.message || 'That file is empty or larger than the configured limit.';
  if (error.status === 422) {
    return /ocr|language pack|corrupt|extractable/i.test(error.message || '')
      ? error.message
      : 'The document could not be read. Try another file.';
  }
  return error.message || 'The document could not be uploaded.';
}

export function initDocuments(chat) {
  const dialog = document.getElementById('documents-dialog');
  const input = document.getElementById('document-file');
  const choose = document.getElementById('document-choose');
  const clear = document.getElementById('document-clear');
  const status = document.getElementById('document-status');
  const list = document.getElementById('document-list');
  const empty = document.getElementById('document-empty');
  const count = document.getElementById('document-count');
  const preview = document.getElementById('document-preview');
  const previewCard = document.getElementById('document-preview-card');
  const previewTitle = document.getElementById('document-preview-title');
  const previewMeta = document.getElementById('document-preview-meta');
  const composerContext = document.getElementById('composer-context');
  const composerContextText = document.getElementById('composer-context-text');
  const composer = document.getElementById('composer-form');
  const attachButton = document.getElementById('attach-menu-button');
  const dropzone = document.getElementById('document-dropzone');
  let records = [];
  let active = null;
  let sequence = 0;
  let previewSequence = 0;

  function setStatus(text, state = '') {
    status.textContent = text;
    status.dataset.state = state;
  }
  function renderComposerContext() {
    const ready = records.filter(item => item.status === 'ready');
    const processing = records.filter(item => item.status === 'processing');
    if (!ready.length && !processing.length) {
      composerContext.hidden = true;
      composerContextText.textContent = '';
      return;
    }
    composerContext.hidden = false;
    if (processing.length) {
      composerContextText.textContent = `${processing.length} source${processing.length === 1 ? '' : 's'} preparing · wait until Ready before asking about them`;
    } else {
      const names = ready.slice(0, 2).map(item => item.document).join(', ');
      const suffix = ready.length > 2 ? ` + ${ready.length - 2} more` : '';
      composerContextText.textContent = `${ready.length} source${ready.length === 1 ? '' : 's'} ready · ${names}${suffix}`;
    }
  }
  function render() {
    list.replaceChildren();
    empty.hidden = records.length > 0;
    const ready = records.filter(item => item.status === 'ready').length;
    count.textContent = `${ready} ready · ${records.length} ${records.length === 1 ? 'document' : 'documents'}`;
    clear.disabled = !records.length || Boolean(active);
    renderComposerContext();
    records.forEach(record => {
      const row = document.createElement('li');
      row.className = 'document-row';
      const mark = document.createElement('span');
      mark.className = 'document-file-mark';
      mark.textContent = extensionOf(record.document).replace('.', '').toUpperCase().slice(0, 4) || 'FILE';
      mark.setAttribute('aria-hidden', 'true');
      const name = document.createElement('strong');
      name.textContent = record.document;
      const detail = document.createElement('span');
      detail.className = 'field-note';
      detail.textContent = record.status === 'processing' ? 'Uploading and preparing…'
        : record.status === 'failed' ? (record.error || 'Upload failed')
          : `${record.chunks || 0} ${record.chunks === 1 ? 'chunk' : 'chunks'}${record.page_count ? ` · ${record.page_count} page${record.page_count === 1 ? '' : 's'}` : ''}${record.detected_language ? ` · ${record.detected_language}` : ''}`;
      const chip = document.createElement('span');
      chip.className = `chip document-status document-status--${record.status}`;
      chip.textContent = record.status === 'processing' ? 'Processing' : record.status === 'failed' ? 'Failed' : 'Ready';
      row.append(mark, name, detail, chip);
      if (record.status === 'failed' && record.file) {
        const retry = document.createElement('button');
        retry.className = 'button button--quiet document-preview-button';
        retry.type = 'button';
        retry.textContent = 'Retry';
        retry.addEventListener('click', () => upload(record.file));
        row.append(retry);
      }
      if (record.status === 'ready' && record.document_id && !mock) {
        const button = document.createElement('button');
        button.className = 'button button--quiet document-preview-button';
        button.type = 'button';
        button.textContent = 'Preview text';
        button.addEventListener('click', () => showPreview(record));
        row.append(button);
      }
      list.append(row);
    });
  }
  async function showPreview(record, source = null) {
    if (!record.document_id) return;
    const previewOwner = ++previewSequence;
    const serverId = chat.getServerConversationId();
    previewCard.hidden = false;
    preview.hidden = false;
    previewTitle.textContent = source ? `Evidence from ${record.document}` : 'Extracted text';
    const chunkLabel = Number.isFinite(Number(source?.chunk)) ? ` · retrieved chunk ${Number(source.chunk) + 1}` : '';
    previewMeta.textContent = source?.excerpt
      ? `Retrieved passage${source.page ? ` · page ${source.page}` : ''}${chunkLabel}`
      : source?.page ? `Page ${source.page}${chunkLabel}` : 'The readable text returned by the document service.';
    preview.textContent = 'Loading extracted text…';
    try {
      const report = await getDocumentReport(serverId, record.document_id);
      if (previewOwner !== previewSequence || serverId !== chat.getServerConversationId()) return;
       const page = source?.page && Array.isArray(report.pages)
         ? report.pages.find(item => Number(item.page_number) === Number(source.page)) : null;
       preview.textContent = source?.excerpt || page?.text || report.full_text || 'No readable text was extracted.';
       if (source) previewCard.scrollIntoView({ block: 'nearest', behavior: document.documentElement.dataset.motion === 'reduced' ? 'auto' : 'smooth' });
    } catch (error) {
      if (previewOwner !== previewSequence || serverId !== chat.getServerConversationId()) return;
      preview.textContent = error.message || 'Could not load the extracted text.';
    }
  }
  function clearView(text = 'Choose a file to add context to this conversation.') {
    records = [];
    previewSequence += 1;
    setStatus(text);
    previewCard.hidden = true;
    preview.hidden = true;
    preview.textContent = '';
    previewTitle.textContent = 'Extracted text';
    previewMeta.textContent = '';
    render();
  }
  async function refresh() {
    const serverId = chat.getServerConversationId();
    if (!serverId) {
      clearView();
      return;
    }
    if (mock) {
      setStatus(records.length ? 'Documents are simulated in this tab.' : 'Choose a file to add context to this conversation.');
      render();
      return;
    }
    const owner = ++sequence;
    setStatus('Loading documents…', 'loading');
    try {
      const result = await listDocuments(serverId);
      if (owner !== sequence || serverId !== chat.getServerConversationId()) return;
      records = (result.documents || []).map(item => ({ ...item, status: 'ready' }));
      setStatus(records.length ? 'Documents ready for this conversation.' : 'Choose a file to add context to this conversation.');
      render();
    } catch (error) {
      if (owner !== sequence) return;
      setStatus(error.message || 'Could not load documents.', 'error');
      render();
    }
  }
  async function upload(file) {
    if (!file) return;
    if (active) {
      toast('A document is already being prepared. Wait until it is Ready.');
      return;
    }
    const extension = extensionOf(file.name);
    if (!ALLOWED_EXTENSIONS.has(extension)) {
       setStatus('That file type is not supported. Use PDF, DOCX, TXT, Markdown, or a supported image.', 'error');
      toast('That file type is not supported. Choose a PDF, DOCX, text, or image file.');
      input.value = '';
      return;
    }
    const maxUploadBytes = Number(globalThis.gaiaDocumentCapabilities?.max_upload_bytes || DEFAULT_MAX_UPLOAD_BYTES);
     if (!file.size || file.size > maxUploadBytes) {
       const limitMiB = maxUploadBytes / (1024 * 1024);
       const limitLabel = Number.isInteger(limitMiB) ? String(limitMiB) : limitMiB.toFixed(1);
       setStatus(`That file is empty or larger than ${limitLabel} MiB.`, 'error');
       toast(`Choose a file smaller than ${limitLabel} MiB.`);
       input.value = '';
       return;
    }
    const record = { document: file.name, chunks: 0, status: 'processing' };
    records = records.filter(item => item.document !== file.name);
    records.unshift(record);
    render();
    setStatus(`Processing ${file.name}…`, 'loading');
    document.dispatchEvent(new CustomEvent('v2documentstate', { detail: { processing: true } }));
    const owner = ++sequence;
    active = { owner };
    clear.disabled = true;
    try {
      const serverId = await chat.ensureServerConversationId();
      if (active?.owner !== owner) return;
      if (mock) {
        await new Promise(resolve => setTimeout(resolve, 180));
        if (active?.owner !== owner) return;
        record.status = 'ready'; record.chunks = 1;
      } else {
        const report = await uploadDocument(file, serverId);
        if (active?.owner !== owner) return;
        Object.assign(record, report);
        record.status = report.status === 'completed' || !report.status ? 'ready' : report.status;
        try {
          await refresh();
        } catch {
          // The upload is already committed; a list refresh failure must not
          // misreport the document as failed or encourage a duplicate retry.
          records = records.filter(item => item !== record);
          records.unshift(record);
          setStatus(`${file.name} is ready, but the document list could not refresh.`, 'ready');
        }
      }
      if (record.status === 'ready') {
        setStatus(`${file.name} is ready.`, 'ready');
        toast('Document ready for this conversation.');
      }
    } catch (error) {
      records = records.filter(item => item !== record);
      record.status = 'failed'; record.error = uploadError(error); record.file = file;
      records.unshift(record);
      setStatus(record.error, 'error');
      toast(record.error);
    } finally {
      if (active?.owner === owner) {
        active = null;
        input.value = '';
        render();
      }
      document.dispatchEvent(new CustomEvent('v2documentstate', { detail: { processing: false } }));
    }
  }
  async function clearAll() {
    const serverId = chat.getServerConversationId();
    if (!serverId || !records.length || active) return;
    if (!window.confirm('Clear all documents from this conversation?')) return;
    if (mock) {
      clearView();
      toast('Documents cleared.');
      return;
    }
    const owner = ++sequence;
    clear.disabled = true;
    setStatus('Clearing documents…', 'loading');
    try {
      await clearDocuments(serverId);
      if (owner !== sequence) return;
      clearView('Choose a file to add context to this conversation.');
      toast('Documents cleared.');
    } catch (error) {
      if (owner !== sequence) return;
      setStatus(error.message || 'Could not clear documents.', 'error');
      render();
    }
  }

  choose.addEventListener('click', () => input.click());
  input.addEventListener('change', () => upload(input.files?.[0]));
  clear.addEventListener('click', clearAll);
  composer?.addEventListener('dragover', event => {
    if (!event.dataTransfer?.files?.length) return;
    event.preventDefault();
    composer.dataset.uploadDragging = 'true';
  });
  composer?.addEventListener('dragleave', event => {
    if (!composer.contains(event.relatedTarget)) delete composer.dataset.uploadDragging;
  });
  composer?.addEventListener('drop', event => {
    if (!event.dataTransfer?.files?.length) return;
    event.preventDefault();
    delete composer.dataset.uploadDragging;
    upload(event.dataTransfer.files[0]);
  });
  composer?.addEventListener('paste', event => {
    const file = [...(event.clipboardData?.files || [])][0];
    if (!file) return;
    event.preventDefault();
    upload(file);
  });
  dropzone.addEventListener('click', event => {
    if (!event.target.closest('button')) input.click();
  });
  dropzone.addEventListener('dragover', event => {
    event.preventDefault();
    dropzone.dataset.dragging = 'true';
  });
  dropzone.addEventListener('dragleave', event => {
    if (!dropzone.contains(event.relatedTarget)) delete dropzone.dataset.dragging;
  });
  dropzone.addEventListener('drop', event => {
    event.preventDefault();
    delete dropzone.dataset.dragging;
    upload(event.dataTransfer?.files?.[0]);
  });
  document.addEventListener('click', event => {
    const attachAction = event.target.closest('[data-attach-action]');
    if (attachAction) {
      if (attachAction.dataset.attachAction === 'upload') input.click();
      if (attachAction.dataset.attachAction === 'browse') openOverlay('documents-dialog', attachButton);
      return;
    }
    if (event.target.closest('[data-shell-open="documents-dialog"]')) setTimeout(refresh, 0);
  });
  document.addEventListener('v2sourceopen', async event => {
    const source = event.detail || {};
    const serverId = chat.getServerConversationId();
    if (!serverId || !source.document) return;
    openOverlay('documents-dialog', event.target instanceof Element ? event.target : document.activeElement);
    if (!records.length) await refresh();
    const record = records.find(item => source.document_id && Number(item.document_id) === Number(source.document_id))
      || records.find(item => item.document === source.document);
    if (record) showPreview(record, source);
    else setStatus(`Evidence source “${source.document}” is not available in this conversation.`, 'error');
  });
  document.addEventListener('v2conversationchange', () => {
    previewSequence += 1;
    if (active) { active = null; sequence += 1; }
    clearView('Choose a file to add context to this conversation.');
    if (dialog.open) refresh();
  });
  clearView();
}
