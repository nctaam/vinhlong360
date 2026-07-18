import {
  getResponseHeaders,
  removeResponseHeader,
  setResponseHeaders,
  type H3Event,
} from 'h3'

import type { LaunchPageDecision, LaunchSafetyDecision } from '../../../types/launch'
import { INDEX_POLICY_REVISION, isSha256 } from './launchEvidence'
import { launchRouteManifest } from './launchRouteManifest'

export const LAUNCH_HEADER_NAMES = Object.freeze([
  'X-Launch-Indexing-Policy',
  'X-Launch-Policy-Fingerprint',
  'X-Launch-Route-Manifest-Revision',
  'X-Launch-Backend-Policy-Revision',
  'X-Launch-Sitemap-Batch-Revision',
  'X-Launch-Sitemap-Requested-Batch',
] as const)

const LAUNCH_HEADER_NAMES_LOWER = new Set([
  ...LAUNCH_HEADER_NAMES.map(name => name.toLowerCase()),
  'cache-control',
  'x-robots-tag',
])
const CLOSED_REASONS = new Set([
  'closed-default',
  'invalid-configuration',
  'owner-approval-missing',
])
const FAILED_OPEN_REASONS = new Set([
  'policy-attestation-unavailable',
  'policy-mismatch',
  'build-isolation-unsafe',
  'entity-policy-unavailable',
  'entity-policy-mismatch',
  'sitemap-batch-unavailable',
  'sitemap-evidence-mismatch',
])
const EMPTY_DECISION: LaunchSafetyDecision = Object.freeze({
  operational_state: 'failed-open',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'unavailable',
  reason: 'build-isolation-unsafe',
})

export interface LaunchResponseHeaderInput {
  readonly decision: Readonly<LaunchSafetyDecision>
  readonly html?: boolean
  readonly sitemap?: boolean
  readonly requestedBatch?: string | null
}

function invalidSelectiveDecision(): Error {
  return new Error('selective-open decision evidence is invalid')
}

function isDecisionRecord(value: unknown): value is Readonly<LaunchSafetyDecision> {
  return value !== null
    && typeof value === 'object'
    && !Array.isArray(value)
}

function hasClearedEvidence(decision: Readonly<LaunchSafetyDecision>): boolean {
  return decision.policy_fingerprint === null
    && decision.route_manifest_revision === null
    && decision.backend_policy_revision === null
    && decision.sitemap_batch_revision === null
}

function validateDecision(value: unknown): Readonly<LaunchSafetyDecision> {
  if (!isDecisionRecord(value)) throw new TypeError('launch safety decision is invalid')

  const decision = value as Readonly<LaunchSafetyDecision>

  if (decision.operational_state === 'closed') {
    if (
      decision.indexing_posture !== 'closed'
      || decision.sitemap_action !== 'closed-empty'
      || !CLOSED_REASONS.has(decision.reason)
      || !hasClearedEvidence(decision)
    ) {
      throw new TypeError('closed launch safety decision is invalid')
    }
    return decision
  }

  if (decision.operational_state === 'failed-open') {
    if (
      decision.indexing_posture !== 'closed'
      || decision.sitemap_action !== 'unavailable'
      || !FAILED_OPEN_REASONS.has(decision.reason)
      || !hasClearedEvidence(decision)
    ) {
      throw new TypeError('failed-open launch safety decision is invalid')
    }
    return decision
  }

  if (decision.operational_state !== 'selective-open') throw new TypeError('launch safety decision state is invalid')
  if (
    decision.indexing_posture !== 'selective-open'
    || decision.sitemap_action !== 'guarded-proxy'
    || decision.reason !== 'valid-two-key-unlock'
    || !isSha256(decision.policy_fingerprint)
    || decision.route_manifest_revision !== launchRouteManifest.revision
    || decision.backend_policy_revision !== INDEX_POLICY_REVISION
    || (decision.sitemap_batch_revision !== null && !isSha256(decision.sitemap_batch_revision))
  ) {
    throw invalidSelectiveDecision()
  }
  return decision
}

