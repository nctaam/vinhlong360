import manifestJson from '#launch-config/launch-indexing-policy.json'

const EXPECTED_REVISION = 'launch-indexing-policy-v1'
const NORMALIZATION = Object.freeze({
  percent_decode: 'utf8-once',
  encoded_separator_policy: 'reject',
  dot_segment_policy: 'reject',
  repeated_slash_policy: 'redirect-canonical',
  trailing_slash_policy: 'redirect-except-root',
  query_policy: 'noindex-except-sitemap-batch',
} as const)

const TOP_LEVEL_KEYS = [
  'backend_ingress_exceptions',
  'canonical_origin',
  'dynamic_templates',
  'exact_routes',
  'normalization',
  'revision',
  'schema_version',
  'sensitive_prefixes',
  'unknown_policy',
]
const EXACT_KEYS = ['classification', 'path', 'sitemap']
const PREFIX_KEYS = ['classification', 'prefix']
const INGRESS_KEYS = ['prefix', 'review_reason', 'upstream']
const TEMPLATE_KEYS = ['authority', 'sitemap', 'template']
const PLACEHOLDER = /^\{([a-z_][a-z0-9_]*)\}$/
// Reviewed paths use lowercase ASCII slugs; underscores remain valid for reserved prefixes.
const CANONICAL_PATH_SEGMENT = /^[a-z0-9_]+(?:-[a-z0-9_]+)*$/

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

function record(value: unknown, label: string): Record<string, unknown> {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`route manifest ${label} must be a plain JSON object`)
  }
  return value as Record<string, unknown>
}

function exactKeys(value: Record<string, unknown>, keys: string[], label: string): void {
  const actual: string[] = []
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (typeof key !== 'string' || !descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`route manifest ${label} keys mismatch`)
    }
    actual.push(key)
  }
  actual.sort()
  const expected = [...keys].sort()
  if (actual.join('\0') !== expected.join('\0')) {
    throw new Error(`route manifest ${label} keys mismatch`)
  }
}

function canonicalPath(value: unknown, label: string): string {
  if (typeof value !== 'string' || !value.startsWith('/')) {
    throw new Error(`route manifest ${label} is not canonical`)
  }
  if (value !== '/' && value.slice(1).split('/').some(segment => !CANONICAL_PATH_SEGMENT.test(segment))) {
    throw new Error(`route manifest ${label} is not canonical`)
  }
  return value
}

function templateSignature(template: unknown): string {
  if (typeof template !== 'string') {
    throw new Error('route manifest dynamic template is invalid')
  }

  const names: string[] = []
  const concreteSegments = template.split('/').map((segment) => {
    if (!segment.includes('{') && !segment.includes('}')) return segment

    const match = PLACEHOLDER.exec(segment)
    const name = match?.[1]
    if (!name || names.includes(name)) {
      throw new Error('route manifest dynamic template is invalid')
    }
    names.push(name)
    return 'value'
  })

  if (names.length === 0) {
    throw new Error('route manifest dynamic template is invalid')
  }
  canonicalPath(concreteSegments.join('/'), 'dynamic template')

  return template
    .split('/')
    .map(segment => PLACEHOLDER.test(segment) ? '{}' : segment)
    .join('/')
}

function array(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new Error(`route manifest ${label} must be a plain dense JSON array`)
  }

  const ownKeys = Reflect.ownKeys(value)
  if (ownKeys.length !== value.length + 1 || !ownKeys.includes('length')) {
    throw new Error(`route manifest ${label} must be a plain dense JSON array`)
  }
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (!descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`route manifest ${label} must be a plain dense JSON array`)
    }
  }
  return value
}

function parseArray<T>(
  value: unknown,
  label: string,
  parseItem: (raw: unknown, index: number) => T,
): T[] {
  const items = array(value, label)
  const parsed: T[] = []
  for (let index = 0; index < items.length; index += 1) {
    parsed[index] = parseItem(items[index], index)
  }
  return parsed
}

function assertUnique(values: string[], message: string): void {
  if (new Set(values).size !== values.length) {
    throw new Error(`route manifest ${message}`)
  }
}

function matchesTemplate(path: string, template: string): boolean {
  const pathSegments = path.split('/').slice(1)
  const templateSegments = template.split('/').slice(1)
  return pathSegments.length === templateSegments.length
    && templateSegments.every((segment, index) => PLACEHOLDER.test(segment) || segment === pathSegments[index])
}

function templatesOverlap(left: string, right: string): boolean {
  const leftSegments = left.split('/')
  const rightSegments = right.split('/')
  if (leftSegments.length !== rightSegments.length) return false

  return leftSegments.every((segment, index) => {
    const other = rightSegments[index]!
    return PLACEHOLDER.test(segment) || PLACEHOLDER.test(other) || segment === other
  })
}

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value as Record<string, unknown>)) {
      deepFreeze(child)
    }
  }
  return value
}

