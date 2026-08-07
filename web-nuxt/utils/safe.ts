// Shared safety helpers (auto-imported by Nuxt from utils/).
// P0-16/17/3: sanitize URLs, HTML, and tel: links before they reach href/innerHTML.

import { entityPath } from './routePaths'

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

/** Get the area slug from an entity (place_area or area field). */
export function getEntityArea(e: { place_area?: string; area?: string }): string {
  return e.place_area || e.area || ''
}

// ── iCalendar (.ics) generation ──
// One implementation for every .ics we emit (entity button + the su-kien/le-hoi bulk
// buttons). Keep it here: three copies of this drifted apart once already.

/** An event ready for ICS output. `dateEnd` is the INCLUSIVE last day, the way our data stores it. */
export interface IcsEventInput {
  id: string
  name?: string
  summary?: string
  place_name?: string
  /** Inclusive first day — `YYYY-MM-DD` (also accepts `YYYYMMDD` or a full ISO timestamp). */
  dateStart: string
  /** Inclusive last day; empty/absent means a single-day event. */
  dateEnd?: string | null
}

/**
 * Parse a calendar date into UTC midnight, or null when it is not a real day.
 * Overflow inputs (`2026-02-30`, `2027-02-29`) are rejected rather than silently rolled
 * into the next month, so bad data can never shift an event to a wrong date.
 */
function parseCalendarDate(value?: string | null): Date | null {
  const m = /^(\d{4})-?(\d{2})-?(\d{2})/.exec(String(value ?? '').trim())
  if (!m) return null
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const dt = new Date(Date.UTC(y, mo - 1, d))
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null
  return dt
}

/** UTC date → the compact `YYYYMMDD` form iCalendar wants for VALUE=DATE. */
function formatCalendarDate(d: Date): string {
  return String(d.getUTCFullYear()).padStart(4, '0')
    + String(d.getUTCMonth() + 1).padStart(2, '0')
    + String(d.getUTCDate()).padStart(2, '0')
}

/**
 * DTEND for an all-day VEVENT, in compact `YYYYMMDD`.
 *
 * RFC 5545 §3.6.1: a DATE-valued DTEND is NON-INCLUSIVE and "MUST be greater than" DTSTART.
 * Our data stores an inclusive last day, so the exclusive end is always (last day + 1) — for a
 * one-day event too. Emitting DTEND == DTSTART produces a zero-length event that Google
 * Calendar and Outlook drop or draw wrong.
 *
 * @param dateStart          inclusive first day
 * @param dateEndInclusive   inclusive last day; empty/unparseable → treated as a single-day event
 * @returns compact exclusive end date, or '' when `dateStart` itself is not a real date
 */
export function icsAllDayEnd(dateStart: string, dateEndInclusive?: string | null): string {
  const start = parseCalendarDate(dateStart)
  if (!start) return ''
  const end = parseCalendarDate(dateEndInclusive) || start
  // Bad data (end before start) collapses to one day instead of an inverted range.
  const last = end.getTime() < start.getTime() ? start : end
  return formatCalendarDate(new Date(last.getTime() + 86_400_000))
}

/** Strip the characters that would break ICS line structure (RFC 5545 delimiters). */
function icsEscape(s?: string | null): string {
  return String(s || '').replace(/[,;\\]/g, ' ')
}

/** Build a complete VCALENDAR document; entries without a usable start date are skipped. */
export function buildIcsCalendar(items: IcsEventInput[]): string {
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//vinhlong360.vn//VI']
  for (const e of items || []) {
    const start = parseCalendarDate(e?.dateStart)
    if (!start) continue
    lines.push(
      'BEGIN:VEVENT',
      `DTSTART;VALUE=DATE:${formatCalendarDate(start)}`,
      `DTEND;VALUE=DATE:${icsAllDayEnd(e.dateStart, e.dateEnd)}`,
      `SUMMARY:${icsEscape(e.name)}`,
      `DESCRIPTION:${icsEscape((e.summary || '').slice(0, 200)).replace(/\r?\n/g, '\\n')}`,
      `LOCATION:${icsEscape(e.place_name)}`,
      `URL:https://vinhlong360.vn${entityPath(e.id)}`,
      'END:VEVENT',
    )
  }
  lines.push('END:VCALENDAR')
  return lines.join('\r\n')
}