function validateRequestedBatch(input: LaunchResponseHeaderInput): string | null {
  const requested = input.requestedBatch
  if (requested === undefined || requested === null) return null
  if (input.sitemap !== true || !isSha256(requested)) {
    throw new TypeError('requested sitemap batch must be a lowercase SHA-256 digest')
  }
  return requested
}

export function buildBaseLaunchResponseHeaders(input: LaunchResponseHeaderInput): Record<string, string> {
  const decision = validateDecision(input.decision)
  if (input.sitemap !== undefined && typeof input.sitemap !== 'boolean') {
    throw new TypeError('sitemap header option must be boolean')
  }
  const requested = validateRequestedBatch(input)

  const headers: Record<string, string> = {
    'Cache-Control': 'no-store',
    'X-Launch-Indexing-Policy': decision.operational_state,
  }

  if (decision.operational_state !== 'selective-open') return headers

  const policyFingerprint = decision.policy_fingerprint
  if (!isSha256(policyFingerprint)) throw invalidSelectiveDecision()
  headers['X-Launch-Policy-Fingerprint'] = policyFingerprint
  headers['X-Launch-Route-Manifest-Revision'] = launchRouteManifest.revision
  headers['X-Launch-Backend-Policy-Revision'] = INDEX_POLICY_REVISION

  if (input.sitemap === true) {
    const batch = decision.sitemap_batch_revision
    if (!isSha256(batch)) throw new Error('validated sitemap batch revision is required')
    headers['X-Launch-Sitemap-Batch-Revision'] = batch

    if (requested !== null) {
      if (requested !== batch) throw new Error('requested sitemap batch must match the served batch')
      headers['X-Launch-Sitemap-Requested-Batch'] = requested
    }
  }

  return headers
}

function launchRobots(decision: Readonly<LaunchSafetyDecision>): LaunchPageDecision['robots'] {
  if (!('robots' in decision)) throw new TypeError('HTML launch decision is missing robots')
  const robots = decision.robots
  if (robots !== 'index, follow' && robots !== 'noindex, follow') {
    throw new TypeError('HTML launch robots decision is invalid')
  }
  return robots
}

export function buildLaunchResponseHeaders(input: LaunchResponseHeaderInput): Record<string, string> {
  if (input.html !== undefined && typeof input.html !== 'boolean') {
    throw new TypeError('HTML header option must be boolean')
  }

  const headers = buildBaseLaunchResponseHeaders(input)
  if (input.html === true) headers['X-Robots-Tag'] = launchRobots(input.decision)
  return headers
}

function clearLaunchHeaders(event: H3Event): void {
  for (const name of Object.keys(getResponseHeaders(event))) {
    if (LAUNCH_HEADER_NAMES_LOWER.has(name.toLowerCase())) removeResponseHeader(event, name)
  }
}

function storeHeaderInput(event: H3Event, input: LaunchResponseHeaderInput): void {
  event.context.launchResponseHeaderInput = Object.freeze({
    decision: input.decision,
    html: input.html,
    sitemap: input.sitemap,
    requestedBatch: input.requestedBatch ?? null,
  })
}

export function writeLaunchResponseHeaders(
  event: H3Event,
  input: LaunchResponseHeaderInput,
): void {
  clearLaunchHeaders(event)

  let headers: Record<string, string>
  let effectiveInput: LaunchResponseHeaderInput = input
  try {
    headers = buildLaunchResponseHeaders(input)
  } catch {
    effectiveInput = {
      decision: input.html === true
        ? Object.freeze({
            ...EMPTY_DECISION,
            robots: 'noindex, follow',
            sitemapDiscovery: false,
          })
        : EMPTY_DECISION,
      html: input.html === true,
    }
    headers = buildLaunchResponseHeaders(effectiveInput)
  }

  setResponseHeaders(event, headers)
  if (effectiveInput.html === true) event.context.launchSafety = effectiveInput.decision
  storeHeaderInput(event, effectiveInput)
}

export { EMPTY_DECISION as failedOpenLaunchDecision }
