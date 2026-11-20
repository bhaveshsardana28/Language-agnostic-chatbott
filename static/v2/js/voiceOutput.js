// User-initiated playback through an installed local voice.
import { plainText } from './markdown.js';
import { toast } from './ui.js';

let playing = null;

export function stopPlayback() {
  if (!playing) return;
  const { button } = playing;
  playing = null;
  button.textContent = 'Listen';
  button.setAttribute('aria-pressed', 'false');
  window.speechSynthesis.cancel();
}

export function addPlaybackButton(actions, message) {
  const synth = window.speechSynthesis;
  if (!synth || !window.SpeechSynthesisUtterance || !message.text || message.meta?.error) return;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'button button--quiet';
  button.textContent = 'Listen';
  button.setAttribute('aria-label', 'Read reply aloud');
  button.setAttribute('aria-pressed', 'false');
  button.addEventListener('click', () => {
    const wasPlaying = playing?.button === button;
    stopPlayback();
    if (wasPlaying) return;
    const lang = message.meta?.response_lang || message.meta?.language_meta?.language || 'en';
    const voice = synth.getVoices().find(v => v.localService && v.lang.split('-')[0] === lang);
    if (!voice) { toast('No local voice is available for this reply language.'); return; }
    const utterance = new SpeechSynthesisUtterance(plainText(message.text));
    utterance.voice = voice;
    utterance.lang = voice.lang;
    playing = { utterance, button };
    button.textContent = 'Stop reading';
    button.setAttribute('aria-pressed', 'true');
    const finish = () => {
      if (playing?.utterance !== utterance) return;
      playing = null;
      button.textContent = 'Listen';
      button.setAttribute('aria-pressed', 'false');
    };
    utterance.onend = finish;
    utterance.onerror = () => {
      if (playing?.utterance !== utterance) return;
      finish();
      toast('Playback stopped. Check the voice installed on this device.');
    };
    try { synth.speak(utterance); } catch { utterance.onerror(); }
  });
  actions.append(button);
}

document.addEventListener('v2conversationchange', stopPlayback);
document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlayback(); });
window.addEventListener('pagehide', stopPlayback);
