import { defineEventHandler, sendRedirect, type H3Event } from 'h3'

import entityRedirects from '../../data/entity-redirects.json'

const REDIRECT_MAP: Record<string, string> = entityRedirects as Record<string, string>
const ENTITY_PATH_RE = /^\/dia-diem\/([^/]+)\/?$/

export function resolveEntityRedirect(rawUrl: string | undefined): string | null {
  if (!rawUrl) return null
  const qIndex = rawUrl.indexOf('?')
  const pathname = qIndex >= 0 ? rawUrl.slice(0, qIndex) : rawUrl
  const search = qIndex >= 0 ? rawUrl.slice(qIndex) : ''

  const match = ENTITY_PATH_RE.exec(pathname)
  const rawSlug = match?.[1]
  if (!rawSlug) return null

  let slug: string
  try {
    slug = decodeURIComponent(rawSlug)
  } catch {
    slug = rawSlug
  }

  const target = Object.prototype.hasOwnProperty.call(REDIRECT_MAP, slug)
    ? REDIRECT_MAP[slug]
    : undefined
  if (!target || target === slug) return null

  return `/dia-diem/${encodeURIComponent(target)}${search}`
}

export default defineEventHandler((event: H3Event) => {
  const method = (event.method || event.node?.req?.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') return

  const rawUrl = event.path || event.node?.req?.url
  const location = resolveEntityRedirect(rawUrl)
  if (location) {
    return sendRedirect(event, location, 301)
  }
})
