import { getPreferences, setPreferences, resetPreferences } from './preferences.js';
import { toast } from './ui.js';

export function initAppearance() {
  const toggle = document.getElementById('theme-toggle');
  function sync() {
    const preferences = getPreferences();
    document.querySelectorAll('input[name="theme"]').forEach(input => { input.checked = input.value === preferences.theme; });
    document.getElementById('reduce-motion').checked = preferences.reduceMotion;
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    toggle.setAttribute('aria-label', `Switch to ${next} theme`);
  }
  document.addEventListener('preferenceschange', sync);
  sync();
  toggle.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    if (!setPreferences({ theme: next })) toast('Theme changed for this visit. Browser storage is unavailable.');
  });
  document.querySelectorAll('input[name="theme"]').forEach(input => input.addEventListener('change', () => {
    if (!setPreferences({ theme: input.value })) toast('Theme changed for this visit. Browser storage is unavailable.');
  }));
  document.getElementById('reduce-motion').addEventListener('change', event => {
    if (!setPreferences({ reduceMotion: event.target.checked })) toast('Motion preference changed for this visit. Browser storage is unavailable.');
  });
  document.getElementById('reset-preferences').addEventListener('click', () => {
    const cleared = resetPreferences();
    toast(cleared ? 'Preview preferences reset. Your existing chats were not touched.'
      : 'Preferences reset for this visit. Browser storage could not be cleared.');
  });
}
