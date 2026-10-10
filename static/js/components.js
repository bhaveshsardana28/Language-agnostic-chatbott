/**
 * GAIA Components — Button, Dialog, Toast, Skeleton, Avatar
 * Reusable UI primitives built on design tokens.
 */
(function () {
  'use strict';

  // --- Button Component ---
  function createButton({ variant = 'primary', size = 'md', icon, label, disabled, onClick, ariaLabel, type = 'button', className = '' }) {
    const btn = document.createElement('button');
    btn.type = type;
    btn.className = `btn btn--${variant} btn--${size} ${className}`;
    if (disabled) btn.disabled = true;
    if (ariaLabel) btn.setAttribute('aria-label', ariaLabel);
    if (onClick) btn.addEventListener('click', onClick);
    if (icon) { btn.innerHTML = icon; if (!label) btn.classList.add('btn--icon'); }
    if (label) btn.appendChild(document.createTextNode(label));
    return btn;
  }

  // --- Icon Button ---
  function createIconButton({ icon, label, disabled, onClick, pressed, size = 'md', className = '' }) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `icon-btn ${className}`;
    if (disabled) btn.disabled = true;
    if (pressed !== undefined) btn.setAttribute('aria-pressed', pressed);
    if (label) btn.setAttribute('aria-label', label);
    if (onClick) btn.addEventListener('click', onClick);
    btn.innerHTML = icon;
    return btn;
  }

  // --- Dialog Component ---
  function createDialog({ title, body, footer, onClose, closeOnEscape = true, closeOnOverlay = true }) {
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    overlay.innerHTML = `<div class="dialog" role="dialog" aria-modal="true" aria-labelledby="dlg-title">
      <header class="dialog__header"><h2 id="dlg-title" class="dialog__title">${title}</h2></header>
      <div class="dialog__body">${body}</div>
      ${footer ? `<footer class="dialog__footer">${footer}</footer>` : ''}
    </div>`;
    const dialog = overlay.querySelector('.dialog');

    function close() {
      overlay.classList.remove('open');
      setTimeout(() => overlay.remove(), 200);
      if (onClose) onClose();
    }

    // Animate in
    requestAnimationFrame(() => overlay.classList.add('open'));

    // Escape
    if (closeOnEscape) {
      const escFn = e => { if (e.key === 'Escape') { document.removeEventListener('keydown', escFn); close(); } };
      document.addEventListener('keydown', escFn);
      overlay._escFn = escFn;
    }

    // Overlay click
    if (closeOnOverlay) {
      overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    }

    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'icon-btn dialog__close';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6 6 18"/></svg>`;
    closeBtn.addEventListener('click', close);
    dialog.querySelector('.dialog__header').appendChild(closeBtn);

    document.body.appendChild(overlay);
    return { element: overlay, dialog, close };
  }

  // --- Confirm Dialog ---
  function confirmDialog({ title, message, confirmText = 'Confirm', cancelText = 'Cancel', variant = 'danger', onConfirm, onCancel }) {
    const dlg = createDialog({
      title,
      body: `<p>${message}</p>`,
      footer: `<button class="btn btn--ghost" data-cancel>${cancelText}</button><button class="btn btn--${variant}" data-confirm>${confirmText}</button>`,
      onClose: onCancel
    });
    dlg.dialog.querySelector('[data-confirm]').addEventListener('click', () => { dlg.close(); if (onConfirm) onConfirm(); });
    dlg.dialog.querySelector('[data-cancel]').addEventListener('click', () => dlg.close());
    return dlg;
  }

  // --- Toast Component ---
  let toastContainer = null;
  function getToastContainer() {
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.className = 'toast-container';
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }
  function showToast(message, duration = 3000) {
    const container = getToastContainer();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.classList.add('removing'); toast.addEventListener('animationend', () => toast.remove(), { once: true }); }, duration);
    return toast;
  }

  // --- Skeleton Component ---
  function createSkeleton({ variant = 'text', width, height, className = '' }) {
    const el = document.createElement('div');
    el.className = `skeleton skeleton--${variant} ${className}`;
    if (width) el.style.width = width;
    if (height) el.style.height = height;
    return el;
  }

  // --- Avatar Component ---
  function createAvatar({ src, alt, name, size = 'md', className = '' }) {
    const el = document.createElement('div');
    el.className = `avatar avatar--${size} ${className}`;
    if (src) {
      const img = document.createElement('img');
      img.src = src; img.alt = alt || '';
      el.appendChild(img);
    } else if (name) {
      el.textContent = name.charAt(0).toUpperCase();
    }
    return el;
  }

  // Expose
  window.GAIA_COMPONENTS = {
    createButton, createIconButton, createDialog, confirmDialog, showToast, createSkeleton, createAvatar
  };
})();