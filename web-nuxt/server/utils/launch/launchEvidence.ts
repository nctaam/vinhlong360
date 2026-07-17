import { createHash } from 'node:crypto'

export const INDEX_POLICY_REVISION = 'index-policy-v1'
export const RESPONSE_MATRIX_REVISION = 'launch-safety-matrix-v1'
export const CACHE_ISOLATION_REVISION = 'launch-cache-isolation-v1'
export const SITEMAP_PROTOCOL_REVISION = 'pinned-sitemap-bundle-v1'

const SHA256_PATTERN = /^[0-9a-f]{64}$/u

export interface PolicySemanticRevisions {
  readonly indexPolicy: string
  readonly responseMatrix: string
  readonly cacheIsolation: string
  readonly sitemapProtocol: string
}

function validateRevision(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new TypeError(`${label} must be a string`)
  const normalized = value.normalize('NFC')
  if (!normalized || normalized.trim() !== normalized) {
    throw new Error(`${label} must be a non-empty canonical revision`)
  }
  return normalized
}

function validateSha256(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new TypeError(`${label} must be a string`)
  if (!SHA256_PATTERN.test(value)) throw new Error(`${label} must be a lowercase SHA-256 digest`)
  return value
}

export function buildPolicyFingerprint(
  input: {
    routeRevision: string
    routeDigest: string
    disclosureRevision: string
    disclosureDigest: string
  },
  overrides: Partial<PolicySemanticRevisions> = {},
): string {
  const semantic: PolicySemanticRevisions = {
    indexPolicy: overrides.indexPolicy ?? INDEX_POLICY_REVISION,
    responseMatrix: overrides.responseMatrix ?? RESPONSE_MATRIX_REVISION,
    cacheIsolation: overrides.cacheIsolation ?? CACHE_ISOLATION_REVISION,
    sitemapProtocol: overrides.sitemapProtocol ?? SITEMAP_PROTOCOL_REVISION,
  }

  // Keep key order and compact UTF-8 JSON identical to Python's sorted JSON.
  const canonicalPayload = JSON.stringify({
    cache_isolation: validateRevision(semantic.cacheIsolation, 'cache isolation revision'),
    disclosure_artifact: {
      revision: validateRevision(input.disclosureRevision, 'disclosure revision'),
      sha256: validateSha256(input.disclosureDigest, 'disclosure digest'),
    },
    index_policy: validateRevision(semantic.indexPolicy, 'index policy revision'),
    response_matrix: validateRevision(semantic.responseMatrix, 'response matrix revision'),
    route_artifact: {
      revision: validateRevision(input.routeRevision, 'route revision'),
      sha256: validateSha256(input.routeDigest, 'route digest'),
    },
    sitemap_protocol: validateRevision(semantic.sitemapProtocol, 'sitemap protocol revision'),
  })
  return createHash('sha256').update(canonicalPayload, 'utf8').digest('hex')
}

export function isSha256(value: unknown): value is string {
  return typeof value === 'string' && SHA256_PATTERN.test(value)
}
