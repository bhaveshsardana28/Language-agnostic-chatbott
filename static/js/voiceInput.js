/**
 * GAIA Voice Input — SpeechRecognition with waveform, states, interim transcript.
 * Browser-only, no audio stored.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;

  const BCP = { en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT' };
  const REC = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;

  const MIC_ERRORS = {
    'not-allowed': 'Microphone permission denied. Allow it in your browser site settings, then try again.',
    'service-not-allowed': 'Microphone blocked by browser/OS privacy settings. Enable it in system preferences.',
    'audio-capture': 'No microphone found. Connect one and try again.',
    'no-speech': 'No speech heard. Check the Speech language in Settings and try speaking again.',
    'network': 'Speech service network error. Check your connection and retry.'
  };

  let rec = null, recActive = false, audioCtx = null, analyser = null, source = null, rafId = null;
  let micBtn, inputEl, canvasEl, canvasCtx;

  function setMic(state) {
    recActive = state === 'listening';
    micBtn.classList.toggle('mic-btn--listen', state === 'listening');
    micBtn.classList.toggle('mic-btn--request', state === 'requesting');
    micBtn.setAttribute('aria-pressed', state !== 'idle');
    inputEl.placeholder = state === 'listening' ? 'Listening… speak now (Esc to stop)'
      : state === 'requesting' ? 'Requesting microphone…'
      : 'Ask anything in any supported language…';
    if (state === 'idle') autoGrow();
    updateWaveform(state === 'listening');
  }

  function autoGrow() { inputEl.style.height = 'auto'; inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px'; }

  function stopVoice() { if (rec && recActive) { try { rec.stop(); } catch (e) {} } updateWaveform(false); }

  function toggleVoice() {
    const R = REC(); if (!R) { chat.toast('Voice input not supported in this browser.'); return; }
    if (recActive) { stopVoice(); return; }
    chat.stopSpeak();
    rec = new R();
    rec.lang = store.get('speechLang') === 'auto' ? (BCP[store.get('lastLang')] || 'en-IN') : store.get('speechLang');
    rec.continuous = false; rec.interimResults = true;
    rec.onresult = e => {
      let interim = '', final = '';
      for (const r of e.results) (r.isFinal ? final += r[0].transcript : interim += r[0].transcript);
      inputEl.value = (final || interim).trim(); autoGrow();
    };
    rec.onerror = e => { chat.toast(MIC_ERRORS[e.error] || `Voice input failed (${e.error || 'unknown'}).`); };
    rec.onend = () => { setMic('idle'); if (inputEl.value.trim()) inputEl.focus(); };
    rec.onstart = () => { setMic('listening'); };
    try { rec.start(); setMic('requesting'); } catch (e) { chat.toast('Could not start microphone.'); setMic('idle'); }
  }

  // --- Waveform visualization ---
  async function updateWaveform(active) {
    if (active) {
      if (!canvasEl) initCanvas();
      if (!audioCtx) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          analyser = audioCtx.createAnalyser(); analyser.fftSize = 256; analyser.smoothingTimeConstant = 0.8;
          source = audioCtx.createMediaStreamSource(stream); source.connect(analyser);
        } catch { return; }
      }
      drawWaveform();
    } else {
      if (rafId) cancelAnimationFrame(rafId); rafId = null;
      if (source) { source.disconnect(); source = null; }
      if (audioCtx) { audioCtx.close(); audioCtx = null; analyser = null; }
      if (canvasCtx) canvasCtx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    }
  }

  function initCanvas() {
    canvasEl = document.getElementById('mic-waveform');
    if (!canvasEl) return;
    canvasCtx = canvasEl.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvasEl.width = canvasEl.offsetWidth * dpr;
    canvasEl.height = canvasEl.offsetHeight * dpr;
    canvasCtx.scale(dpr, dpr);
  }

  function drawWaveform() {
    if (!analyser || !canvasCtx) return;
    const bufferLength = analyser.frequencyBinCount;
    const data = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(data);
    const w = canvasEl.width / (window.devicePixelRatio || 1);
    const h = canvasEl.height / (window.devicePixelRatio || 1);
    canvasCtx.clearRect(0, 0, w, h);
    const barWidth = w / bufferLength * 2.5;
    let x = 0;
    for (let i = 0; i < bufferLength; i++) {
      const v = data[i] / 255;
      const barHeight = v * h * 0.8;
      canvasCtx.fillStyle = `rgba(239, 68, 68, ${0.3 + v * 0.7})`;
      canvasCtx.fillRect(x, h - barHeight, barWidth, barHeight);
      x += barWidth + 1;
    }
    rafId = requestAnimationFrame(drawWaveform);
  }

  // --- Init ---
  function init() {
    micBtn = document.getElementById('mic-btn');
    inputEl = document.getElementById('input');
    if (REC()) micBtn.addEventListener('click', toggleVoice);
    else { micBtn.disabled = true; micBtn.title = 'Voice input not supported (use Chrome or Safari)'; }

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') { if (recActive) { e.preventDefault(); stopVoice(); return; } }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'm') { e.preventDefault(); toggleVoice(); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();