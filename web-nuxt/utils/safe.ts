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

/** True if the string is an absolute http(s) URL (used to pick NuxtImg vs plain img). */
export function isRemoteUrl(url: string): boolean {
  return /^https?:\/\//.test(url)
}

/** Truncate text at a word boundary, appending '…' if trimmed. */
export function truncateText(text: string, max: number): string {
  if (!text || text.length <= max) return text || ''
  return text.slice(0, max).replace(/\s+\S*$/, '') + '…'
}

/** Generate and download an .ics calendar file for an entity with date attributes. */
export function downloadIcal(e: { id: string; name?: string; summary?: string; place_name?: string; attributes?: Record<string, any> }) {
  const attrs = e.attributes || {}
  const ds = String(attrs.date_start || '').replace(/-/g, '')
  if (!ds) return
  const de = String(attrs.date_end || attrs.date_start || '').replace(/-/g, '')
  const lines = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//vinhlong360.vn//VI',
    'BEGIN:VEVENT',
    `DTSTART;VALUE=DATE:${ds}`,
    `DTEND;VALUE=DATE:${de}`,
    `SUMMARY:${(e.name || '').replace(/[,;\\]/g, ' ')}`,
    `DESCRIPTION:${(e.summary || '').slice(0, 200).replace(/\n/g, '\\n')}`,
    `LOCATION:${(e.place_name || '').replace(/[,;\\]/g, ' ')}`,
    `URL:https://vinhlong360.vn/dia-diem/${e.id}`,
    'END:VEVENT', 'END:VCALENDAR',
  ]
  const blob = new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${e.id}.ics`
  a.click()
  URL.revokeObjectURL(url)
}

/** Build a dialable tel: href, stripping dots/spaces/parens (keeps leading +). */
export function telHref(phone?: string | null): string {
  if (!phone) return '#'
  const digits = String(phone).replace(/[^\d+]/g, '')
  return digits ? `tel:${digits}` : '#'
}
