import type { LaunchPageDecision, LaunchSafetyDecision } from '../../../types/launch'

export type EntityPolicyKind = 'entity' | 'ward'

export interface IndexPolicyDecision {
  readonly indexable: boolean
  readonly kind: EntityPolicyKind
  readonly policy_fingerprint: string
  readonly policy_revision: string
  readonly reasons: readonly string[]
}

const INDEX_POLICY_KEYS = Object.freeze([
  'indexable',
  'kind',
  'policy_fingerprint',
  'policy_revision',
  'reasons',
] as const)

const INDEX_POLICY_KEY_SET: ReadonlySet<string> = new Set(INDEX_POLICY_KEYS)
const LOWER_SHA256 = /^[a-f0-9]{64}$/u

function failedOpenPageDecision(
  reason: 'entity-policy-unavailable' | 'entity-policy-mismatch',
): LaunchPageDecision {
  return Object.freeze({
    operational_state: 'failed-open',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'unavailable',
    reason,
    robots: 'noindex, follow',
    sitemapDiscovery: false,
  })
}

function isSelectiveOpen(base: Readonly<LaunchSafetyDecision>): boolean {
  return base.operational_state === 'selective-open'
    && base.indexing_posture === 'selective-open'
}

/**
 * Turn the request middleware's base decision into the page-shaped decision
 * used by Nuxt head/response consumers before a backend entity carrier arrives.
 */
export function pageDecisionFromBase(
  base: Readonly<LaunchSafetyDecision>,
  routeIsKnownCanonical = false,
): LaunchPageDecision {
  return Object.freeze({
    ...base,
    robots: isSelectiveOpen(base) && routeIsKnownCanonical ? 'index, follow' : 'noindex, follow',
    sitemapDiscovery: isSelectiveOpen(base),
  })
}

export function initialRequestPageDecision(
  base: Readonly<LaunchSafetyDecision>,
  requiresEntityPolicy: boolean,
  routeIsKnownCanonical: boolean,
): LaunchPageDecision {
  if (!isSelectiveOpen(base)) return pageDecisionFromBase(base)
  if (requiresEntityPolicy) return failedOpenPageDecision('entity-policy-unavailable')
  return pageDecisionFromBase(base, routeIsKnownCanonical)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/**
 * Validate the exact backend policy carrier against the already-attested base.
 * This parser is deliberately independent of Vue/Nuxt state so concurrent SSR
 * requests cannot share mutable policy data.
 */
export function parseMatchingEntityPolicy(
  carrier: unknown,
  base: Readonly<LaunchSafetyDecision>,
  expectedKind: EntityPolicyKind,
): Readonly<IndexPolicyDecision> | null {
  try {
    if (!isRecord(carrier)) return null
    const policy = carrier.index_policy
    if (!isRecord(policy)) return null

    const keys = Object.keys(policy)
    if (keys.length !== INDEX_POLICY_KEYS.length || keys.some((key) => !INDEX_POLICY_KEY_SET.has(key))) {
      return null
    }

    if (policy.kind !== expectedKind || typeof policy.indexable !== 'boolean') return null
    if (!Array.isArray(policy.reasons)) return null
    if (policy.reasons.some((reason) => typeof reason !== 'string' || reason.trim().length === 0)) return null

    if (
      typeof policy.policy_fingerprint !== 'string'
      || !LOWER_SHA256.test(policy.policy_fingerprint)
      || policy.policy_fingerprint !== base.policy_fingerprint
    ) {
      return null
    }

    if (
      typeof policy.policy_revision !== 'string'
      || policy.policy_revision.length === 0
      || policy.policy_revision !== base.backend_policy_revision
    ) {
      return null
    }

    // Backend semantics are intentionally checked here as well as in Python:
    // an indexable page has no exclusion reasons; a noindex page has at least one.
    if ((policy.indexable && policy.reasons.length !== 0) || (!policy.indexable && policy.reasons.length === 0)) {
      return null
    }

    const parsed: IndexPolicyDecision = {
      indexable: policy.indexable,
      kind: expectedKind,
      policy_fingerprint: policy.policy_fingerprint,
      policy_revision: policy.policy_revision,
      reasons: Object.freeze([...policy.reasons]),
    }
    return Object.freeze(parsed)
  } catch {
    // Accessors/proxies and malformed payloads are request-local failures.
    return null
  }
}

export interface RefineEntityLaunchDecisionInput {
  readonly base: Readonly<LaunchSafetyDecision>
  readonly carrier: unknown
  readonly expectedKind: EntityPolicyKind
  readonly canonicalPath: boolean
}

export function refineEntityLaunchDecision({
  base,
  carrier,
  expectedKind,
  canonicalPath,
}: RefineEntityLaunchDecisionInput): LaunchPageDecision {
  // Do not inspect or fetch policy data for closed/failed base requests.
  if (!isSelectiveOpen(base)) return pageDecisionFromBase(base)

  // null/undefined denotes a fetch timeout/unavailable response; an object
  // without a valid policy is a received-but-mismatched carrier.
  if (carrier === null || carrier === undefined) return failedOpenPageDecision('entity-policy-unavailable')

  const policy = parseMatchingEntityPolicy(carrier, base, expectedKind)
  if (!policy) return failedOpenPageDecision('entity-policy-mismatch')

  return Object.freeze({
    ...base,
    robots: policy.indexable && canonicalPath ? 'index, follow' : 'noindex, follow',
    sitemapDiscovery: true,
  })
}

export { failedOpenPageDecision }
