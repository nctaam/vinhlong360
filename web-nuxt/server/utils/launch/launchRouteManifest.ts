import manifestJson from '#launch-config/launch-indexing-policy.json'
import { parseLaunchRouteManifestArtifact } from '../../../utils/launchArtifactValidators.mjs'

const EXPECTED_REVISION = 'launch-indexing-policy-v1'
const NORMALIZATION = Object.freeze({
  percent_decode: 'utf8-once',
  encoded_separator_policy: 'reject',
  dot_segment_policy: 'reject',
  repeated_slash_policy: 'redirect-canonical',
  trailing_slash_policy: 'redirect-except-root',
  query_policy: 'noindex-except-sitemap-batch',
} as const)

const PLACEHOLDER = /^\{([a-z_][a-z0-9_]*)\}$/

export interface LaunchRouteManifest {
  readonly schema_version: 1
  readonly revision: string
  readonly canonical_origin: 'https://vinhlong360.vn'
  readonly unknown_policy: 'noindex-follow-public'
  readonly normalization: typeof NORMALIZATION
  readonly exact_routes: ReadonlyArray<{
    readonly path: string
    readonly classification: 'indexable-public' | 'noindex-follow-public'
    readonly sitemap: boolean
  }>
  readonly sensitive_prefixes: ReadonlyArray<{
    readonly prefix: string
    readonly classification: 'crawl-blocked-sensitive'
  }>
  readonly backend_ingress_exceptions: ReadonlyArray<{
    readonly prefix: string
    readonly upstream: 'agent' | 'bot-gateway'
    readonly review_reason: string
  }>
  readonly dynamic_templates: ReadonlyArray<{
    readonly template: string
    readonly authority: 'backend-entity' | 'backend-ward' | 'fixed-noindex'
    readonly sitemap: 'backend' | false
  }>
}

export interface RouteDecision {
  readonly classification: string
  readonly canonical_path: string | null
}

export type DynamicRouteAuthority = LaunchRouteManifest['dynamic_templates'][number]['authority']

function matchesTemplate(path: string, template: string): boolean {
  const pathSegments = path.split('/').slice(1)
  const templateSegments = template.split('/').slice(1)
  return pathSegments.length === templateSegments.length
    && templateSegments.every((segment, index) => PLACEHOLDER.test(segment) || segment === pathSegments[index])
}

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index)
    if (unit >= 0xD800 && unit <= 0xDBFF) {
      const next = value.charCodeAt(index + 1)
      if (!(next >= 0xDC00 && next <= 0xDFFF)) return true
      index += 1
    } else if (unit >= 0xDC00 && unit <= 0xDFFF) {
      return true
    }
  }
  return false
}

function decodeOnce(rawPath: string): string | null {
  if (
    hasUnpairedSurrogate(rawPath)
    || /%(?![0-9A-Fa-f]{2})/.test(rawPath)
    || /%2f|%5c/i.test(rawPath)
  ) return null

  let decoded: string
  try {
    decoded = decodeURIComponent(rawPath)
  } catch {
    return null
  }
  if (
    hasUnpairedSurrogate(decoded)
    || decoded.includes('\0')
    || /%[0-9A-Fa-f]{2}/.test(decoded)
  ) return null
  if (decoded.split('/').some(segment => segment === '.' || segment === '..')) return null
  return decoded
}

function segmentMatch(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`)
}

export function parseLaunchRouteManifest(
  value: unknown,
  expectedRevision = EXPECTED_REVISION,
): LaunchRouteManifest {
  return parseLaunchRouteManifestArtifact(value, expectedRevision) as LaunchRouteManifest
}

export const launchRouteManifest = parseLaunchRouteManifest(manifestJson)

export function classifyRequestTarget(
  target: string,
  manifest: LaunchRouteManifest,
  method: 'GET' | 'HEAD' | string = 'GET',
): RouteDecision {
  if (!target.startsWith('/') || target.includes('#')) {
    return { classification: 'reject', canonical_path: null }
  }

  const question = target.indexOf('?')
  const rawPath = question === -1 ? target : target.slice(0, question)
  const query = question === -1 ? '' : target.slice(question + 1)
  const decoded = decodeOnce(rawPath)
  if (decoded === null) return { classification: 'reject', canonical_path: null }

  const rawWithoutEmpty = `/${rawPath.split('/').filter(Boolean).join('/')}`
  const normalized = `/${decoded.split('/').filter(Boolean).join('/')}`

  for (const item of manifest.sensitive_prefixes) {
    if (segmentMatch(rawWithoutEmpty, item.prefix) || segmentMatch(normalized, item.prefix)) {
      return { classification: 'crawl-blocked-sensitive', canonical_path: normalized }
    }
  }

  if (rawPath !== normalized) {
    const classification = method === 'GET' || method === 'HEAD'
      ? 'redirect-canonical'
      : 'noindex-follow-public'
    return { classification, canonical_path: normalized }
  }

  if (question !== -1 && query !== '') {
    return { classification: 'noindex-follow-public', canonical_path: normalized }
  }

  const exact = manifest.exact_routes.find(item => item.path === normalized)
  if (exact) return { classification: exact.classification, canonical_path: normalized }

  const dynamic = manifest.dynamic_templates.find(item => matchesTemplate(normalized, item.template))
  if (dynamic) return { classification: dynamic.authority, canonical_path: normalized }

  return { classification: manifest.unknown_policy, canonical_path: normalized }
}

/**
 * Resolve the manifest authority behind canonical and non-canonical aliases.
 * Classification alone is insufficient because query/slash/encoding aliases
 * intentionally classify as noindex or redirect before page authority runs.
 */
export function resolveRequestTargetAuthority(
  target: string,
  manifest: LaunchRouteManifest,
  method: 'GET' | 'HEAD' | string = 'GET',
): DynamicRouteAuthority | null {
  const canonical = classifyRequestTarget(target, manifest, method).canonical_path
  if (!canonical) return null
  return manifest.dynamic_templates.find(item => matchesTemplate(canonical, item.template))?.authority ?? null
}

export function extractStaticSitemapPaths(manifest: LaunchRouteManifest): string[] {
  return manifest.exact_routes
    .filter(item => item.classification === 'indexable-public' && item.sitemap === true)
    .map(item => item.path)
    .sort(compareCodePointOrder)
}

function compareCodePointOrder(left: string, right: string): number {
  // Match Python's Unicode code-point ordering for deterministic parity.
  const leftPoints = Array.from(left, character => character.codePointAt(0)!)
  const rightPoints = Array.from(right, character => character.codePointAt(0)!)
  const sharedLength = Math.min(leftPoints.length, rightPoints.length)
  for (let index = 0; index < sharedLength; index += 1) {
    const difference = leftPoints[index]! - rightPoints[index]!
    if (difference !== 0) return difference
  }
  return leftPoints.length - rightPoints.length
}
