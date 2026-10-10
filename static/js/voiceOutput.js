/**
 * GAIA Voice Output — SpeechSynthesis with language-matched voices,
 * sentence-queued stream-aware reading, barge-in, missing-voice fallback.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;

  const BCP = { en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT' };
  const NATIVE = { en: 'English', hi: 'हिन्दी', pa: 'ਪੰਜਾਬੀ', es: 'Español', fr: 'Français', de: 'Deutsch', it: 'Italiano' };

  const SYNTH = () => window.speechSynthesis || null;

  let speakQueue = [], speakingTs = null, speakPaused = false;

  function voicesFor(lang) {
    const s = SYNTH(); if (!s) return [];
    const base = (BCP[lang] || lang || 'en').split('-')[0].toLowerCase();
    return s.getVoices().filter(v => v.lang && v.lang.toLowerCase().startsWith(base));
  }

  function stopSpeak() {
    const s = SYNTH(); if (s) s.cancel();
    speakQueue = []; speakingTs = null; speakPaused = false; updateListenUI();
  }
  chat.stopSpeak = stopSpeak;

  function speakNext() {
    const s = SYNTH(); if (!s || !speakQueue.length) { speakingTs = null; updateListenUI(); return; }
    const item = speakQueue.shift();
    const vs = voicesFor(item.lang);
    if (!vs.length) { chat.toast(`No voice available for ${NATIVE[item.lang] || item.lang} on this device.`); return speakNext(); }
    const u = new SpeechSynthesisUtterance(item.text);
    u.voice = vs[0]; u.lang = vs[0].lang; u.rate = store.get('speakRate') || 1;
    u.onend = u.onerror = () => speakNext();
    s.speak(u);
  }

  function speakMessage(m) {
    if (speakingTs === m.ts) {
      const s = SYNTH(); if (!s) { stopSpeak(); return; }
      if (speakPaused) { if (typeof s.resume === 'function') { s.resume(); speakPaused = false; } }
      else if (typeof s.pause === 'function') { s.pause(); speakPaused = true; }
      else { stopSpeak(); }
      updateListenUI(); return;
    }
    stopSpeak();
    const lang = m.meta?.language_meta?.language || 'en';
    const text = speechText(m.content);
    if (!text) { chat.toast('Nothing to read aloud.'); return; }
    speakQueue = [{ text, lang }]; speakingTs = m.ts; speakPaused = false; updateListenUI(); speakNext();
  }
  chat.speakMessage = speakMessage;

  function updateListenUI() {
    document.querySelectorAll('.listen-btn').forEach(b => {
      const ts = b.closest('.msg')?.dataset.id;
      const mine = ts && ts === String(speakingTs);
      b.classList.toggle('speaking', !!mine && !speakPaused);
      b.classList.toggle('paused', !!mine && speakPaused);
      b.setAttribute('aria-label', mine ? (speakPaused ? 'Resume reading' : 'Pause reading') : 'Listen');
    });
  }

  function feedSpeech(delta, ts, lang) {
    if (!store.get('autoRead') || !SYNTH()) return;
    if (!speechBuf) speechBuf = '';
    speechBuf += delta;
    const parts = speechText(speechBuf).split(/(?<=[.!?।])\s+/).filter(s => s.trim().length > 1);
    while (parts.length > spokenSentences) {
      const text = parts[spokenSentences++].trim();
      speakQueue.push({ text, lang });
      if (!speakingTs) { speakingTs = Number(ts); updateListenUI(); }
      speakNext();
    }
  }
  let speechBuf = '', spokenSentences = 0;
  chat.feedSpeech = feedSpeech;

  // Expose for settings
  window.GAIA_VOICE_OUTPUT = { stopSpeak, speakMessage, voicesFor };
})();