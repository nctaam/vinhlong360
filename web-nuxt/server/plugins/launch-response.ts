import { type H3Event } from 'h3'
import { defineNitroPlugin } from 'nitropack/runtime/internal/plugin'

import type { LaunchPageDecision, LaunchSafetyDecision } from '../../types/launch'
import {
  isKnownNonHtmlRequest,
  isLaunchSafetyCandidate,
  isRootSeoRequest,
} from '../middleware/launch-safety'
import {
  clearLaunchResponseHeaders,
  failedOpenLaunchDecision,
  writeLaunchResponseHeaders,
  type LaunchResponseHeaderInput,
} from '../utils/launch/launchHeaders'
import { pageDecisionFromBase } from '../utils/launch/entityPolicy'

const LAUNCH_STATE_PAYLOAD_KEY = '$slaunch-safety-page-decision'
const LAUNCH_PAGE_FIELDS = [
  'operational_state',
  'indexing_posture',
  'policy_fingerprint',
  'route_manifest_revision',
  'backend_policy_revision',
  'sitemap_batch_revision',
  'sitemap_action',
  'reason',
  'robots',
  'sitemapDiscovery',
] as const

interface LaunchResponseBody {
  body?: unknown
}

function findTagEnd(source: string, start: number): number {
  let quote = ''
  for (let index = start; index < source.length; index += 1) {
    const character = source[index]
    if (quote) {
      if (character === quote) quote = ''
    } else if (character === '"' || character === "'") {
      quote = character
    } else if (character === '>') {
      return index
    }
  }
  return -1
}

function tagAttributes(tag: string): Record<string, string> {
  const attributes: Record<string, string> = {}
  let index = /^<\s*[a-z0-9:-]+/iu.exec(tag)?.[0].length ?? 0
  while (index < tag.length) {
    while (/\s/u.test(tag[index] ?? '')) index += 1
    if (tag[index] === '>' || tag[index] === '/') break

    const nameStart = index
    while (index < tag.length && !/[\s=/>]/u.test(tag[index]!)) index += 1
    const name = tag.slice(nameStart, index).toLowerCase()
    if (!name) {
      index += 1
      continue
    }
    while (/\s/u.test(tag[index] ?? '')) index += 1
    let value = ''
    if (tag[index] === '=') {
      index += 1
      while (/\s/u.test(tag[index] ?? '')) index += 1
      const quote = tag[index]
      if (quote === '"' || quote === "'") {
        index += 1
        const valueStart = index
        while (index < tag.length && tag[index] !== quote) index += 1
        value = tag.slice(valueStart, index)
        index += 1
      } else {
        const valueStart = index
        while (index < tag.length && !/[\s>]/u.test(tag[index]!)) index += 1
        value = tag.slice(valueStart, index)
      }
    }
    attributes[name] = value
  }
  return attributes
}

function robotsMetaRanges(head: string): Array<[number, number]> {
  const ranges: Array<[number, number]> = []
  let cursor = 0
  while (cursor < head.length) {
    const open = head.indexOf('<', cursor)
    if (open < 0) break
    if (head.startsWith('<!--', open)) {
      const commentEnd = head.indexOf('-->', open + 4)
      cursor = commentEnd < 0 ? head.length : commentEnd + 3
      continue
    }
    const end = findTagEnd(head, open + 1)
    if (end < 0) break
    const tag = head.slice(open, end + 1)
    const name = /^<\s*([a-z0-9:-]+)/iu.exec(tag)?.[1]?.toLowerCase()
    if (name === 'script' || name === 'style' || name === 'noscript' || name === 'template') {
      const close = new RegExp(`<\\/${name}\\s*>`, 'iu').exec(head.slice(end + 1))
      cursor = close ? end + 1 + close.index + close[0].length : head.length
      continue
    }
    if (name === 'meta' && (tagAttributes(tag).name ?? '').toLowerCase() === 'robots') {
      ranges.push([open, end + 1])
    }
    cursor = end + 1
  }
  return ranges
}

function headCloseIndex(body: string, start: number): number {
  let cursor = start
  while (cursor < body.length) {
    const open = body.indexOf('<', cursor)
    if (open < 0) return -1
    if (body.startsWith('<!--', open)) {
      const commentEnd = body.indexOf('-->', open + 4)
      cursor = commentEnd < 0 ? body.length : commentEnd + 3
      continue
    }
    const end = findTagEnd(body, open + 1)
    if (end < 0) return -1
    const tag = body.slice(open, end + 1)
    const closingName = /^<\s*\/\s*([a-z0-9:-]+)/iu.exec(tag)?.[1]?.toLowerCase()
    if (closingName === 'head') return open

    const name = /^<\s*([a-z0-9:-]+)/iu.exec(tag)?.[1]?.toLowerCase()
    if (name === 'script' || name === 'style' || name === 'noscript' || name === 'template') {
      const close = new RegExp(`<\\/${name}\\s*>`, 'iu').exec(body.slice(end + 1))
      cursor = close ? end + 1 + close.index + close[0].length : body.length
      continue
    }
    cursor = end + 1
  }
  return -1
}

