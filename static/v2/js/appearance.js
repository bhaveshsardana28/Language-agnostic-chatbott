import { getPreferences, setPreferences, resetPreferences } from './preferences.js';
import { toast } from './ui.js';

export function initAppearance() {
  const toggle = document.getElementById('theme-toggle');
  const reduceMotion = document.getElementById('reduce-motion');
  const showInsights = document.getElementById('show-insights');
  const speechLanguage = document.getElementById('speech-language');
  const reset = document.getElementById('reset-preferences');
  function sync() {
    const preferences = getPreferences();
    document.querySelectorAll('input[name="theme"]').forEach(input => { input.checked = input.value === preferences.theme; });
    if (reduceMotion) reduceMotion.checked = preferences.reduceMotion;
    if (showInsights) showInsights.checked = preferences.debug;
    if (speechLanguage) speechLanguage.value = preferences.speechLanguage;
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    if (toggle) toggle.setAttribute('aria-label', `Switch to ${next} theme`);
  }
  document.addEventListener('preferenceschange', sync);
  sync();
  toggle?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    if (!setPreferences({ theme: next })) toast('Theme changed for this visit. Browser storage is unavailable.');
  });
  document.querySelectorAll('input[name="theme"]').forEach(input => input.addEventListener('change', () => {
    if (!setPreferences({ theme: input.value })) toast('Theme changed for this visit. Browser storage is unavailable.');
  }));
  reduceMotion?.addEventListener('change', event => {
    if (!setPreferences({ reduceMotion: event.target.checked })) toast('Motion preference changed for this visit. Browser storage is unavailable.');
  });
  showInsights?.addEventListener('change', event => {
    if (!setPreferences({ debug: event.target.checked })) toast('Insights changed for this visit. Browser storage is unavailable.');
  });
  speechLanguage?.addEventListener('change', event => {
    if (!setPreferences({ speechLanguage: event.target.value })) toast('Speech language changed for this visit. Browser storage is unavailable.');
  });
  reset?.addEventListener('click', () => {
    const cleared = resetPreferences();
    toast(cleared ? 'Preview preferences reset. Your existing chats were not touched.'
      : 'Preferences reset for this visit. Browser storage could not be cleared.');
  });
}
