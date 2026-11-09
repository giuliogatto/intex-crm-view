/** Escape text for safe insertion into a print HTML document. */
export function escapeHtml(value) {
  if (value == null || value === '') return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function printCell(value, fallback = '—') {
  const text = value == null || value === '' ? fallback : String(value)
  return escapeHtml(text)
}

const PRINT_STYLES = `
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 11px;
    color: #111;
    margin: 16px;
    line-height: 1.35;
  }
  h1 {
    font-size: 16px;
    margin: 0 0 4px;
  }
  .meta {
    color: #444;
    margin: 0 0 14px;
    font-size: 10px;
  }
  .block {
    break-inside: avoid;
    page-break-inside: avoid;
    margin: 0 0 14px;
    border: 1px solid #ccc;
    padding: 8px 10px;
  }
  .block h2 {
    font-size: 12px;
    margin: 0 0 6px;
  }
  .kv {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 4px 12px;
    margin: 0 0 8px;
  }
  .kv div span {
    display: block;
    color: #666;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .kv div strong {
    font-weight: 600;
  }
  h3 {
    font-size: 11px;
    margin: 10px 0 4px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 2px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 4px;
  }
  th, td {
    border: 1px solid #ccc;
    padding: 3px 5px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background: #f0f0f0;
    font-weight: 600;
  }
  .muted { color: #666; }
  .compat {
    margin: 6px 0;
    padding: 6px 8px;
    background: #fafafa;
    border: 1px solid #e0e0e0;
  }
  .compat__head {
    font-weight: 600;
    margin-bottom: 4px;
  }
  .pct { font-variant-numeric: tabular-nums; }
  ul.plain {
    margin: 0;
    padding-left: 16px;
  }
  ol.fasi {
    margin: 0;
    padding-left: 18px;
  }
  .empty { color: #666; font-style: italic; }
  @media print {
    body { margin: 8mm; }
    .block, .compat { break-inside: avoid; page-break-inside: avoid; }
  }
`

/**
 * Print exploded content via a hidden iframe (no popup / about:blank window).
 * Leaves the interactive UI untouched.
 */
export function openPrintDocument({ title, meta = '', bodyHtml }) {
  const html = `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(title)}</title>
  <style>${PRINT_STYLES}</style>
</head>
<body>
  <h1>${escapeHtml(title)}</h1>
  ${meta ? `<p class="meta">${meta}</p>` : ''}
  ${bodyHtml}
</body>
</html>`

  const existing = document.getElementById('intex-print-frame')
  if (existing) existing.remove()

  const iframe = document.createElement('iframe')
  iframe.id = 'intex-print-frame'
  iframe.setAttribute('aria-hidden', 'true')
  iframe.style.cssText =
    'position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none;'
  document.body.appendChild(iframe)

  const win = iframe.contentWindow
  const doc = win?.document
  if (!win || !doc) {
    iframe.remove()
    throw new Error('Impossibile preparare la stampa in questo browser.')
  }

  doc.open()
  doc.write(html)
  doc.close()

  const cleanup = () => {
    setTimeout(() => {
      if (iframe.parentNode) iframe.remove()
    }, 1000)
  }

  const trigger = () => {
    try {
      win.focus()
      win.print()
    } catch (_) {
      /* ignore */
    } finally {
      cleanup()
    }
  }

  // Give the iframe a tick to layout before opening the print dialog.
  setTimeout(trigger, 100)
  return iframe
}
