import { animate, springFrames, tokenNumber, tokenTime } from './motion.js';

const openers = new WeakMap();
const closing = new WeakSet();
let activeMenu = null;
let activeMenuButton = null;
let currentTooltip = null;
let tooltipTimer;

export function selectTab(tab, focus = false) {
  const list = tab.closest('[role="tablist"]');
  for (const item of list.querySelectorAll('[role="tab"]')) {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
  }
  if (focus) tab.focus();
  tab.dispatchEvent(new CustomEvent('tabchange', { bubbles: true }));
}

export function closeMenu(restoreFocus = true) {
  if (!activeMenu) return;
  activeMenu.hidden = true;
  activeMenuButton.setAttribute('aria-expanded', 'false');
  if (restoreFocus) activeMenuButton.focus();
  activeMenu = activeMenuButton = null;
}

function openMenu(button, last = false) {
  closeMenu(false);
  activeMenuButton = button;
  activeMenu = document.getElementById(button.getAttribute('aria-controls'));
  activeMenu.hidden = false;
  button.setAttribute('aria-expanded', 'true');
  const items = activeMenu.querySelectorAll('[role="menuitem"]:not(:disabled)');
  items[last ? items.length - 1 : 0].focus();
}

function hideTooltip() {
  clearTimeout(tooltipTimer);
  if (currentTooltip) currentTooltip.hidden = true;
  currentTooltip = null;
}

export function openOverlay(id, opener = document.activeElement) {
  const dialog = document.getElementById(id);
  if (!dialog || dialog.open) return;
  closeMenu(false);
  hideTooltip();
  openers.set(dialog, opener);
  dialog.showModal();
  if (dialog.classList.contains('drawer')) {
    animate(dialog, springFrames(), '--motion-panel', '--ease-linear');
  } else {
    const rise = tokenNumber('--motion-rise');
    const scale = tokenNumber('--dialog-start-scale');
    animate(dialog, [{ opacity: 0, transform: `translateY(${rise}px) scale(${scale})` },
      { opacity: 1, transform: 'translateY(0) scale(1)' }]);
  }
}

export async function closeOverlay(dialog) {
  if (!dialog?.open || closing.has(dialog)) return;
  closing.add(dialog);
  const transform = dialog.classList.contains('drawer') ? 'translateX(-100%)'
    : `translateY(${tokenNumber('--motion-rise')}px)`;
  await animate(dialog, [{ opacity: 1, transform: 'translate(0)' }, { opacity: 0, transform }],
    '--motion-fast', '--ease-exit');
  dialog.close();
  closing.delete(dialog);
  const opener = openers.get(dialog);
  if (opener?.isConnected && opener.getClientRects().length) opener.focus({ preventScroll: true });
}

export function toast(message) {
  const dialog = [...document.querySelectorAll('dialog[open]')].at(-1);
  let region = dialog ? dialog.querySelector('.toast-inline') : document.getElementById('toast-region');
  if (!region) {
    region = document.createElement('div');
    region.className = 'toast-inline';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    dialog.append(region);
  }
  const item = document.createElement('div');
  item.className = 'toast';
  const text = document.createElement('p');
  text.textContent = message;
  const dismiss = document.createElement('button');
  dismiss.type = 'button';
  dismiss.className = 'icon-button icon-button--quiet';
  dismiss.setAttribute('aria-label', 'Dismiss notification');
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.classList.add('icon');
  icon.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#i-close');
  icon.append(use);
  dismiss.append(icon);
  item.append(text, dismiss);
  region.append(item);
  let timer, removing = false;
  const remove = async () => {
    if (removing) return;
    removing = true;
    clearTimeout(timer);
    const hadFocus = item.contains(document.activeElement);
    await animate(item, [{ opacity: 1 }, { opacity: 0 }], '--motion-fast', '--ease-exit');
    item.remove();
    if (hadFocus) (dialog?.open ? dialog.querySelector('[data-close]') : document.getElementById('theme-toggle')).focus();
  };
  const schedule = () => { if (!removing) { clearTimeout(timer); timer = setTimeout(remove, tokenTime('--toast-duration')); } };
  item.addEventListener('pointerenter', () => clearTimeout(timer));
  item.addEventListener('pointerleave', () => { if (!item.contains(document.activeElement)) schedule(); });
  item.addEventListener('focusin', () => clearTimeout(timer));
  item.addEventListener('focusout', () => { if (!item.matches(':hover')) schedule(); });
  dismiss.addEventListener('click', remove);
  animate(item, [{ opacity: 0, transform: `translateY(${tokenNumber('--motion-rise')}px)` },
    { opacity: 1, transform: 'translateY(0)' }]);
  schedule();
}

