import {
  defineEventHandler,
  getRequestURL,
  setResponseHeader,
  setResponseStatus,
  type H3Event,
} from 'h3'

import type { LaunchSafetyDecision } from '../../../types/launch'
import {
  createInternalSitemapFetcher,
  proxyGuardedSitemap,
  type RootSitemapDocument,
} from './guardedSitemapProxy'
import {
  buildBaseLaunchResponseHeaders,
  failedOpenLaunchDecision,
  writeLaunchResponseHeaders,
} from './launchHeaders'
import { launchRouteManifest } from './launchRouteManifest'

export const XML_CONTENT_TYPE = 'application/xml; charset=utf-8'
export const ROBOTS_CONTENT_TYPE = 'text/plain; charset=utf-8'
export const EMPTY_URLSET = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
export const EMPTY_MEDIA_URLSET = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>'
export const EMPTY_SITEMAP_INDEX = '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'

const ROBOT_AGENTS = Object.freeze([
  '*',
  'Googlebot',
  'GPTBot',
  'ClaudeBot',
  'PerplexityBot',
  'Google-Extended',
] as const)
const CANONICAL_SITEMAP = `${launchRouteManifest.canonical_origin}/sitemap-index.xml`
const CLOSED_SITEMAP_BODIES: Readonly<Record<RootSitemapDocument, string>> = Object.freeze({
  'sitemap.xml': EMPTY_URLSET,
  'sitemap-media.xml': EMPTY_MEDIA_URLSET,
  'sitemap-index.xml': EMPTY_SITEMAP_INDEX,
})

export interface RootSitemapHandlerDependencies {
  readonly proxySitemap?: typeof proxyGuardedSitemap
  readonly createFetcher?: typeof createInternalSitemapFetcher
}

function requestLaunchDecision(event: H3Event): Readonly<LaunchSafetyDecision> {
  const decision = event.context.launchSafety as Readonly<LaunchSafetyDecision> | undefined
  try {
    buildBaseLaunchResponseHeaders({ decision: decision ?? failedOpenLaunchDecision })
    if (decision) return decision
  } catch {
    // Malformed request-local evidence must not select an open response branch.
  }
  event.context.launchSafety = failedOpenLaunchDecision
  return failedOpenLaunchDecision
}

function unavailableSitemapDecision(): Readonly<LaunchSafetyDecision> {
  return Object.freeze({
    ...failedOpenLaunchDecision,
    reason: 'sitemap-batch-unavailable',
  })
}

function writeRootResponse(
  event: H3Event,
  status: 200 | 503,
  contentType: string,
  decision: Readonly<LaunchSafetyDecision>,
  sitemap: boolean,
  requestedBatch: string | null = null,
): void {
  setResponseStatus(event, status)
  setResponseHeader(event, 'Content-Type', contentType)
  writeLaunchResponseHeaders(event, {
    decision,
    sitemap,
    requestedBatch,
  })
}

export function buildLaunchRobotsBody(decision: Readonly<LaunchSafetyDecision>): string {
  const blocked = launchRouteManifest.sensitive_prefixes.map(({ prefix }) => `Disallow: ${prefix}`)
  const groups = ROBOT_AGENTS.map((agent) => [
    `User-agent: ${agent}`,
    'Allow: /',
    ...blocked,
    ...(agent === '*' ? ['Crawl-delay: 2'] : []),
  ].join('\n'))
  const discovery = decision.sitemap_action === 'guarded-proxy'
    ? [`Sitemap: ${CANONICAL_SITEMAP}`]
    : []
  return `${groups.join('\n\n')}\n\nHost: ${launchRouteManifest.canonical_origin}\n${discovery.join('\n')}${discovery.length ? '\n' : ''}`
}

export function createRootRobotsHandler() {
  return defineEventHandler((event) => {
    const decision = requestLaunchDecision(event)
    writeRootResponse(event, 200, ROBOTS_CONTENT_TYPE, decision, false)
    return buildLaunchRobotsBody(decision)
  })
}

export function createRootSitemapHandler(
  document: RootSitemapDocument,
  dependencies: RootSitemapHandlerDependencies = {},
) {
  const proxySitemap = dependencies.proxySitemap ?? proxyGuardedSitemap
  const createFetcher = dependencies.createFetcher ?? createInternalSitemapFetcher

  return defineEventHandler(async (event) => {
    const decision = requestLaunchDecision(event)

    if (decision.sitemap_action === 'closed-empty') {
      writeRootResponse(event, 200, XML_CONTENT_TYPE, decision, true)
      return CLOSED_SITEMAP_BODIES[document]
    }

    if (decision.sitemap_action !== 'guarded-proxy') {
      writeRootResponse(event, 503, XML_CONTENT_TYPE, decision, true)
      return ''
    }

    const url = getRequestURL(event)
    if (
      document === 'sitemap-index.xml'
      && (url.search !== '' || url.href.endsWith('?'))
    ) {
      const unavailable = unavailableSitemapDecision()
      event.context.launchSafety = unavailable
      writeRootResponse(event, 503, XML_CONTENT_TYPE, unavailable, true)
      return ''
    }

    const result = await proxySitemap({
      event,
      document,
      decision,
      url,
      fetchRaw: createFetcher(event),
    })
    event.context.launchSafety = result.decision
    writeRootResponse(
      event,
      result.status,
      result.contentType,
      result.decision,
      true,
      result.requestedBatch,
    )
    return result.body
  })
}
