// Shared safety helpers (auto-imported by Nuxt from utils/).
// P0-16/17/3: sanitize URLs, HTML, and tel: links before they reach href/innerHTML.

/** Allow only http(s) URLs into an href; anything else (javascript:, data:, …) → '#'. */
export function safeUrl(url?: string | null): string {
  if (!url) return '#'
  const u = String(url).trim()
  return /^https?:\/\//i.test(u) ? u : '#'
}

/** Escape a string for safe interpolation into innerHTML / setHTML (map popups, etc.). */
export function escapeHtml(s?: string | null): string {
  if (s == null) return ''
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string
  ))
}

/** Build a dialable tel: href, stripping dots/spaces/parens (keeps leading +). */
export function telHref(phone?: string | null): string {
  if (!phone) return '#'
  const digits = String(phone).replace(/[^\d+]/g, '')
  return digits ? `tel:${digits}` : '#'
}