export function parseLaunchRouteManifest(
  value: unknown,
  expectedRevision = EXPECTED_REVISION,
): LaunchRouteManifest {
  const manifest = record(value, 'root')
  exactKeys(manifest, TOP_LEVEL_KEYS, 'root')

  if (
    manifest.schema_version !== 1
    || manifest.revision !== expectedRevision
    || manifest.canonical_origin !== 'https://vinhlong360.vn'
    || manifest.unknown_policy !== 'noindex-follow-public'
  ) {
    throw new Error('route manifest fixed fields mismatch')
  }

  const normalization = record(manifest.normalization, 'normalization')
  exactKeys(normalization, Object.keys(NORMALIZATION), 'normalization')
  if (Object.entries(NORMALIZATION).some(([key, expected]) => normalization[key] !== expected)) {
    throw new Error('route manifest normalization mismatch')
  }

  const exactRoutes = parseArray(manifest.exact_routes, 'exact_routes', (
    raw,
    index,
  ): LaunchRouteManifest['exact_routes'][number] => {
    const item = record(raw, `exact_routes[${index}]`)
    exactKeys(item, EXACT_KEYS, `exact_routes[${index}]`)
    const path = canonicalPath(item.path, 'exact path')
    const classification = item.classification
    if (
      (classification !== 'indexable-public' && classification !== 'noindex-follow-public')
      || typeof item.sitemap !== 'boolean'
    ) {
      throw new Error('route manifest exact route values mismatch')
    }
    return { path, classification, sitemap: item.sitemap }
  })

  const sensitivePrefixes = parseArray(manifest.sensitive_prefixes, 'sensitive_prefixes', (
    raw,
    index,
  ): LaunchRouteManifest['sensitive_prefixes'][number] => {
    const item = record(raw, `sensitive_prefixes[${index}]`)
    exactKeys(item, PREFIX_KEYS, `sensitive_prefixes[${index}]`)
    const prefix = canonicalPath(item.prefix, 'sensitive prefix')
    if (prefix === '/') {
      throw new Error('route manifest sensitive prefix cannot be root')
    }
    if (item.classification !== 'crawl-blocked-sensitive') {
      throw new Error('route manifest sensitive classification mismatch')
    }
    return { prefix, classification: item.classification }
  })

  const ingressExceptions = parseArray(
    manifest.backend_ingress_exceptions,
    'backend_ingress_exceptions',
    (raw, index): LaunchRouteManifest['backend_ingress_exceptions'][number] => {
      const item = record(raw, `backend_ingress_exceptions[${index}]`)
      exactKeys(item, INGRESS_KEYS, `backend_ingress_exceptions[${index}]`)
      const prefix = canonicalPath(item.prefix, 'ingress prefix')
      if (prefix === '/') {
        throw new Error('route manifest ingress prefix cannot be root')
      }

      const upstream = item.upstream
      if (
        (upstream !== 'agent' && upstream !== 'bot-gateway')
        || typeof item.review_reason !== 'string'
        || item.review_reason.trim() === ''
      ) {
        throw new Error('route manifest ingress exception mismatch')
      }
      return { prefix, upstream, review_reason: item.review_reason }
    },
  )

  const templates = parseArray(
    manifest.dynamic_templates,
    'dynamic_templates',
    (raw, index): (LaunchRouteManifest['dynamic_templates'][number] & { signature: string }) => {
      const item = record(raw, `dynamic_templates[${index}]`)
      exactKeys(item, TEMPLATE_KEYS, `dynamic_templates[${index}]`)
      const template = item.template
      const signature = templateSignature(template)
      if (typeof template !== 'string') {
        throw new Error('route manifest dynamic template is invalid')
      }

      const authority = item.authority
      if (
        authority !== 'backend-entity'
        && authority !== 'backend-ward'
        && authority !== 'fixed-noindex'
      ) {
        throw new Error('route manifest dynamic authority mismatch')
      }
      if (authority === 'fixed-noindex') {
        if (item.sitemap !== false) {
          throw new Error('route manifest dynamic authority mismatch')
        }
        return { template, signature, authority, sitemap: false }
      }
      if (item.sitemap !== 'backend') {
        throw new Error('route manifest dynamic authority mismatch')
      }
      return { template, signature, authority, sitemap: 'backend' }
    },
  )

  assertUnique(exactRoutes.map(item => item.path), 'duplicate exact route')
  assertUnique(sensitivePrefixes.map(item => item.prefix), 'duplicate sensitive prefix')
  assertUnique(ingressExceptions.map(item => item.prefix), 'duplicate ingress exception')
  assertUnique(templates.map(item => item.signature), 'ambiguous dynamic template')
  for (let left = 0; left < templates.length; left += 1) {
    for (let right = left + 1; right < templates.length; right += 1) {
      if (templatesOverlap(templates[left]!.template, templates[right]!.template)) {
        throw new Error('route manifest overlapping dynamic template')
      }
    }
  }

  if (ingressExceptions.some(item => sensitivePrefixes.some(rule => (
    item.prefix === rule.prefix
    || item.prefix.startsWith(`${rule.prefix}/`)
    || rule.prefix.startsWith(`${item.prefix}/`)
  )))) {
    throw new Error('route manifest ingress/sensitive ambiguity')
  }
  if (exactRoutes.some(item => templates.some(template => matchesTemplate(item.path, template.template)))) {
    throw new Error('route manifest exact/template ambiguity')
  }

  return deepFreeze({
    schema_version: 1,
    revision: manifest.revision,
    canonical_origin: 'https://vinhlong360.vn',
    unknown_policy: 'noindex-follow-public',
    normalization: { ...NORMALIZATION },
    exact_routes: exactRoutes,
    sensitive_prefixes: sensitivePrefixes,
    backend_ingress_exceptions: ingressExceptions,
    dynamic_templates: templates.map(({ signature: _signature, ...item }) => item),
  })
}

export const launchRouteManifest = parseLaunchRouteManifest(manifestJson)
