import manifestJson from '#launch-config/launch-indexing-policy.json'
import { parseLaunchRouteManifestArtifact } from '#launch-validators'

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
const INVALID_PERCENT_ESCAPE = /%(?![0-9A-Fa-f]{2})/
const ENCODED_SLASH_ESCAPE = /%2f|%5c/i
const RESIDUAL_PERCENT_ESCAPE = /%[0-9A-Fa-f]{2}/

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

export type RouteClassificationDecision = RouteDecision
export type DynamicRouteAuthority = LaunchRouteManifest['dynamic_templates'][number]['authority']

interface CompiledDynamicTemplate {
  readonly authority: DynamicRouteAuthority
  readonly segments: ReadonlyArray<string | null>
}

interface CompiledManifestIndex {
  readonly exactRoutes: ReadonlyMap<string, LaunchRouteManifest['exact_routes'][number]['classification']>
  readonly dynamicByLength: ReadonlyMap<number, ReadonlyArray<CompiledDynamicTemplate>>
  readonly staticSitemapPaths: ReadonlyArray<string>
}

const compiledManifestCache = new WeakMap<LaunchRouteManifest, CompiledManifestIndex>()

function compileManifestIndex(manifest: LaunchRouteManifest): CompiledManifestIndex {
  const exactRoutes = new Map<string, LaunchRouteManifest['exact_routes'][number]['classification']>()
  const staticPaths: string[] = []
  for (const item of manifest.exact_routes) {
    if (!exactRoutes.has(item.path)) {
      exactRoutes.set(item.path, item.classification)
    }
    if (item.classification === 'indexable-public' && item.sitemap === true) {
      staticPaths.push(item.path)
    }
  }
  staticPaths.sort(compareCodePointOrder)

  const dynamicByLength = new Map<number, CompiledDynamicTemplate[]>()
  for (const item of manifest.dynamic_templates) {
    const rawSegments = item.template.split('/').slice(1)
    const segments = rawSegments.map(seg => (PLACEHOLDER.test(seg) ? null : seg))
    const bucket = dynamicByLength.get(segments.length)
    if (bucket) bucket.push({ authority: item.authority, segments })
    else dynamicByLength.set(segments.length, [{ authority: item.authority, segments }])
  }

  return {
    exactRoutes,
    dynamicByLength,
    staticSitemapPaths: Object.freeze(staticPaths),
  }
}

function getManifestIndex(manifest: LaunchRouteManifest): CompiledManifestIndex {
  if (!Object.isFrozen(manifest)) return compileManifestIndex(manifest)
  let compiled = compiledManifestCache.get(manifest)
  if (!compiled) {
    compiled = compileManifestIndex(manifest)
    compiledManifestCache.set(manifest, compiled)
  }
  return compiled
}

function matchDynamicAuthority(path: string, index: CompiledManifestIndex): DynamicRouteAuthority | null {
  const pathSegments = path.split('/').slice(1)
  const candidates = index.dynamicByLength.get(pathSegments.length)
  if (!candidates) return null
  for (const candidate of candidates) {
    let matched = true
    for (let i = 0; i < pathSegments.length; i += 1) {
      const expected = candidate.segments[i]
      if (expected !== null && expected !== pathSegments[i]) {
        matched = false
        break
      }
    }
    if (matched) return candidate.authority
  }
  return null
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

function hasDotSegment(path: string): boolean {
  const segments = path.split('/')
  for (let i = 0; i < segments.length; i += 1) {
    const seg = segments[i]
    if (seg === '.' || seg === '..') return true
  }
  return false
}

function decodeOnce(rawPath: string): string | null {
  if (hasUnpairedSurrogate(rawPath)) return null

  if (!rawPath.includes('%')) {
    if (rawPath.includes('\0') || hasDotSegment(rawPath)) return null
    return rawPath
  }

  if (INVALID_PERCENT_ESCAPE.test(rawPath) || ENCODED_SLASH_ESCAPE.test(rawPath)) {
    return null
  }

  let decoded: string
  try {
    decoded = decodeURIComponent(rawPath)
  } catch {
    return null
  }
  if (
    hasUnpairedSurrogate(decoded)
    || decoded.includes('\0')
    || RESIDUAL_PERCENT_ESCAPE.test(decoded)
    || hasDotSegment(decoded)
  ) return null
  return decoded
}

function segmentMatch(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`)
}

export function parseLaunchRouteManifest(
  value: unknown,
  expectedRevision = EXPECTED_REVISION,
): LaunchRouteManifest {
  const parsed = parseLaunchRouteManifestArtifact(value, expectedRevision) as LaunchRouteManifest
  getManifestIndex(parsed)
  return parsed
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
  const normalized = decoded === rawPath
    ? rawWithoutEmpty
    : `/${decoded.split('/').filter(Boolean).join('/')}`

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

  const index = getManifestIndex(manifest)
  const exactClassification = index.exactRoutes.get(normalized)
  if (exactClassification) return { classification: exactClassification, canonical_path: normalized }

  const dynamicAuthority = matchDynamicAuthority(normalized, index)
  if (dynamicAuthority) return { classification: dynamicAuthority, canonical_path: normalized }

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
  return matchDynamicAuthority(canonical, getManifestIndex(manifest))
}

export function extractStaticSitemapPaths(manifest: LaunchRouteManifest): string[] {
  return [...getManifestIndex(manifest).staticSitemapPaths]
}

function compareCodePointOrder(left: string, right: string): number {
  // Match Python's Unicode code-point ordering without allocating per-character arrays.
  let leftIndex = 0
  let rightIndex = 0
  while (leftIndex < left.length && rightIndex < right.length) {
    const leftPoint = left.codePointAt(leftIndex)!
    const rightPoint = right.codePointAt(rightIndex)!
    if (leftPoint !== rightPoint) return leftPoint - rightPoint
    leftIndex += leftPoint > 0xFFFF ? 2 : 1
    rightIndex += rightPoint > 0xFFFF ? 2 : 1
  }
  return (left.length - leftIndex) - (right.length - rightIndex)
}
