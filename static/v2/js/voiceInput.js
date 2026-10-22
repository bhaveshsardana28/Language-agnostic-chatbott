import { getPreferences } from './preferences.js';
import { toast } from './ui.js';

const LOCALE_BY_LANGUAGE = Object.freeze({
  en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT',
});

const ERROR_COPY = Object.freeze({
  'not-allowed': 'Microphone permission was denied. Allow speech recognition or type your message instead.',
  'service-not-allowed': 'Speech recognition is blocked by this browser or OS. Type your message instead.',
  'audio-capture': 'No microphone was available. Check the device input or type your message instead.',
  'no-speech': 'No speech was detected. Try again when you are ready.',
  network: 'Speech recognition could not reach its service. Check the connection or type your message instead.',
});

function recognitionConstructor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function initVoiceInput(chat) {
  const button = document.getElementById('voice-input-button');
  const input = document.getElementById('message-input');
  const status = document.getElementById('voice-input-status');
  const form = document.getElementById('composer-form');
  let recognition = null;
  let state = 'idle';
  let baseText = '';
  let finalSegments = [];
  let lastError = false;

  const supported = Boolean(recognitionConstructor());
  const setStatus = text => { status.textContent = text; };
  const localeFor = () => {
    const preference = getPreferences().speechLanguage;
    if (preference !== 'auto') return preference;
    return LOCALE_BY_LANGUAGE[chat.getLastDetectedLanguage?.()] || 'en-IN';
  };
  const syncButton = () => {
    const listening = state === 'listening';
    const requesting = state === 'requesting';
    button.disabled = !supported || requesting;
    button.setAttribute('aria-pressed', String(listening));
    button.dataset.state = state;
    button.setAttribute('aria-label', listening ? 'Stop voice input' : 'Start voice input');
    button.title = supported ? (listening ? 'Stop voice input' : 'Start voice input') : 'Voice input is not supported in this browser';
  };
  const setState = (next, message) => {
    state = next;
    if (message) setStatus(message);
    syncButton();
  };
  const updateDraft = interim => {
    const transcript = [...finalSegments, interim].filter(Boolean).join(' ').trim();
    const separator = baseText && transcript ? `${baseText.trimEnd()} ` : baseText.trimEnd();
    input.value = `${separator}${transcript}`;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const finish = message => {
    recognition = null;
    setState('idle', message || (lastError ? status.textContent : 'Voice input ready when supported.'));
  };
  const stop = (message = 'Voice input stopped.') => {
    if (!recognition) {
      if (state !== 'idle') finish(message);
      return;
    }
    try { recognition.stop(); } catch { /* already stopped */ }
    finish(message);
  };
  const start = () => {
    if (!supported) return;
    if (state === 'requesting' || state === 'listening') { stop(); return; }
    const Recognition = recognitionConstructor();
    baseText = input.value;
    finalSegments = [];
    lastError = false;
    let instance;
    try { instance = new Recognition(); recognition = instance; } catch {
      finish('Voice input could not start. Type your message instead.');
      return;
    }
    instance.continuous = false;
    instance.interimResults = true;
    instance.maxAlternatives = 1;
    instance.lang = localeFor();
    instance.onstart = () => { if (recognition === instance) setState('listening', `Listening in ${instance.lang}. Speak when ready.`); };
    instance.onresult = event => {
      if (recognition !== instance) return;
      let interim = '';
      for (let index = event.resultIndex || 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result?.[0]?.transcript || '';
        if (result.isFinal) finalSegments[index] = transcript;
        else interim += transcript;
      }
      updateDraft(interim);
    };
    instance.onerror = event => {
      if (recognition !== instance) return;
      lastError = true;
      const message = ERROR_COPY[event.error] || 'Voice input stopped unexpectedly. Type your message instead.';
      setStatus(message);
      toast(message);
    };
    instance.onend = () => { if (recognition === instance) finish(lastError ? status.textContent : 'Voice input ready when supported.'); };
    setState('requesting', `Requesting voice input in ${instance.lang}…`);
    try { instance.start(); }
    catch { finish('Voice input could not start. Type your message instead.'); }
  };

  if (!supported) {
    button.disabled = true;
    button.dataset.state = 'unsupported';
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', 'Voice input unavailable');
    button.title = 'Voice input is not supported in this browser';
    setStatus('Voice input is not supported in this browser. Type your message instead.');
  } else {
    syncButton();
    button.addEventListener('click', start);
    document.addEventListener('keydown', event => {
      if (event.defaultPrevented || !event.shiftKey || event.key.toLowerCase() !== 'm' || (!event.metaKey && !event.ctrlKey)) return;
      event.preventDefault();
      start();
    });
  }
  form.addEventListener('submit', () => stop('Voice input stopped. Draft is ready to send.'), true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && (state === 'requesting' || state === 'listening')) {
      event.preventDefault();
      stop();
    }
  }, true);
  document.addEventListener('click', event => {
    if (event.target.closest('[data-new-chat]')) stop();
  });
  document.addEventListener('v2conversationchange', () => stop());
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop('Voice input paused while this tab is hidden.'); });
  window.addEventListener('pagehide', () => stop());
}
