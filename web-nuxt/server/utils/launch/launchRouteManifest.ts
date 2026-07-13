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

export interface LaunchRouteManifest {
  schema_version: 1
  revision: string
  canonical_origin: 'https://vinhlong360.vn'
  unknown_policy: 'noindex-follow-public'
  normalization: typeof NORMALIZATION
  exact_routes: Array<{
    path: string
    classification: 'indexable-public' | 'noindex-follow-public'
    sitemap: boolean
  }>
  sensitive_prefixes: Array<{
    prefix: string
    classification: 'crawl-blocked-sensitive'
  }>
  backend_ingress_exceptions: Array<{
    prefix: string
    upstream: 'agent' | 'bot-gateway'
    review_reason: string
  }>
  dynamic_templates: Array<{
    template: string
    authority: 'backend-entity' | 'backend-ward' | 'fixed-noindex'
    sitemap: 'backend' | false
  }>
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`route manifest ${label} must be an object`)
  }
  return value as Record<string, unknown>
}

function exactKeys(value: Record<string, unknown>, keys: string[], label: string): void {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  if (actual.join('\0') !== expected.join('\0')) {
    throw new Error(`route manifest ${label} keys mismatch`)
  }
}

function canonicalPath(value: unknown, label: string): string {
  if (
    typeof value !== 'string'
    || !value.startsWith('/')
    || value.includes('?')
    || value.includes('#')
    || value.includes('//')
    || value.includes('%')
    || value.includes('\\')
    || (value !== '/' && value.endsWith('/'))
    || value.split('/').some(segment => segment === '.' || segment === '..')
  ) {
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
  if (!Array.isArray(value)) {
    throw new Error(`route manifest ${label} must be an array`)
  }
  return value
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

  const exactRoutes = array(manifest.exact_routes, 'exact_routes').map((
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

  const sensitivePrefixes = array(manifest.sensitive_prefixes, 'sensitive_prefixes').map((
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

  const ingressExceptions = array(
    manifest.backend_ingress_exceptions,
    'backend_ingress_exceptions',
  ).map((raw, index): LaunchRouteManifest['backend_ingress_exceptions'][number] => {
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
  })

  const templates = array(manifest.dynamic_templates, 'dynamic_templates').map((raw, index): (
    LaunchRouteManifest['dynamic_templates'][number] & { signature: string }
  ) => {
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
  })

  assertUnique(exactRoutes.map(item => item.path), 'duplicate exact route')
  assertUnique(sensitivePrefixes.map(item => item.prefix), 'duplicate sensitive prefix')
  assertUnique(ingressExceptions.map(item => item.prefix), 'duplicate ingress exception')
  assertUnique(templates.map(item => item.signature), 'ambiguous dynamic template')

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
