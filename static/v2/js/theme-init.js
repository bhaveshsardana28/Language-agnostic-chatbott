/* Deliberately synchronous, before CSS: resolve theme without a first-paint flash. */
(() => {
  let preferences = {};
  try {
    preferences = JSON.parse(localStorage.getItem('gaia.redesign.v2') || '{}') || {};
  } catch { /* Storage unavailable or malformed: use system defaults. */ }
  const theme = ['light', 'dark', 'system'].includes(preferences.theme) ? preferences.theme : 'system';
  document.documentElement.dataset.theme = theme === 'system'
    ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
  document.documentElement.dataset.motion = preferences.reduceMotion === true ||
    matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduced' : 'full';
  document.documentElement.dataset.sidebar = preferences.sideCollapsed === true ? 'collapsed' : 'expanded';
})();
