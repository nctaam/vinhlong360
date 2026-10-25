import { createHash } from 'node:crypto'

import disclosureArtifactSource from '#launch-config/ai-disclosure.json?raw'
import routeArtifactSource from '#launch-config/launch-indexing-policy.json?raw'
import { defineEventHandler, type H3Event } from 'h3'
import { useRuntimeConfig } from 'nitropack/runtime'

import type { BackendAttestation, LaunchBuildEvidence, LaunchSafetyDecision } from '../../types/launch'
import { aiDisclosure } from '../../utils/aiDisclosure'
import { fetchBackendAttestation } from '../utils/launch/backendAttestation'
import { failedOpenLaunchDecision } from '../utils/launch/launchHeaders'
import {
  classifyRequestTarget,
  launchRouteManifest,
  type RouteClassificationDecision,
} from '../utils/launch/launchRouteManifest'
import { resolveBaseLaunchSafetyDecision } from '../utils/launch/launchSafetyDecision'

const ROOT_SEO_PATHS = new Set([
  '/robots.txt',
  '/sitemap.xml',
  '/sitemap-media.xml',
  '/sitemap-index.xml',
])
const PUBLIC_CLASSIFICATIONS = new Set([
  'indexable-public',
  'noindex-follow-public',
  'backend-entity',
  'backend-ward',
  'fixed-noindex',
  'redirect-canonical',
])

export const launchBuildEvidence: Readonly<LaunchBuildEvidence> = Object.freeze({
  routeRevision: launchRouteManifest.revision,
  routeDigest: createHash('sha256').update(routeArtifactSource, 'utf8').digest('hex'),
  disclosureRevision: aiDisclosure.revision,
  disclosureDigest: createHash('sha256').update(disclosureArtifactSource, 'utf8').digest('hex'),
})

type AttestationFetcher = () => Promise<BackendAttestation | unknown>

export interface ResolveRequestLaunchSafetyDependencies {
  readonly env: NodeJS.ProcessEnv
  readonly build: LaunchBuildEvidence
  readonly fetchAttestation: AttestationFetcher
}

interface CachedEventRouteInfo {
  method: string
  target: string
  pathname: string
  decision?: RouteClassificationDecision
}

const eventRouteCache = new WeakMap<H3Event, CachedEventRouteInfo>()

function getEventRouteInfo(event: H3Event): CachedEventRouteInfo {
  let cached = eventRouteCache.get(event)
  if (!cached) {
    const method = event.method || event.node.req.method || 'GET'
    const target = event.node.req.url || event.path || '/'
    const pathname = target.split('?', 1)[0] || '/'
    cached = { method, target, pathname }
    eventRouteCache.set(event, cached)
  }
  return cached
}

function getEventRouteDecision(event: H3Event, info = getEventRouteInfo(event)): RouteClassificationDecision {
  if (!info.decision) {
    info.decision = classifyRequestTarget(info.target, launchRouteManifest, info.method)
  }
  return info.decision
}

function acceptsHtml(event: H3Event): boolean {
  const raw = event.node.req.headers.accept
  const accept = Array.isArray(raw) ? raw.join(',') : raw
  return typeof accept !== 'string'
    || accept.includes('text/html')
    || accept.includes('application/xhtml+xml')
    || accept.includes('*/*')
}

export function isRootSeoRequest(event: H3Event): boolean {
  return ROOT_SEO_PATHS.has(getEventRouteInfo(event).pathname)
}

export function isKnownNonHtmlRequest(event: H3Event): boolean {
  const info = getEventRouteInfo(event)
  if (info.pathname === '/_nuxt' || info.pathname.startsWith('/_nuxt/')) return true

  const decision = getEventRouteDecision(event, info)
  return decision.classification === 'crawl-blocked-sensitive'
}

export function isLaunchSafetyCandidate(event: H3Event): boolean {
  const info = getEventRouteInfo(event)
  if (info.method !== 'GET' && info.method !== 'HEAD') return false
  if (ROOT_SEO_PATHS.has(info.pathname)) return true

  const finalSegment = info.pathname.slice(info.pathname.lastIndexOf('/') + 1)
  if (finalSegment.includes('.') || !acceptsHtml(event)) return false

  const decision = getEventRouteDecision(event, info)
  return PUBLIC_CLASSIFICATIONS.has(decision.classification)
}

function defaultDependencies(event: H3Event): ResolveRequestLaunchSafetyDependencies {
  return {
    env: process.env,
    build: launchBuildEvidence,
    fetchAttestation: async () => {
      const runtimeConfig = useRuntimeConfig(event) as { apiBase?: unknown }
      const baseURL = typeof runtimeConfig.apiBase === 'string' ? runtimeConfig.apiBase : ''
      return fetchBackendAttestation({ baseURL })
    },
  }
}

export async function resolveRequestLaunchSafety(
  event: H3Event,
  dependencies: ResolveRequestLaunchSafetyDependencies = defaultDependencies(event),
): Promise<Readonly<LaunchSafetyDecision> | undefined> {
  if (!isLaunchSafetyCandidate(event)) return undefined

  // Establish a safe request-local value before the attestation request can yield or fail.
  const fallbackDecision = Object.freeze({ ...failedOpenLaunchDecision })
  event.context.launchSafety = fallbackDecision

  try {
    const decision = await resolveBaseLaunchSafetyDecision({
      env: dependencies.env,
      build: dependencies.build,
      fetchAttestation: dependencies.fetchAttestation,
    })
    const immutableDecision = Object.freeze({ ...decision })
    event.context.launchSafety = immutableDecision
    return immutableDecision
  } catch {
    return fallbackDecision
  }
}

export default defineEventHandler(async (event) => {
  await resolveRequestLaunchSafety(event)
})