/** Download a multi-event .ics; no-op when nothing has a usable date. */
export function downloadIcsBundle(items: IcsEventInput[], filename: string) {
  const usable = (items || []).filter(i => parseCalendarDate(i?.dateStart))
  if (!usable.length) return
  downloadBlob(new Blob([buildIcsCalendar(usable)], { type: 'text/calendar;charset=utf-8' }), filename)
}

/** Generate and download an .ics calendar file for an entity with date attributes. */
export function downloadIcal(e: { id: string; name?: string; summary?: string; place_name?: string; attributes?: Record<string, any> }) {
  const attrs = e.attributes || {}
  downloadIcsBundle([{
    id: e.id,
    name: e.name,
    summary: e.summary,
    place_name: e.place_name,
    dateStart: String(attrs.date_start || ''),
    dateEnd: String(attrs.date_end || ''),
  }], `${e.id}.ics`)
}

// ── Event date helpers (shared by le-hoi + su-kien pages) ──

interface EventLike { attributes?: Record<string, any>; season?: { months?: number[] } }

export function getDateStart(e: EventLike): Date | null {
  const ds = e.attributes?.date_start
  if (!ds) return null
  const d = new Date(ds + 'T00:00:00')
  return isNaN(d.getTime()) ? null : d
}

export function formatEventMonth(e: EventLike): string {
  const d = getDateStart(e)
  if (!d) {
    const months = e.season?.months
    if (months?.length) return `T${months[0]}`
    return ''
  }
  return `Tg ${d.getMonth() + 1}`
}

export function formatEventDay(e: EventLike): string {
  const d = getDateStart(e)
  if (!d) return '—'
  return String(d.getDate())
}

export function eventDateRange(e: EventLike): string {
  const attrs = e.attributes || {}
  const ds = attrs.date_start
  if (!ds) return ''
  const de = attrs.date_end || ds
  const fmt = (s: string) => {
    const d = new Date(s + 'T00:00:00')
    if (isNaN(d.getTime())) return ''
    return `${d.getDate()}/${d.getMonth() + 1}`
  }
  if (ds === de) return fmt(ds)
  const f1 = fmt(ds)
  const f2 = fmt(de)
  return (f1 && f2) ? `${f1} – ${f2}` : f1
}

/** Format an ISO date string to Vietnamese locale (dd/mm/yyyy). */
export function formatDateVN(d?: string | null): string {
  if (!d) return ''
  return new Date(d).toLocaleDateString('vi-VN')
}

/** Trigger a file download from a Blob (used by admin CSV/JSON export and iCal). */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Navigate back if history exists, otherwise go to a fallback path. */
export function goBackOr(fallback: string) {
  if (import.meta.client && window.history.length > 1) {
    useRouter().back()
  } else {
    navigateTo(fallback)
  }
}

/** Emoji icon for a user reputation level (1–4). */
export function levelIcon(level: number): string {
  return (['', '🌱', '🤝', '🌟', '👑'][level]) || '🌱'
}

/** Build a dialable tel: href, stripping dots/spaces/parens (keeps leading +). */
export function telHref(phone?: string | null): string {
  if (!phone) return '#'
  const digits = String(phone).replace(/[^\d+]/g, '')
  return digits ? `tel:${digits}` : '#'
}

/** Escape content then linkify @-mentions and #hashtags for safe v-html rendering. */
export function linkifyContent(content: string, mentions?: Array<{ label?: string; id?: string; type?: string }>): string {
  let html = escapeHtml(content)
  if (Array.isArray(mentions) && mentions.length) {
    const sorted = [...mentions].sort((a, b) => (b?.label?.length || 0) - (a?.label?.length || 0))
    for (const m of sorted) {
      if (!m?.label || !m?.id || (m.type !== 'user' && m.type !== 'entity')) continue
      const href = m.type === 'user'
        ? `/nguoi-dung/${encodeURIComponent(m.id)}`
        : `/dia-diem/${encodeURIComponent(m.id)}`
      const token = '@' + escapeHtml(m.label)
      html = html.split(token).join(`<a class="mention-link" href="${href}">${token}</a>`)
    }
  }
  // \p{L}\p{N} (Unicode) để khớp hashtag tiếng Việt (#đặcsản) như backend _extract_hashtags
  // (Python \w+UNICODE). JS \w LUÔN chỉ [A-Za-z0-9_] kể cả cờ u → phải dùng property escape.
  html = html.replace(/#([\p{L}\p{N}_]{1,30})/gu, (_m, tag) =>
    `<a class="hashtag-link" href="/cong-dong?tag=${encodeURIComponent(tag.toLowerCase())}">#${tag}</a>`)
  return html
}
