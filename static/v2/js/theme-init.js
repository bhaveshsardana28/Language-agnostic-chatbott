/* Deliberately synchronous, before CSS: resolve theme without a first-paint flash. */
(() => {
  let preferences = {};
  try {
    preferences = JSON.parse(localStorage.getItem('gaia.redesign.v2') || '{}') || {};
  } catch { /* Storage unavailable or malformed: use system defaults. */ }
  const theme = ['light', 'dark', 'system'].includes(preferences.theme) ? preferences.theme : 'dark';
  document.documentElement.dataset.theme = theme === 'system'
    ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = document.documentElement.dataset.theme === 'dark' ? '#0E0E14' : '#F7F6F9';
  document.documentElement.dataset.motion = preferences.reduceMotion === true ||
    matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduced' : 'full';
  document.documentElement.dataset.sidebar = preferences.sideCollapsed === true ? 'collapsed' : 'expanded';
})();
