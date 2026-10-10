/**
 * GAIA Voice Mode — Full-screen orb with Listen → Think → Speak loop.
 * Animated orb driven by real audio levels via Web Audio AnalyserNode.
 */
(function () {
  'use strict';

  const store = window.GAIA_STORE;
  const chat = window.GAIA_CHAT;

  const BCP = { en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT' };
  const NATIVE = { en: 'English', hi: 'हिन्दी', pa: 'ਪੰਜਾਬੀ', es: 'Español', fr: 'Français', de: 'Deutsch', it: 'Italiano' };
  const REC = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const MIC_ERRORS = {
    'not-allowed': 'Microphone permission denied. Allow it in browser site settings.',
    'service-not-allowed': 'Microphone blocked by browser/OS privacy settings.',
    'audio-capture': 'No microphone found.',
    'no-speech': 'No speech heard. Check Speech language in Settings.',
    'network': 'Speech service network error.'
  };

  let vmEl, vmOrb, vmLabel, vmTranscript, vmEq, vmCloseBtn, vmEndBtn;
  let vmRec = null, vmActive = false, vmPhase = 'idle', vmFinalText = '', vmInterimText = '';
  let vmAudioCtx = null, vmAnalyser = null, vmSource = null, vmRafId = null;

  function vmSetPhase(p) {
    vmPhase = p;
    vmOrb.classList.remove('voice-orb--idle', 'voice-orb--listen', 'voice-orb--think', 'voice-orb--speak');
    vmOrb.classList.add(`voice-orb--${p}`);
    vmEq.style.display = (p === 'listen' || p === 'speak') ? 'flex' : 'none';
    const labels = { idle: 'Tap to start', listening: 'Listening…', thinking: 'Thinking…', speaking: 'Speaking…' };
    vmLabel.textContent = labels[p] || labels.idle;
  }

  function vmOpen() {
    chat.stopSpeak();
    if (window.GAIA_VOICE_INPUT) { /* stop voice input if active */ }
    vmEl.hidden = false; vmEl.classList.add('show');
    vmSetPhase('idle'); vmFinalText = ''; vmInterimText = ''; vmTranscript.innerHTML = '';
    vmCloseBtn.focus();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || store.get('noMotion')) {
      vmOrb.style.animation = 'none';
    }
  }

  function vmClose() {
    if (vmRec) { try { vmRec.stop(); } catch (e) {} vmRec = null; }
    stopAudio();
    vmEl.classList.remove('show'); vmEl.hidden = true; vmActive = false; vmSetPhase('idle');
  }

  async function startAudio() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      vmAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      vmAnalyser = vmAudioCtx.createAnalyser(); vmAnalyser.fftSize = 256; vmAnalyser.smoothingTimeConstant = 0.8;
      vmSource = vmAudioCtx.createMediaStreamSource(stream); vmSource.connect(vmAnalyser);
      drawOrbEq();
    } catch { /* ignore */ }
  }

  function stopAudio() {
    if (vmRafId) cancelAnimationFrame(vmRafId); vmRafId = null;
    if (vmSource) { vmSource.disconnect(); vmSource = null; }
    if (vmAudioCtx) { vmAudioCtx.close(); vmAudioCtx = null; vmAnalyser = null; }
  }

  function drawOrbEq() {
    if (!vmAnalyser) return;
    const data = new Uint8Array(vmAnalyser.frequencyBinCount);
    vmAnalyser.getByteFrequencyData(data);
    const bars = vmEq.querySelectorAll('.voice-orb__eq-bar');
    bars.forEach((bar, i) => {
      const idx = Math.floor(i * data.length / bars.length);
      const v = data[idx] / 255;
      bar.style.height = `${Math.max(4, v * 36)}px`;
    });
    vmRafId = requestAnimationFrame(drawOrbEq);
  }

  function vmStart() {
    const R = REC(); if (!R) { chat.toast('Voice input not supported.'); return; }
    vmRec = new R();
    vmRec.lang = store.get('speechLang') === 'auto' ? (BCP[store.get('lastLang')] || 'en-IN') : store.get('speechLang');
    vmRec.continuous = true; vmRec.interimResults = true;
    vmRec.onresult = e => {
      vmInterimText = '';
      for (const r of e.results) {
        if (r.isFinal) vmFinalText += r[0].transcript + ' ';
        else vmInterimText += r[0].transcript;
      }
      vmTranscript.innerHTML = window.esc(vmFinalText) + (vmInterimText ? `<span style="color:var(--accent)">${window.esc(vmInterimText)}</span>` : '');
      vmTranscript.scrollTop = vmTranscript.scrollHeight;
    };
    vmRec.onerror = e => {
      const msg = MIC_ERRORS[e.error] || `Voice error: ${e.error || 'unknown'}`;
      chat.toast(msg);
      if (e.error === 'no-speech') vmSetPhase('idle'); else vmClose();
    };
    vmRec.onend = () => { if (vmActive) vmRec.start(); };
    vmActive = true; vmSetPhase('listening');
    startAudio();
    try { vmRec.start(); } catch (e) { chat.toast('Could not start microphone.'); vmClose(); }
  }

  function vmSend() {
    if (!vmFinalText.trim()) { vmSetPhase('idle'); return; }
    vmSetPhase('thinking');
    const text = vmFinalText.trim(); vmFinalText = ''; vmInterimText = ''; vmTranscript.innerHTML = '';
    if (vmRec) { try { vmRec.stop(); } catch (e) {} vmRec = null; stopAudio(); }
    chat.send(text).then(() => {
      const c = store.current; const last = c?.messages[c.messages.length - 1];
      if (last && last.role === 'assistant') {
        vmSetPhase('speaking'); chat.speakMessage(last);
        setTimeout(() => vmSetPhase('idle'), 30000);
      } else { vmSetPhase('idle'); }
    }).catch(() => vmSetPhase('idle'));
  }

  function init() {
    vmEl = document.getElementById('voice-mode');
    vmOrb = document.getElementById('vm-orb');
    vmLabel = document.getElementById('vm-label');
    vmTranscript = document.getElementById('vm-transcript');
    vmEq = document.getElementById('vm-eq');
    vmCloseBtn = document.getElementById('vm-close');
    vmEndBtn = document.getElementById('vm-end');

    document.getElementById('voice-mode-btn').addEventListener('click', vmOpen);
    vmCloseBtn.addEventListener('click', vmClose);
    vmEndBtn.addEventListener('click', vmClose);
    vmOrb.addEventListener('click', () => {
      if (vmPhase === 'idle' || vmPhase === 'listening') vmStart();
      else if (vmPhase === 'speaking') vmClose();
    });

    document.addEventListener('keydown', e => {
      if (vmEl.classList.contains('show')) {
        if (e.key === 'Escape') { e.preventDefault(); vmClose(); }
        if (e.key === ' ' && (vmPhase === 'idle' || vmPhase === 'listening')) { e.preventDefault(); vmStart(); }
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();