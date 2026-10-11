const KEY = 'gaia.redesign.v2';
const colorQuery = matchMedia('(prefers-color-scheme: dark)');
const motionQuery = matchMedia('(prefers-reduced-motion: reduce)');

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
    return {
      theme: ['light', 'dark', 'system'].includes(saved.theme) ? saved.theme : 'system',
      reduceMotion: saved.reduceMotion === true,
    };
  } catch { return { theme: 'system', reduceMotion: false }; }
}

let preferences = load();
export const getPreferences = () => ({ ...preferences });
export const reducedMotion = () => preferences.reduceMotion || motionQuery.matches;

function apply() {
  document.documentElement.dataset.theme = preferences.theme === 'system'
    ? (colorQuery.matches ? 'dark' : 'light') : preferences.theme;
  document.documentElement.dataset.motion = reducedMotion() ? 'reduced' : 'full';
  if (reducedMotion()) document.getAnimations().forEach(animation => animation.cancel());
  document.dispatchEvent(new CustomEvent('preferenceschange', { detail: getPreferences() }));
}

export function setPreferences(patch) {
  preferences = {
    theme: ['light', 'dark', 'system'].includes(patch.theme) ? patch.theme : preferences.theme,
    reduceMotion: typeof patch.reduceMotion === 'boolean' ? patch.reduceMotion : preferences.reduceMotion,
  };
  let saved = true;
  try { localStorage.setItem(KEY, JSON.stringify(preferences)); } catch { saved = false; }
  apply();
  return saved;
}

export function resetPreferences() {
  preferences = { theme: 'system', reduceMotion: false };
  let cleared = true;
  try { localStorage.removeItem(KEY); } catch { cleared = false; }
  apply();
  return cleared;
}

colorQuery.addEventListener('change', apply);
motionQuery.addEventListener('change', apply);
document.addEventListener('visibilitychange', () => {
  document.documentElement.dataset.visibility = document.hidden ? 'hidden' : 'visible';
});
apply();
