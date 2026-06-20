// B5 — minimal, XSS-safe markdown renderer for admin-editable rich text
// (legal pages, etc.). Strategy: escape ALL HTML first, THEN emit only a fixed
// whitelist of tags (<p>, <br>, <strong>, <ul>/<li>, <a> with a validated
// href). Because the source is fully escaped before any tag is injected, an
// admin cannot inject <script>, event handlers, or arbitrary attributes — the
// only HTML in the output is what this function produces.
//
// Supported syntax:
//   **bold**                  → <strong>
//   - item (lines)            → <ul><li>
//   [text](/path or https://) → <a> (other URL schemes render as plain text)
//   blank line                → new paragraph; single newline → <br>

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// url is already HTML-escaped. Allow only internal ("/...") or http(s) links.
function safeHref(url: string): string | null {
  if (/^\/[^\s"'<>]*$/.test(url)) return url
  if (/^https?:\/\/[^\s"'<>]+$/.test(url)) return url
  return null
}

function inline(escaped: string): string {
  let out = escaped
  // [text](url) — both captured from already-escaped text
  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, text, url) => {
    const href = safeHref(url)
    if (!href) return m
    const ext = /^https?:/.test(href)
    const attrs = ext ? ' target="_blank" rel="noopener nofollow"' : ''
    return `<a href="${href}"${attrs}>${text}</a>`
  })
  // **bold**
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  return out
}

export function mdLite(src: unknown): string {
  if (!src || typeof src !== 'string') return ''
  const escaped = escapeHtml(src)
  const blocks = escaped.split(/\n\s*\n/)
  const html: string[] = []
  for (const block of blocks) {
    if (!block.trim()) continue
    const lines = block.split('\n')
    const isList = lines.length > 0 && lines.every(l => /^\s*-\s+/.test(l))
    if (isList) {
      const items = lines.map(l => `<li>${inline(l.replace(/^\s*-\s+/, ''))}</li>`).join('')
      html.push(`<ul>${items}</ul>`)
    } else {
      html.push(`<p>${inline(block.replace(/\n/g, '<br>'))}</p>`)
    }
  }
  return html.join('')
}
