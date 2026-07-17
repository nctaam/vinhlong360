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

function requestMethod(event: H3Event): string {
  return event.method || event.node.req.method || 'GET'
}

function requestTarget(event: H3Event): string {
  return event.node.req.url || event.path || '/'
}

function requestPathname(event: H3Event): string {
  return requestTarget(event).split('?', 1)[0] || '/'
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
  return ROOT_SEO_PATHS.has(requestPathname(event))
}

export function isLaunchSafetyCandidate(event: H3Event): boolean {
  const method = requestMethod(event)
  if (method !== 'GET' && method !== 'HEAD') return false
  if (isRootSeoRequest(event)) return true

  const pathname = requestPathname(event)
  const finalSegment = pathname.slice(pathname.lastIndexOf('/') + 1)
  if (finalSegment.includes('.') || !acceptsHtml(event)) return false

  const decision = classifyRequestTarget(requestTarget(event), launchRouteManifest, method)
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

export default defineEventHandler(resolveRequestLaunchSafety)
