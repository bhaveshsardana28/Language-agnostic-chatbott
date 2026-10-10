/**
 * GAIA Markdown Renderer — escape-first, XSS-safe by construction.
 * Zero dependencies. Handles: headings, lists, tables, blockquotes,
 * links, inline code, fenced code blocks with language + copy.
 */
// Export immediately for synchronous availability
const ESC_MAP = { '&': '&#38;', '<': '&#60;', '>': '&#62;', '"': '&#34;', "'": '&apos;' };
function esc(s) { return String(s).replace(/[&<>"']/g, c => ESC_MAP[c]); }
window.esc = esc;

// --- Syntax highlighting (token colors only) ---
const KEYWORDS = {
  python: 'def return if elif else for while import from class try except with as pass not in is None True False lambda print',
  javascript: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false',
  js: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false',
  bash: 'if then else fi for while do done echo export cd sudo',
  sh: 'if then else fi for while do done echo export cd sudo',
  typescript: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false interface type',
  json: 'true false null',
  html: 'div span class id style script',
  css: 'color background margin padding border display flex grid'
};

function highlight(code, lang) {
  const kws = KEYWORDS[(lang || '').toLowerCase()];
  if (!kws) return code;

  const parts = [];

  // --- Syntax highlighting (token colors only) ---
  const KEYWORDS = {
    python: 'def return if elif else for while import from class try except with as pass not in is None True False lambda print',
    javascript: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false',
    js: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false',
    bash: 'if then else fi for while do done echo export cd sudo',
    sh: 'if then else fi for while do done echo export cd sudo',
    typescript: 'function return if else for while const let var class import export new async await try catch typeof null undefined true false interface type',
    json: 'true false null',
    html: 'div span class id style script',
    css: 'color background margin padding border display flex grid'
  };

  function highlight(code, lang) {
    const kws = KEYWORDS[(lang || '').toLowerCase()];
    if (!kws) return code;

    const parts = [];
    // Extract strings and comments FIRST so keywords inside them aren't highlighted
    code = code.replace(/("([^"\\]|\\.)*"|'([^'\\]|\\.)*'|`[^`]*`)|((?<!&)#[^\n]*|\/\/[^\n]*)/g,
      (m) => { parts.push(m); return `\x00H${parts.length - 1}\x00`; });

    const re = new RegExp('\\b(' + kws.trim().split(/\s+/).join('|') + ')\\b', 'g');
    code = code.replace(re, '<span class="tok-k">$1</span>');

    // Restore strings/comments with appropriate classes
    code = code.replace(/\x00H(\d+)\x00/g, (m, i) => {
      const part = parts[i];
      const cls = (part.startsWith('#') || part.startsWith('//')) ? 'tok-c' : 'tok-s';
      return `<span class="${cls}">${part}</span>`;
    });

    return code;
  }

  // --- Main markdown function ---
  function md(src) {
    const blocks = [];
    // Extract fenced code blocks first
    src = String(src).replace(/```([\w+-]*)\n?([\s\S]*?)(?:```|$)/g, (m, lang, code) => {
      blocks.push({ lang: lang || 'text', code });
      return `\x00B${blocks.length - 1}\x00`;
    });

    let html = esc(src);

    // Inline replacements
    const inline = s => s
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
      .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<i>$2</i>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    const lines = html.split(/\n/);
    const out = [];
    let list = null, table = null, para = [];

    const flushP = () => { if (para.length) { out.push('<p>' + inline(para.join('<br>')) + '</p>'); para = []; } };
    const flushL = () => { if (list) { out.push(`<${list.t}>` + list.items.map(i => '<li>' + inline(i) + '</li>').join('') + `</${list.t}>`); list = null; } };
    const flushT = () => {
      if (table && table.rows.length) {
        out.push('<div class="tblwrap"><table>' +
          '<tr>' + table.head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr>' +
          table.rows.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') +
          '</table></div>');
      }
      table = null;
    };

    for (let ln of lines) {
      // Standalone code block placeholder -> block level
      const bm = ln.match(/^\x00B(\d+)\x00\s*$/);
      if (bm) { flushP(); flushL(); flushT(); out.push(codeBlockHtml(blocks, +bm[1])); continue; }

      if (/^\s*$/.test(ln)) { flushP(); flushL(); flushT(); continue; }

      const hm = ln.match(/^(#{1,3})\s+(.*)/);
      if (hm) { flushP(); flushL(); flushT(); out.push(`<h${hm[1].length}>${inline(hm[2])}</h${hm[1].length}>`); continue; }

      if (/^\s*(---|\*\*\*)\s*$/.test(ln)) { flushP(); flushL(); flushT(); out.push('<hr>'); continue; }

      const qm = ln.match(/^>\s?(.*)/);
      if (qm) { flushP(); flushL(); flushT(); out.push('<blockquote>' + inline(qm[1]) + '</blockquote>'); continue; }

      const um = ln.match(/^\s*[-*•]\s+(.*)/);
      if (um) { flushP(); flushT(); if (!list || list.t !== 'ul') flushL(), list = { t: 'ul', items: [] }; list.items.push(um[1]); continue; }

      const om = ln.match(/^\s*\d+[.)]\s+(.*)/);
      if (om) { flushP(); flushT(); if (!list || list.t !== 'ol') flushL(), list = { t: 'ol', items: [] }; list.items.push(om[1]); continue; }

      const cells = ln.split('|').map(c => c.trim());
      if (cells.length >= 2 && ln.trim().startsWith('|')) {
        flushP(); flushL();
        if (/^\s*:?-{2,}:?\s*$/.test(cells[1]) && table) continue; // header separator row
        if (!table) { table = { head: cells.filter(c => c !== ''), rows: [] }; continue; }
        table.rows.push(cells.filter(c => c !== '')); continue;
      }

      flushL(); flushT(); para.push(ln);
    }
    flushP(); flushL(); flushT();

    // Safety net: any remaining inline placeholders
    return out.join('').replace(/\x00B(\d+)\x00/g, (m, i) => codeBlockHtml(blocks, +i));
  }

  function codeBlockHtml(blocks, i) {
    const b = blocks[i];
    return `<div class="code-block" data-cb="${i}"><div class="code-block__header"><span class="code-block__lang">${esc(b.lang)}</span><button class="code-block__copy" type="button" data-copy="${i}">Copy</button></div><pre><code>${highlight(esc(b.code.replace(/\n$/,'')), b.lang)}</code></pre></div>`;
  }

  // --- Copy handler (delegated) ---
  function initCopyHandler() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('.code-block__copy');
      if (!btn) return;
      const idx = +btn.dataset.copy;
      const blk = document.querySelector(`.code-block[data-cb="${idx}"]`);
      if (!blk) return;
      const code = blk.querySelector('code').textContent;
      navigator.clipboard?.writeText(code).catch(() => {
        const ta = document.createElement('textarea'); ta.value = code;
        document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
      });
      btn.textContent = 'Copied';
      setTimeout(() => btn.textContent = 'Copy', 1200);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initCopyHandler);
  else initCopyHandler();

// --- Speech text cleanup (markdown -> plain text for TTS) ---
function speechText(raw) {
  let t = raw
    .replace(/```[\s\S]*?```/g, ' Code block skipped. ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_>#|]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return t;
}
window.speechText = speechText;

// Expose md globally as well
function md(src) {
  const blocks = [];
  src = String(src).replace(/```([\w+-]*)\n?([\s\S]*?)(?:```|$)/g, (m, lang, code) => {
    blocks.push({ lang: lang || 'text', code });
    return `\x00B${blocks.length - 1}\x00`;
  });

  let html = esc(src);

  const inline = s => s
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  const lines = html.split(/\n/); const out = []; let list = null, table = null, para = [];
  const flushP = () => { if (para.length) { out.push('<p>' + inline(para.join('<br>')) + '</p>'); para = []; } };
  const flushL = () => { if (list) { out.push(`<${list.t}>` + list.items.map(i => '<li>' + inline(i) + '</li>').join('') + `</${list.t}>`); list = null; } };
  const flushT = () => { if (table && table.rows.length) { out.push('<div class="tblwrap"><table>' + '<tr>' + table.head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr>' + table.rows.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') + '</table></div>'); } table = null; };
  for (let ln of lines) {
    const bm = ln.match(/^\x00B(\d+)\x00\s*$/);
    if (bm) { flushP(); flushL(); flushT(); out.push(codeBlockHtml(blocks, +bm[1])); continue; }
    if (/^\s*$/.test(ln)) { flushP(); flushL(); flushT(); continue; }
    const hm = ln.match(/^(#{1,3})\s+(.*)/);
    if (hm) { flushP(); flushL(); flushT(); out.push(`<h${hm[1].length}>${inline(hm[2])}</h${hm[1].length}>`); continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(ln)) { flushP(); flushL(); flushT(); out.push('<hr>'); continue; }
    const qm = ln.match(/^>\s?(.*)/);
    if (qm) { flushP(); flushL(); flushT(); out.push('<blockquote>' + inline(qm[1]) + '</blockquote>'); continue; }
    const um = ln.match(/^\s*[-*•]\s+(.*)/);
    if (um) { flushP(); flushT(); if (!list || list.t !== 'ul') flushL(), list = { t: 'ul', items: [] }; list.items.push(um[1]); continue; }
    const om = ln.match(/^\s*\d+[.)]\s+(.*)/);
    if (om) { flushP(); flushT(); if (!list || list.t !== 'ol') flushL(), list = { t: 'ol', items: [] }; list.items.push(om[1]); continue; }
    const cells = ln.split('|').map(c => c.trim());
    if (cells.length >= 2 && ln.trim().startsWith('|')) {
      flushP(); flushL();
      if (/^\s*:?-{2,}:?\s*$/.test(cells[1]) && table) continue;
      if (!table) { table = { head: cells.filter(c => c !== ''), rows: [] }; continue; }
      table.rows.push(cells.filter(c => c !== '')); continue;
    }
    flushL(); flushT(); para.push(ln);
  }
  flushP(); flushL(); flushT();
  return out.join('').replace(/\x00B(\d+)\x00/g, (m, i) => codeBlockHtml(blocks, +i));
}
window.md = md;

function codeBlockHtml(blocks, i) {
  const b = blocks[i];
  return `<div class="code-block" data-cb="${i}"><div class="code-block__header"><span class="code-block__lang">${esc(b.lang)}</span><button class="code-block__copy" type="button" data-copy="${i}">Copy</button></div><pre><code>${highlight(esc(b.code.replace(/\n$/,'')), b.lang)}</code></pre></div>`;
}

// --- Copy handler (delegated) ---
function initCopyHandler() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.code-block__copy');
    if (!btn) return;
    const idx = +btn.dataset.copy;
    const blk = document.querySelector(`.code-block[data-cb="${idx}"]`);
    if (!blk) return;
    const code = blk.querySelector('code').textContent;
    navigator.clipboard?.writeText(code).catch(() => {
      const ta = document.createElement('textarea'); ta.value = code;
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
    });
    btn.textContent = 'Copied';
    setTimeout(() => btn.textContent = 'Copy', 1200);
  });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initCopyHandler);
else initCopyHandler();