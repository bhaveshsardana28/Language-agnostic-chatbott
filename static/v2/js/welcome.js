import { reducedMotion } from './preferences.js';
import { animate, tokenTime } from './motion.js';

const greetings = [
  { text: 'Hello.', lang: 'en', script: 'Latin' },
  { text: 'नमस्ते.', lang: 'hi', script: 'Devanagari' },
  { text: 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ.', lang: 'pa', script: 'Gurmukhi' },
  { text: 'Hola.', lang: 'es', script: 'Latin' },
  { text: 'Bonjour.', lang: 'fr', script: 'Latin' },
  { text: 'Hallo.', lang: 'de', script: 'Latin' },
  { text: 'Ciao.', lang: 'it', script: 'Latin' },
];

export function initWelcome() {
  const greeting = document.getElementById('greeting');
  const script = document.getElementById('greeting-script');
  const pause = document.getElementById('greeting-pause');
  let index = 0, timer, epoch = 0, paused = false;
  const welcome = greeting.closest('.shell-welcome');
  const canRotate = () => !welcome?.hidden && !paused && !reducedMotion() && !document.hidden && !document.querySelector('dialog[open]');

  function schedule() {
    if (canRotate()) timer = setTimeout(advance, tokenTime('--greeting-interval'));
  }
  async function advance() {
    const owner = epoch;
    if (!canRotate()) return;
    await animate(greeting, [{ opacity: 1 }, { opacity: 0 }], '--motion-fast', '--ease-exit');
    if (owner !== epoch || !canRotate()) return;
    index = (index + 1) % greetings.length;
    greeting.textContent = greetings[index].text;
    greeting.lang = greetings[index].lang;
    script.textContent = greetings[index].script;
    await animate(greeting, [{ opacity: 0 }, { opacity: 1 }]);
    if (owner === epoch) schedule();
  }
  function sync() {
    epoch++;
    clearTimeout(timer);
    greeting.getAnimations().forEach(animation => animation.cancel());
    const stopped = paused || reducedMotion();
    pause.disabled = reducedMotion();
    pause.setAttribute('aria-pressed', String(stopped));
    const label = reducedMotion() ? 'Greeting rotation paused by reduced motion'
      : `${paused ? 'Resume' : 'Pause'} greeting rotation`;
    pause.setAttribute('aria-label', label);
    pause.title = label;
    pause.querySelector('use').setAttribute('href', stopped ? '#i-play' : '#i-pause');
    schedule();
  }
  pause.addEventListener('click', () => { paused = !paused; sync(); });
  document.addEventListener('visibilitychange', sync);
  document.addEventListener('preferenceschange', sync);
  const observer = new MutationObserver(sync);
  if (welcome) observer.observe(welcome, { attributes: true, attributeFilter: ['hidden'] });
  document.querySelectorAll('dialog').forEach(dialog => observer.observe(dialog, { attributes: true, attributeFilter: ['open'] }));
  window.addEventListener('pagehide', () => { epoch++; clearTimeout(timer); });
  window.addEventListener('pageshow', event => { if (event.persisted) sync(); });
  sync();
}
