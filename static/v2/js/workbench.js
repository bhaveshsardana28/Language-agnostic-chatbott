import { initAppearance } from './appearance.js';
import { initIcons } from './icons.js';
import { initUI, selectTab, toast } from './ui.js';

initIcons();
initUI();
initAppearance();

const search = document.getElementById('collection-search');
search.addEventListener('input', () => {
  const match = 'a small question about language english deutsch'.includes(search.value.trim().toLowerCase());
  document.getElementById('sample-conversation').hidden = !match;
  document.getElementById('empty-search').hidden = match;
  document.getElementById('search-status').textContent = match ? 'One sample conversation.' : 'No matching sample conversations.';
});

let thinkingTimer;
function previewThinking() {
  clearTimeout(thinkingTimer);
  const reply = document.getElementById('preview-reply');
  const thinking = document.getElementById('thinking-preview');
  const text = document.getElementById('reply-de');
  reply.setAttribute('aria-busy', 'true');
  thinking.hidden = false;
  text.hidden = true;
  document.querySelectorAll('[data-thinking], [data-copy="reply-de"]').forEach(button => { button.disabled = true; });
  // Fixture delay for the component preview, never presented as backend latency.
  thinkingTimer = setTimeout(() => {
    reply.setAttribute('aria-busy', 'false');
    thinking.hidden = true;
    text.hidden = false;
    document.querySelectorAll('[data-thinking], [data-copy="reply-de"]').forEach(button => { button.disabled = false; });
    toast('Thinking preview finished. No API request was made.');
  }, 1800);
}

async function copySample(id) {
  const text = document.getElementById(id).innerText;
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(text);
    toast('Sample reply copied as text.');
  } catch { toast('Clipboard access is unavailable. Select the reply text and copy it manually.'); }
}

document.addEventListener('click', event => {
  const view = event.target.closest('[data-view]');
  if (view) {
    event.preventDefault();
    const tab = document.getElementById(`tab-${view.dataset.view}`);
    const dialog = view.closest('dialog');
    selectTab(tab, !dialog);
    if (dialog) dialog.addEventListener('close', () => tab.focus(), { once: true });
  }
  const library = event.target.closest('[data-library-tab]');
  if (library) selectTab(document.getElementById(`tab-${library.dataset.libraryTab}`));
  const copy = event.target.closest('[data-copy]');
  if (copy) copySample(copy.dataset.copy);
  if (event.target.closest('[data-thinking]')) previewThinking();
});
document.getElementById('upload-preview').addEventListener('click', () => {
  toast('Document component preview. No file was uploaded.');
});

const form = document.getElementById('preview-composer');
const message = document.getElementById('preview-message');
const error = document.getElementById('composer-error');
form.addEventListener('submit', event => {
  event.preventDefault();
  const empty = !message.value.trim();
  message.setAttribute('aria-invalid', String(empty));
  error.hidden = !empty;
  error.textContent = empty ? 'Write a thought to try this component.' : '';
  if (empty) { message.focus(); return; }
  toast('Preview only. Your draft stayed here; no request was sent.');
});
message.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); form.requestSubmit();
  }
});
message.addEventListener('input', () => {
  if (!error.hidden && message.value.trim()) { error.hidden = true; message.setAttribute('aria-invalid', 'false'); }
});

const voiceCopy = {
  idle: 'A quiet place for your next thought.',
  listening: '“Ich möchte jeden Tag ein bisschen üben …”',
  thinking: 'Making room for an answer. Visual preview only.',
  speaking: 'An answer in your language. Visual preview only.',
};
document.getElementById('voice-state').addEventListener('change', event => {
  const state = event.target.value;
  document.getElementById('voice-orb').dataset.state = state;
  document.getElementById('voice-state-label').textContent = `${state[0].toUpperCase()}${state.slice(1)} · design preview`;
  const copy = document.getElementById('voice-copy');
  copy.textContent = voiceCopy[state];
  copy.lang = state === 'listening' ? 'de' : 'en';
  copy.dir = 'auto';
});
