import { type H3Event } from 'h3'
import { defineNitroPlugin } from 'nitropack/runtime/internal/plugin'

import type { LaunchPageDecision, LaunchSafetyDecision } from '../../types/launch'
import {
  isKnownNonHtmlRequest,
  isLaunchSafetyCandidate,
  isRootSeoRequest,
} from '../middleware/launch-safety'
import {
  failedOpenLaunchDecision,
  writeLaunchResponseHeaders,
  type LaunchResponseHeaderInput,
} from '../utils/launch/launchHeaders'
import { pageDecisionFromBase } from '../utils/launch/entityPolicy'

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

export function finalizeLaunchResponse(event: H3Event): void {
  let shouldFinalize = false
  let html = false
  try {
    shouldFinalize = shouldFinalizeLaunchResponse(event)
    if (!shouldFinalize) return

    html = !isRootSeoRequest(event)
    writeLaunchResponseHeaders(event, finalHeaderInput(event, html))
  } catch {
    // Response/error hooks must never leak stale evidence or throw into Nitro's lifecycle.
    try {
      if (!shouldFinalize && !shouldFinalizeLaunchResponse(event)) return
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
  nitroApp.hooks.hook('beforeResponse', (event) => {
    finalizeLaunchResponse(event)
  })
  nitroApp.hooks.hook('error', (_error, context) => {
    if (context.event) finalizeLaunchResponse(context.event)
  })
})
