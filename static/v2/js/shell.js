import { getPreferences, setPreferences } from './preferences.js';
import { openOverlay, closeOverlay, toast } from './ui.js';

export async function closeNavigation() {
  const drawer = document.getElementById('navigation-drawer');
  if (drawer?.open) await closeOverlay(drawer);
}

export function initShell() {
  const desktop = matchMedia('(min-width: 64rem)');
  const toggle = document.getElementById('sidebar-toggle');
  const collapse = document.getElementById('sidebar-collapse');
  const sidebar = document.getElementById('app-sidebar');
  const drawer = document.getElementById('navigation-drawer');
  const draft = document.getElementById('message-input');
  let lastFocused = document.activeElement;
  document.addEventListener('focusin', event => { lastFocused = event.target; });

  function syncToggle() {
    const expanded = desktop.matches ? !getPreferences().sideCollapsed : drawer.open;
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', desktop.matches ? `${expanded ? 'Collapse' : 'Expand'} sidebar` : 'Open navigation');
    toggle.setAttribute('aria-controls', desktop.matches ? 'app-sidebar' : 'navigation-drawer');
    toggle.querySelector('use').setAttribute('href', desktop.matches ? '#i-sidebar' : '#i-menu');
    if (collapse) {
      collapse.setAttribute('aria-expanded', String(expanded));
      collapse.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} sidebar`);
      collapse.title = `${expanded ? 'Collapse' : 'Expand'} sidebar`;
      collapse.querySelector('use').setAttribute('href', '#i-sidebar');
    }
  }
  function placeSidebar() {
    // CSS can hide the desktop sidebar before matchMedia's event, moving focus to body.
    const focused = document.activeElement === document.body ? lastFocused : document.activeElement;
    const hadFocus = sidebar.contains(focused) || drawer.contains(focused);
    if (drawer.open) {
      drawer.getAnimations().forEach(animation => animation.cancel());
      drawer.close();
    }
    document.getElementById(desktop.matches ? 'sidebar-dock' : 'mobile-sidebar-slot').append(sidebar);
    syncToggle();
    if (hadFocus) (desktop.matches ? collapse : toggle).focus({ preventScroll: true });
  }
  placeSidebar();
  desktop.addEventListener('change', placeSidebar);
  document.addEventListener('preferenceschange', syncToggle);
  drawer.addEventListener('close', syncToggle);
  toggle.addEventListener('click', () => {
    if (desktop.matches) {
      if (!setPreferences({ sideCollapsed: !getPreferences().sideCollapsed })) {
        toast('Sidebar changed for this visit. Browser storage is unavailable.');
      }
    } else {
      openOverlay('navigation-drawer', toggle);
      document.getElementById('new-chat').focus();
      syncToggle();
    }
  });
  collapse?.addEventListener('click', () => {
    if (!desktop.matches) return;
    if (!setPreferences({ sideCollapsed: !getPreferences().sideCollapsed })) {
      toast('Sidebar changed for this visit. Browser storage is unavailable.');
    }
  });

  document.querySelectorAll('[data-shell-open]').forEach(button => {
    button.addEventListener('click', async () => {
      const wasMobileNav = drawer.contains(button);
       await closeNavigation();
       openOverlay(button.dataset.shellOpen, wasMobileNav && !desktop.matches ? toggle : button);
       if (button.dataset.shellOpen === 'search-dialog') {
         requestAnimationFrame(() => document.getElementById('search-dialog-input')?.focus());
       }
    });
  });
  document.querySelectorAll('[data-new-chat]').forEach(button => {
    button.addEventListener('click', async () => {
      await closeNavigation();
      draft.value = '';
      resizeDraft();
      document.getElementById('conversation-heading').textContent = 'New conversation';
      document.getElementById('main-content').scrollTop = 0;
      draft.focus({ preventScroll: true });
      toast('A fresh draft. No server conversation was created.');
    });
  });
  function resizeDraft() {
    draft.style.height = 'auto';
    const computed = getComputedStyle(draft);
    draft.style.height = `${Math.min(draft.scrollHeight, parseFloat(computed.maxHeight))}px`;
  }
  draft.addEventListener('input', resizeDraft);
  window.addEventListener('resize', resizeDraft);
  document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {
   draft.value = button.dataset.prompt;
    draft.dispatchEvent(new Event('input', { bubbles: true }));
   resizeDraft();
    draft.focus({ preventScroll: true });
    draft.setSelectionRange(draft.value.length, draft.value.length);
  }));
  document.fonts.ready.then(resizeDraft);
}
