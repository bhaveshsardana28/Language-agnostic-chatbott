import { stopPlayback } from './voiceOutput.js';
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
  let watchdog;

  const supported = Boolean(recognitionConstructor());
  const setStatus = text => {
    status.textContent = text;
    status.dataset.quiet = String(text === 'Voice input ready.');
  };
  const localeFor = () => {
    const preference = getPreferences().speechLanguage;
    if (preference !== 'auto') return preference;
    return LOCALE_BY_LANGUAGE[chat.getLastDetectedLanguage?.()] || 'en-IN';
  };
  const syncButton = () => {
    const listening = state === 'listening';
    const engaged = listening || state === 'processing';
    const requesting = state === 'requesting';
    button.disabled = !supported || requesting;
    button.setAttribute('aria-pressed', String(listening));
    button.dataset.state = state;
    button.setAttribute('aria-label', engaged ? 'Stop voice input' : 'Start voice input');
    button.title = supported ? (engaged ? 'Stop voice input' : 'Start voice input') : 'Voice input is not supported in this browser';
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
    clearTimeout(watchdog);
    recognition = null;
    setState('idle', message || 'Voice input ready.');
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
    if (state === 'requesting' || state === 'listening' || state === 'processing') { stop(); return; }
    stopPlayback();
    const Recognition = recognitionConstructor();
    baseText = input.value;
    finalSegments = [];
    let instance;
    try { instance = new Recognition(); recognition = instance; } catch {
      finish('Voice input could not start. Type your message instead.');
      return;
    }
    instance.continuous = false;
    instance.interimResults = true;
    instance.maxAlternatives = 1;
    instance.lang = localeFor();
    const timeout = (delay, message) => {
      clearTimeout(watchdog);
      watchdog = setTimeout(() => {
        if (recognition !== instance) return;
        finish(message);
        try { instance.abort(); } catch { /* engine already ended */ }
      }, delay);
    };
    instance.onstart = () => {
      if (recognition !== instance) return;
      setState('listening', `Listening in ${instance.lang}. Speak when ready.`);
      timeout(90000, 'Voice input timed out. Your draft is ready to edit.');
    };
    instance.onspeechend = () => {
      if (recognition !== instance) return;
      setState('processing', 'Finishing transcription…');
      timeout(12000, 'Transcription timed out. Review your draft or try again.');
    };
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
      const message = ERROR_COPY[event.error] || 'Voice input stopped unexpectedly. Type your message instead.';
      finish(message);
      toast(message);
    };
    instance.onend = () => { if (recognition === instance) finish(); };
    setState('requesting', `Requesting voice input in ${instance.lang}…`);
    timeout(20000, 'Voice service did not start. Check microphone permissions or type your message.');
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
    setStatus('Voice input ready.');
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
    if (event.key === 'Escape' && (state === 'requesting' || state === 'listening' || state === 'processing')) {
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
