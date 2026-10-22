// Small escape-first Markdown renderer for assistant replies.
// It intentionally supports the audited display subset; unknown syntax remains text.
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

function inline(value) {
  let text = escapeHtml(value);
  const links = [];
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
    const index = links.push(`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`) - 1;
    return `\u0000LINK${index}\u0000`;
  });
  text = text.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  text = text.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
  text = text.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  text = text.replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');
  return text.replace(/\u0000LINK(\d+)\u0000/g, (_, index) => links[index]);
}

function codeBlock(language, content, index) {
  const label = language ? `<span class="code-language">${escapeHtml(language)}</span>` : '';
  return `<div class="code-block"><div class="code-head">${label}<button class="button button--quiet code-copy" type="button" data-code-index="${index}" aria-label="Copy code block">Copy</button></div><pre><code>${escapeHtml(content)}</code></pre></div>`;
}

export function renderMarkdown(source) {
  const lines = String(source ?? '').replace(/\r\n?/g, '\n').split('\n');
  const output = [];
  let paragraph = [], list = null, quote = [], table = null, code = null, codeIndex = 0;
  const flushParagraph = () => { if (paragraph.length) { output.push(`<p>${inline(paragraph.join(' '))}</p>`); paragraph = []; } };
  const flushList = () => { if (!list) return; output.push(`<${list.type}>${list.items.map(item => `<li>${inline(item)}</li>`).join('')}</${list.type}>`); list = null; };
  const flushQuote = () => { if (quote.length) { output.push(`<blockquote>${quote.map(item => `<p>${inline(item)}</p>`).join('')}</blockquote>`); quote = []; } };
  const flushTable = () => {
    if (!table) return;
    const [header, ...rows] = table;
    output.push(`<div class="table-wrap"><table><thead><tr>${header.map(cell => `<th scope="col">${inline(cell)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${inline(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
    table = null;
  };
  const flushAll = () => { flushParagraph(); flushList(); flushQuote(); flushTable(); };
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (code) {
      if (/^\s*```/.test(line)) { output.push(codeBlock(code.language, code.lines.join('\n'), codeIndex)); codeIndex += 1; code = null; }
      else code.lines.push(line);
      continue;
    }
    const fence = line.match(/^\s*```\s*([\w+-]*)\s*$/);
    if (fence) { flushAll(); code = { language: fence[1], lines: [] }; continue; }
    if (/^\s*$/.test(line)) { flushAll(); continue; }
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) { flushAll(); output.push('<hr>'); continue; }
    const heading = line.match(/^\s*(#{1,3})\s+(.+?)\s*#*$/);
    if (heading) { flushAll(); const level = heading[1].length; output.push(`<h${level}>${inline(heading[2])}</h${level}>`); continue; }
    if (/^\s*>/.test(line)) { flushParagraph(); flushList(); flushTable(); quote.push(line.replace(/^\s*>\s?/, '')); continue; }
    const listItem = line.match(/^\s*([-*+] |\d+[.)] )(.+)$/);
    if (listItem) { flushParagraph(); flushQuote(); flushTable(); const type = /^\d/.test(listItem[1]) ? 'ol' : 'ul'; if (!list || list.type !== type) { flushList(); list = { type, items: [] }; } list.items.push(listItem[2]); continue; }
    if (line.includes('|') && line.trim().startsWith('|')) {
      const cells = line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
      if (cells.every(cell => /^:?-{3,}:?$/.test(cell))) continue;
      flushParagraph(); flushList(); flushQuote(); if (!table) table = []; table.push(cells); continue;
    }
    flushList(); flushQuote(); flushTable(); paragraph.push(line.trim());
  }
  if (code) output.push(codeBlock(code.language, code.lines.join('\n'), codeIndex));
  flushAll();
  return output.join('');
}

export function plainText(source) {
  const container = document.createElement('div');
  container.innerHTML = renderMarkdown(source);
  return container.innerText;
}