export function initUI() {
  document.querySelectorAll('[data-tabs]').forEach(list => {
    list.addEventListener('click', event => {
      const tab = event.target.closest('[role="tab"]');
      if (tab) selectTab(tab);
    });
    list.addEventListener('keydown', event => {
      const tabs = [...list.querySelectorAll('[role="tab"]')];
      const index = tabs.indexOf(document.activeElement);
      if (index < 0) return;
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); selectTab(tabs[next], true); }
    });
  });

  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.addEventListener('cancel', event => { event.preventDefault(); closeOverlay(dialog); });
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll(
        'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
      )].filter(element => element.getClientRects().length);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom) closeOverlay(dialog);
    });
  });

  document.querySelectorAll('[aria-haspopup="menu"]').forEach(button => {
    button.addEventListener('click', () => {
      if (activeMenuButton === button) closeMenu(); else openMenu(button);
    });
    button.addEventListener('keydown', event => {
      if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
        event.preventDefault(); openMenu(button, event.key === 'ArrowUp');
      }
    });
  });

  document.querySelectorAll('[data-tooltip]').forEach(button => {
    const wrapper = button.closest('.tooltip');
    const tooltip = document.getElementById(button.dataset.tooltip);
    const show = () => {
      if (currentTooltip === tooltip) return;
      hideTooltip();
      tooltipTimer = setTimeout(() => {
        currentTooltip = tooltip;
        currentTooltip.hidden = false;
      }, tokenTime('--tooltip-delay'));
    };
    wrapper.addEventListener('pointerenter', show);
    wrapper.addEventListener('pointerleave', () => { if (document.activeElement !== button) hideTooltip(); });
    button.addEventListener('focus', show);
    button.addEventListener('blur', () => { if (!wrapper.matches(':hover')) hideTooltip(); });
  });

  document.addEventListener('pointerdown', event => {
    if (activeMenu && !event.target.closest('.menu-anchor')) closeMenu();
  });
  document.addEventListener('click', event => {
    const opener = event.target.closest('[data-open]');
    if (opener) openOverlay(opener.dataset.open, opener);
    const closer = event.target.closest('[data-close]');
    if (closer) closeOverlay(closer.closest('dialog'));
    if (event.target.closest('[role="menuitem"]')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented) return;
    if (event.key === 'Escape' && currentTooltip) { hideTooltip(); event.preventDefault(); return; }
    if (!activeMenu) return;
    const items = [...activeMenu.querySelectorAll('[role="menuitem"]:not(:disabled)')];
    const index = items.indexOf(document.activeElement);
    let next;
    if (event.key === 'ArrowDown') next = (index + 1) % items.length;
    if (event.key === 'ArrowUp') next = (index - 1 + items.length) % items.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = items.length - 1;
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
      const rotated = [...items.slice(index + 1), ...items.slice(0, index + 1)];
      const found = rotated.find(item => item.textContent.trim().toLowerCase().startsWith(event.key.toLowerCase()));
      if (found) { event.preventDefault(); found.focus(); }
    }
    if (next !== undefined) { event.preventDefault(); items[next].focus(); }
    if (event.key === 'Escape') { event.preventDefault(); closeMenu(); }
    if (event.key === 'Tab') closeMenu(false);
  });
}
