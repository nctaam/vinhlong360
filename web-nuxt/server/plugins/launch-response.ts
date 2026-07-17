import {
  getResponseHeaders,
  removeResponseHeader,
  setResponseHeader,
  type H3Event,
} from 'h3'
import { defineNitroPlugin } from 'nitropack/runtime/internal/plugin'

import { isRootSeoRequest } from '../middleware/launch-safety'
import {
  failedOpenLaunchDecision,
  writeLaunchResponseHeaders,
  type LaunchResponseHeaderInput,
} from '../utils/launch/launchHeaders'

function clearRobotsHeader(event: H3Event): void {
  for (const name of Object.keys(getResponseHeaders(event))) {
    if (name.toLowerCase() === 'x-robots-tag') removeResponseHeader(event, name)
  }
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

function shouldFinalizeLaunchResponse(event: H3Event): boolean {
  if (isRootSeoRequest(event)) return true

  // The response is authoritative whenever Nitro has selected an HTML type;
  // Accept/path heuristics must not hide a dotted 404 or JSON-preferring client.
  const contentType = responseContentType(event)
  if (contentType) return isHtmlContentType(contentType)

  // Error hooks can run before Nitro attaches Content-Type. Only an explicit
  // browser HTML request is safe to treat as HTML in that window; wildcard
  // Accept is common for assets and must remain unprotected.
  const accept = requestHeader(event, 'accept')
  return accept.includes('text/html') || accept.includes('application/xhtml+xml')
}

function isStoredInput(value: unknown): value is LaunchResponseHeaderInput {
  return value !== null
    && typeof value === 'object'
    && 'decision' in value
}

function finalHeaderInput(event: H3Event): LaunchResponseHeaderInput {
  const decision = event.context.launchSafety
  const stored = event.context.launchResponseHeaderInput
  if (isStoredInput(stored) && stored.decision === decision) return stored
  return { decision: decision ?? failedOpenLaunchDecision }
}

export function finalizeLaunchResponse(event: H3Event): void {
  try {
    const shouldFinalize = shouldFinalizeLaunchResponse(event)
    if (!shouldFinalize) {
      clearRobotsHeader(event)
      return
    }

    writeLaunchResponseHeaders(event, finalHeaderInput(event))
    clearRobotsHeader(event)
    if (!isRootSeoRequest(event)) {
      // Task 24 will refine eligible page robots; until then the global posture stays closed.
      setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')
    }
  } catch {
    // Response/error hooks must never leak stale evidence or throw into Nitro's lifecycle.
    try {
      writeLaunchResponseHeaders(event, { decision: failedOpenLaunchDecision })
      clearRobotsHeader(event)
      if (shouldFinalizeLaunchResponse(event) && !isRootSeoRequest(event)) {
        setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')
      }
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
