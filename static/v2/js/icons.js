// Original trusted static artwork shared by both pages. Never interpolate user content.
export function initIcons() {
  document.body.insertAdjacentHTML('afterbegin', `
  <svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" hidden>
     <symbol id="i-gaia" viewBox="0 0 32 32"><path d="M22 6h-7a7 7 0 1 0 7 7V6m0 7v11c0 5-10 6-14 2M15 6h11"/></symbol>
     <symbol id="i-polyglot" viewBox="0 0 32 32"><path d="M5 9h10a6 6 0 0 1 0 12H5M27 23H17a6 6 0 0 1 0-12h10"/><path d="M11 9v12m10-10v12"/></symbol>
    <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
    <symbol id="i-chat" viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4zM8 9h8m-8 3h5"/></symbol>
    <symbol id="i-voice" viewBox="0 0 24 24"><path d="M4 9v6m4-10v14m4-12v10m4-13v16m4-11v6"/></symbol>
    <symbol id="i-settings" viewBox="0 0 24 24"><path d="M4 6h5m4 0h7M4 12h11m4 0h1M4 18h3m4 0h9"/><circle cx="11" cy="6" r="2"/><circle cx="17" cy="12" r="2"/><circle cx="9" cy="18" r="2"/></symbol>
    <symbol id="i-theme" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 4v16m0-16a8 8 0 0 1 0 16"/></symbol>
    <symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></symbol>
    <symbol id="i-more" viewBox="0 0 24 24"><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></symbol>
    <symbol id="i-close" viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18"/></symbol>
    <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M6 18 18 6M6 6h12v12"/></symbol>
    <symbol id="i-switch" viewBox="0 0 24 24"><path d="M4 8h15m-4-4 4 4-4 4M20 16H5m4-4-4 4 4 4"/></symbol>
    <symbol id="i-copy" viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/></symbol>
    <symbol id="i-refresh" viewBox="0 0 24 24"><path d="M20 9a8 8 0 1 0 0 6M20 3v6h-6"/></symbol>
    <symbol id="i-file" viewBox="0 0 24 24"><path d="M14 3H5v18h14V8zM14 3v5h5M9 13h6m-6 4h6"/></symbol>
    <symbol id="i-send" viewBox="0 0 24 24"><path d="M12 20V4M5 11l7-7 7 7"/></symbol>
    <symbol id="i-sound" viewBox="0 0 24 24"><path d="m11 5-5 4H3v6h3l5 4zM16 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></symbol>
    <symbol id="i-sidebar" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></symbol>
    <symbol id="i-pause" viewBox="0 0 24 24"><path d="M9 5v14M15 5v14"/></symbol>
    <symbol id="i-play" viewBox="0 0 24 24"><path d="m8 4 12 8-12 8z"/></symbol>
    <symbol id="empty-chat" viewBox="0 0 168 168"><g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M24 29h91v69H60l-22 19V98H24z"/><path d="M69 69h73v58h-17v15l-20-15H69z"/><path d="M42 49h38m-38 14h55m-12 23h37m-37 14h26"/><circle cx="119" cy="28" r="9"/><path d="M119 24v8m-4-4h8"/></g></symbol>
    <symbol id="empty-docs" viewBox="0 0 168 168"><g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M42 19h57l26 27v101H42zM99 19v27h26M29 41H19v102h10M60 70h47M60 87h47M60 104h31"/><circle cx="115" cy="124" r="21"/><path d="M105 124h20m-10-10v20"/></g></symbol>
  </svg>`);
}
