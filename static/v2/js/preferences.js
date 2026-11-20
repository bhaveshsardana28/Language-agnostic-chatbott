const KEY = 'gaia.redesign.v2';
export const SPEECH_LANGUAGES = ['auto', 'en-IN', 'hi-IN', 'pa-IN', 'es-ES', 'fr-FR', 'de-DE', 'it-IT'];
const colorQuery = matchMedia('(prefers-color-scheme: dark)');
const motionQuery = matchMedia('(prefers-reduced-motion: reduce)');

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
    return {
      theme: ['light', 'dark', 'system'].includes(saved.theme) ? saved.theme : 'dark',
      reduceMotion: saved.reduceMotion === true,
      sideCollapsed: saved.sideCollapsed === true,
      debug: saved.debug === true,
      speechLanguage: SPEECH_LANGUAGES.includes(saved.speechLanguage) ? saved.speechLanguage : 'auto',
    };
    } catch { return { theme: 'dark', reduceMotion: false, sideCollapsed: false, debug: false, speechLanguage: 'auto' }; }
}

let preferences = load();
export const getPreferences = () => ({ ...preferences });
export const reducedMotion = () => preferences.reduceMotion || motionQuery.matches;

function apply() {
  const resolvedTheme = preferences.theme === 'system'
    ? (colorQuery.matches ? 'dark' : 'light') : preferences.theme;
  document.documentElement.dataset.theme = resolvedTheme;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = resolvedTheme === 'dark' ? '#0E0E14' : '#F7F6F9';
  document.documentElement.dataset.motion = reducedMotion() ? 'reduced' : 'full';
  document.documentElement.dataset.sidebar = preferences.sideCollapsed ? 'collapsed' : 'expanded';
  document.documentElement.dataset.debug = preferences.debug ? 'true' : 'false';
  if (reducedMotion()) document.getAnimations().forEach(animation => animation.cancel());
  document.dispatchEvent(new CustomEvent('preferenceschange', { detail: getPreferences() }));
}

export function setPreferences(patch) {
  preferences = {
    theme: ['light', 'dark', 'system'].includes(patch.theme) ? patch.theme : preferences.theme,
    reduceMotion: typeof patch.reduceMotion === 'boolean' ? patch.reduceMotion : preferences.reduceMotion,
    sideCollapsed: typeof patch.sideCollapsed === 'boolean' ? patch.sideCollapsed : preferences.sideCollapsed,
    debug: typeof patch.debug === 'boolean' ? patch.debug : preferences.debug,
    speechLanguage: SPEECH_LANGUAGES.includes(patch.speechLanguage) ? patch.speechLanguage : preferences.speechLanguage,
  };
  let saved = true;
  try { localStorage.setItem(KEY, JSON.stringify(preferences)); } catch { saved = false; }
  apply();
  return saved;
}

export function resetPreferences() {
  preferences = { theme: 'dark', reduceMotion: false, sideCollapsed: false, debug: false, speechLanguage: 'auto' };
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