function replaceRobotsMeta(body: string, robots: LaunchPageDecision['robots']): string {
  const headOpen = /<head(?:\s[^>]*)?>/iu.exec(body)
  if (!headOpen) return body

  const headStart = headOpen.index + headOpen[0].length
  const headEnd = headCloseIndex(body, headStart)
  if (headEnd < headStart) return body
  const head = body.slice(headStart, headEnd)
  const ranges = robotsMetaRanges(head)
  const replacement = `<meta name="robots" content="${robots}">`
  if (ranges.length === 0) return `${body.slice(0, headEnd)}${replacement}${body.slice(headEnd)}`

  let output = ''
  let cursor = 0
  ranges.forEach(([start, end], index) => {
    output += head.slice(cursor, start)
    if (index === 0) output += replacement
    cursor = end
  })
  output += head.slice(cursor)
  return `${body.slice(0, headStart)}${output}${body.slice(headEnd)}`
}

function payloadObject(values: unknown[], reference: unknown): Record<string, unknown> | null {
  if (typeof reference !== 'number' || !Number.isInteger(reference)) return null
  let index = reference
  if (index < 0 || index >= values.length) return null
  let value = values[index]
  const seen = new Set<number>()
  while (Array.isArray(value) && typeof value[0] === 'string' && Number.isInteger(value[1])) {
    if (seen.has(index)) return null
    seen.add(index)
    index = value[1] as number
    value = values[index]
  }
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function payloadReference(values: unknown[], value: unknown): number {
  const existing = values.findIndex(candidate => Object.is(candidate, value))
  if (existing >= 0) return existing
  values.push(value)
  return values.length - 1
}

function nuxtPayloadRange(body: string): { start: number, end: number } | null {
  let cursor = 0
  while (cursor < body.length) {
    const open = body.indexOf('<', cursor)
    if (open < 0) return null
    if (body.startsWith('<!--', open)) {
      const commentEnd = body.indexOf('-->', open + 4)
      cursor = commentEnd < 0 ? body.length : commentEnd + 3
      continue
    }
    const tagEnd = findTagEnd(body, open + 1)
    if (tagEnd < 0) return null
    const tag = body.slice(open, tagEnd + 1)
    const name = /^<\s*([a-z0-9:-]+)/iu.exec(tag)?.[1]?.toLowerCase()
    if (name !== 'script') {
      cursor = tagEnd + 1
      continue
    }

    const close = /<\/script\s*>/iu.exec(body.slice(tagEnd + 1))
    if (!close) return null
    const contentStart = tagEnd + 1
    const contentEnd = contentStart + close.index
    const attributes = tagAttributes(tag)
    if (
      attributes.id === '__NUXT_DATA__'
      && (attributes.type ?? '').toLowerCase() === 'application/json'
    ) {
      return { start: contentStart, end: contentEnd }
    }
    cursor = contentEnd + close[0].length
  }
  return null
}

function replaceLaunchPayload(body: string, decision: Readonly<LaunchPageDecision>): string {
  const range = nuxtPayloadRange(body)
  if (!range) return body
  const payload = body.slice(range.start, range.end)
  let values: unknown[]
  try {
    const parsed = JSON.parse(payload) as unknown
    if (!Array.isArray(parsed) || parsed.length === 0) return body
    values = parsed
  } catch {
    return body
  }

  const root = payloadObject(values, 0)
  const state = root ? payloadObject(values, root.state) : null
  const page = state ? payloadObject(values, state[LAUNCH_STATE_PAYLOAD_KEY]) : null
  if (!page || LAUNCH_PAGE_FIELDS.some(field => !Object.hasOwn(page, field))) return body

  for (const field of LAUNCH_PAGE_FIELDS) page[field] = payloadReference(values, decision[field])
  const serialized = JSON.stringify(values).replaceAll('/', '\\u002F')
  return `${body.slice(0, range.start)}${serialized}${body.slice(range.end)}`
}

function synchronizeLaunchHtmlBody(body: string, decision: Readonly<LaunchPageDecision>): string {
  return replaceRobotsMeta(replaceLaunchPayload(body, decision), decision.robots)
}

function responseContentType(event: H3Event): string {
  const header = event.node.res.getHeader('content-type')
  if (Array.isArray(header)) return header.join(',').toLowerCase()
  return typeof header === 'string' ? header.toLowerCase() : ''
}

function requestHeader(event: H3Event, name: string): string {
  const headers = event.node.req.headers ?? {}
  const expected = name.toLowerCase()
  for (const [candidate, value] of Object.entries(headers)) {
    if (candidate.toLowerCase() !== expected) continue
    if (Array.isArray(value)) return value.join(',').toLowerCase()
    return typeof value === 'string' ? value.toLowerCase() : ''
  }
  return ''
}

function isHtmlContentType(contentType: string): boolean {
  return contentType.includes('text/html') || contentType.includes('application/xhtml+xml')
}

function responseStatus(event: H3Event): number {
  const status = event.node.res.statusCode
  return Number.isInteger(status) ? status : 200
}

function shouldFinalizeLaunchResponse(event: H3Event): boolean {
  if (isRootSeoRequest(event)) return true

  // The response is authoritative whenever Nitro has selected an HTML type;
  // Accept/path heuristics must not hide a dotted 404 or JSON-preferring client.
  const contentType = responseContentType(event)
  if (contentType) {
    if (!isHtmlContentType(contentType)) return false
    return event.context.launchSafety !== undefined || !isKnownNonHtmlRequest(event)
  }

  if (isKnownNonHtmlRequest(event)) return false

  // Middleware already attested this request. Preserve that request-local
  // decision for wildcard browser requests only while response type is absent.
  if (event.context.launchSafety !== undefined) return true

  if (responseStatus(event) < 400) return isLaunchSafetyCandidate(event)

  // Error hooks can run before Nitro attaches Content-Type. Only an explicit
  // browser HTML request is safe to treat as HTML in that window. Known APIs,
  // framework assets, and manifest-sensitive paths were excluded above.
  const accept = requestHeader(event, 'accept')
  return accept.includes('text/html') || accept.includes('application/xhtml+xml')
}

function isStoredInput(value: unknown): value is LaunchResponseHeaderInput {
  return value !== null
    && typeof value === 'object'
    && 'decision' in value
}

function isPageDecision(value: unknown): value is Readonly<LaunchPageDecision> {
  return value !== null
    && typeof value === 'object'
    && 'robots' in value
    && 'sitemapDiscovery' in value
}

function finalHtmlDecision(event: H3Event): Readonly<LaunchPageDecision> {
  const contextual = event.context.launchSafety
  const decision = isPageDecision(contextual)
    ? contextual
    : pageDecisionFromBase((contextual as Readonly<LaunchSafetyDecision> | undefined) ?? failedOpenLaunchDecision)

  if (responseStatus(event) < 400 || decision.robots === 'noindex, follow') {
    event.context.launchSafety = decision
    return decision
  }

  const noindexDecision = Object.freeze({ ...decision, robots: 'noindex, follow' as const })
  event.context.launchSafety = noindexDecision
  return noindexDecision
}

function finalHeaderInput(event: H3Event, html: boolean): LaunchResponseHeaderInput {
  const decision = html
    ? finalHtmlDecision(event)
    : (event.context.launchSafety as Readonly<LaunchSafetyDecision> | undefined) ?? failedOpenLaunchDecision
  const stored = event.context.launchResponseHeaderInput
  if (isStoredInput(stored) && stored.decision === decision) return { ...stored, html }
  return { decision, html }
}

export function finalizeLaunchResponse(event: H3Event, response?: LaunchResponseBody): void {
  let shouldFinalize = false
  let html = false
  try {
    shouldFinalize = shouldFinalizeLaunchResponse(event)
    if (!shouldFinalize) {
      clearLaunchResponseHeaders(event)
      return
    }

    html = !isRootSeoRequest(event)
    writeLaunchResponseHeaders(event, finalHeaderInput(event, html))
    if (html && typeof response?.body === 'string') {
      response.body = synchronizeLaunchHtmlBody(
        response.body,
        event.context.launchSafety as Readonly<LaunchPageDecision>,
      )
    }
  } catch {
    // Response/error hooks must never leak stale evidence or throw into Nitro's lifecycle.
    try {
      if (!shouldFinalize && !shouldFinalizeLaunchResponse(event)) {
        clearLaunchResponseHeaders(event)
        return
      }
      html = html || !isRootSeoRequest(event)
      const decision = html
        ? pageDecisionFromBase(failedOpenLaunchDecision)
        : failedOpenLaunchDecision
      if (html) event.context.launchSafety = decision
      writeLaunchResponseHeaders(event, { decision, html })
    } catch {
      // A destroyed response cannot be repaired; the hook still remains non-throwing.
    }
  }
}

export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('beforeResponse', (event, response) => {
    finalizeLaunchResponse(event, response)
  })
  nitroApp.hooks.hook('error', (_error, context) => {
    if (context.event) finalizeLaunchResponse(context.event)
  })
})
