const ROUTE_REVISION = 'launch-indexing-policy-v1'
const NORMALIZATION = Object.freeze({
  percent_decode: 'utf8-once',
  encoded_separator_policy: 'reject',
  dot_segment_policy: 'reject',
  repeated_slash_policy: 'redirect-canonical',
  trailing_slash_policy: 'redirect-except-root',
  query_policy: 'noindex-except-sitemap-batch',
})
const ROUTE_ROOT_KEYS = [
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
const EXACT_ROUTE_KEYS = ['classification', 'path', 'sitemap']
const PREFIX_KEYS = ['classification', 'prefix']
const INGRESS_KEYS = ['prefix', 'review_reason', 'upstream']
const TEMPLATE_KEYS = ['authority', 'sitemap', 'template']
const PLACEHOLDER = /^\{([a-z_][a-z0-9_]*)\}$/u
const FORBIDDEN_PATH_CHARACTERS = /[\u0000-\u0020\u007F{}\s]/u

const DISCLOSURE_ROOT_KEYS = [
  'entity_ai',
  'forbidden_entity_image_claims',
  'placeholder',
  'revision',
  'schema_version',
  'ugc_photo',
]
const DISCLOSURE_COPY_KEYS = ['accessible_description_key', 'full_disclosure', 'short_label']
const CANONICAL_DISCLOSURE = Object.freeze({
  schema_version: 1,
  revision: 'ai-disclosure-v1',
  entity_ai: Object.freeze({
    short_label: 'Minh h\u1ecda AI',
    full_disclosure: '\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i \u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7.',
    accessible_description_key: 'entity-ai-full',
  }),
  placeholder: Object.freeze({
    short_label: null,
    full_disclosure: 'Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho \u0111\u1ecba \u0111i\u1ec3m.',
    accessible_description_key: 'entity-placeholder-full',
  }),
  ugc_photo: Object.freeze({
    short_label: '\u1ea2nh ng\u01b0\u1eddi d\u00f9ng',
    full_disclosure: '\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.',
    accessible_description_key: 'ugc-photo-full',
  }),
  forbidden_entity_image_claims: Object.freeze([
    '\u1ea3nh th\u1eadt',
    'real photo',
    'documentary photo',
    'on-site photo',
    '\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7',
  ]),
})

function plainRecord(value, label, errorPrefix) {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`${errorPrefix} ${label} must be a plain JSON object`)
  }
  return value
}

function exactKeys(value, expected, label, errorPrefix) {
  const actual = []
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (typeof key !== 'string' || !descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`${errorPrefix} ${label} keys mismatch`)
    }
    actual.push(key)
  }
  actual.sort()
  const sortedExpected = [...expected].sort()
  if (actual.join('\0') !== sortedExpected.join('\0')) {
    throw new Error(`${errorPrefix} ${label} keys mismatch`)
  }
}

function denseArray(value, label, errorPrefix) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new Error(`${errorPrefix} ${label} must be a plain dense JSON array`)
  }
  const ownKeys = Reflect.ownKeys(value)
  if (ownKeys.length !== value.length + 1 || !ownKeys.includes('length')) {
    throw new Error(`${errorPrefix} ${label} must be a plain dense JSON array`)
  }
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (!descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`${errorPrefix} ${label} must be a plain dense JSON array`)
    }
  }
  return value
}

function parseArray(value, label, parseItem, errorPrefix) {
  const items = denseArray(value, label, errorPrefix)
  return items.map((item, index) => parseItem(item, index))
}

function canonicalPath(value, label) {
  if (
    typeof value !== 'string'
    || !value.startsWith('/')
    || value.includes('?')
    || value.includes('#')
    || value.includes('//')
    || value.includes('%')
    || value.includes('\\')
    || FORBIDDEN_PATH_CHARACTERS.test(value)
    || (value !== '/' && value.endsWith('/'))
    || value.split('/').some(segment => segment === '.' || segment === '..')
  ) {
    throw new Error(`route manifest ${label} is not canonical`)
  }
  return value
}

function templateSignature(template) {
  if (typeof template !== 'string') throw new Error('route manifest dynamic template is invalid')
  const names = []
  const concreteSegments = template.split('/').map((segment) => {
    if (!segment.includes('{') && !segment.includes('}')) return segment
    const match = PLACEHOLDER.exec(segment)
    const name = match?.[1]
    if (!name || names.includes(name)) throw new Error('route manifest dynamic template is invalid')
    names.push(name)
    return 'value'
  })
  if (names.length === 0) throw new Error('route manifest dynamic template is invalid')
  canonicalPath(concreteSegments.join('/'), 'dynamic template')
  return template.split('/').map(segment => PLACEHOLDER.test(segment) ? '{}' : segment).join('/')
}

function assertUnique(values, message) {
  if (new Set(values).size !== values.length) throw new Error(`route manifest ${message}`)
}

function templatesOverlap(left, right) {
  const leftSegments = left.split('/')
  const rightSegments = right.split('/')
  if (leftSegments.length !== rightSegments.length) return false
  return leftSegments.every((segment, index) => {
    const other = rightSegments[index]
    return PLACEHOLDER.test(segment) || PLACEHOLDER.test(other) || segment === other
  })
}

function deepFreeze(value) {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value)) deepFreeze(child)
  }
  return value
}

export function parseLaunchRouteManifestArtifact(value, expectedRevision = ROUTE_REVISION) {
  const manifest = plainRecord(value, 'root', 'route manifest')
  exactKeys(manifest, ROUTE_ROOT_KEYS, 'root', 'route manifest')
  if (
    manifest.schema_version !== 1
    || manifest.revision !== expectedRevision
    || manifest.canonical_origin !== 'https://vinhlong360.vn'
    || manifest.unknown_policy !== 'noindex-follow-public'
  ) throw new Error('route manifest fixed fields mismatch')

  const normalization = plainRecord(manifest.normalization, 'normalization', 'route manifest')
  exactKeys(normalization, Object.keys(NORMALIZATION), 'normalization', 'route manifest')
  if (Object.entries(NORMALIZATION).some(([key, expected]) => normalization[key] !== expected)) {
    throw new Error('route manifest normalization mismatch')
  }

  const exactRoutes = parseArray(manifest.exact_routes, 'exact_routes', (raw, index) => {
    const item = plainRecord(raw, `exact_routes[${index}]`, 'route manifest')
    exactKeys(item, EXACT_ROUTE_KEYS, `exact_routes[${index}]`, 'route manifest')
    const path = canonicalPath(item.path, 'exact path')
    const classification = item.classification
    if (
      (classification !== 'indexable-public' && classification !== 'noindex-follow-public')
      || typeof item.sitemap !== 'boolean'
    ) throw new Error('route manifest exact route values mismatch')
    return { path, classification, sitemap: item.sitemap }
  }, 'route manifest')

  const sensitivePrefixes = parseArray(manifest.sensitive_prefixes, 'sensitive_prefixes', (raw, index) => {
    const item = plainRecord(raw, `sensitive_prefixes[${index}]`, 'route manifest')
    exactKeys(item, PREFIX_KEYS, `sensitive_prefixes[${index}]`, 'route manifest')
    const prefix = canonicalPath(item.prefix, 'sensitive prefix')
    if (prefix === '/') throw new Error('route manifest sensitive prefix cannot be root')
    if (item.classification !== 'crawl-blocked-sensitive') {
      throw new Error('route manifest sensitive classification mismatch')
    }
    return { prefix, classification: item.classification }
  }, 'route manifest')

  const ingressExceptions = parseArray(manifest.backend_ingress_exceptions, 'backend_ingress_exceptions', (raw, index) => {
    const item = plainRecord(raw, `backend_ingress_exceptions[${index}]`, 'route manifest')
    exactKeys(item, INGRESS_KEYS, `backend_ingress_exceptions[${index}]`, 'route manifest')
    const prefix = canonicalPath(item.prefix, 'ingress prefix')
    if (prefix === '/') throw new Error('route manifest ingress prefix cannot be root')
    if (
      (item.upstream !== 'agent' && item.upstream !== 'bot-gateway')
      || typeof item.review_reason !== 'string'
      || item.review_reason.trim() === ''
    ) throw new Error('route manifest ingress exception mismatch')
    return { prefix, upstream: item.upstream, review_reason: item.review_reason }
  }, 'route manifest')

  const templates = parseArray(manifest.dynamic_templates, 'dynamic_templates', (raw, index) => {
    const item = plainRecord(raw, `dynamic_templates[${index}]`, 'route manifest')
    exactKeys(item, TEMPLATE_KEYS, `dynamic_templates[${index}]`, 'route manifest')
    const template = item.template
    const signature = templateSignature(template)
    const authority = item.authority
    if (
      authority !== 'backend-entity'
      && authority !== 'backend-ward'
      && authority !== 'fixed-noindex'
    ) throw new Error('route manifest dynamic authority mismatch')
    if (authority === 'fixed-noindex') {
      if (item.sitemap !== false) throw new Error('route manifest dynamic authority mismatch')
      return { template, signature, authority, sitemap: false }
    }
    if (item.sitemap !== 'backend') throw new Error('route manifest dynamic authority mismatch')
    return { template, signature, authority, sitemap: 'backend' }
  }, 'route manifest')

  assertUnique(exactRoutes.map(item => item.path), 'duplicate exact route')
  assertUnique(sensitivePrefixes.map(item => item.prefix), 'duplicate sensitive prefix')
  assertUnique(ingressExceptions.map(item => item.prefix), 'duplicate ingress exception')
  assertUnique(templates.map(item => item.signature), 'ambiguous dynamic template')
  for (let left = 0; left < templates.length; left += 1) {
    for (let right = left + 1; right < templates.length; right += 1) {
      if (templatesOverlap(templates[left].template, templates[right].template)) {
        throw new Error('route manifest overlapping dynamic template')
      }
    }
  }
  if (ingressExceptions.some(item => sensitivePrefixes.some(rule => (
    item.prefix === rule.prefix
    || item.prefix.startsWith(`${rule.prefix}/`)
    || rule.prefix.startsWith(`${item.prefix}/`)
  )))) throw new Error('route manifest ingress/sensitive ambiguity')
  if (exactRoutes.some(item => templates.some(template => {
    const pathSegments = item.path.split('/').slice(1)
    const templateSegments = template.template.split('/').slice(1)
    return pathSegments.length === templateSegments.length
      && templateSegments.every((segment, index) => PLACEHOLDER.test(segment) || segment === pathSegments[index])
  }))) throw new Error('route manifest exact/template ambiguity')

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

function parseDisclosureCopy(value, expected, label) {
  const copy = plainRecord(value, label, 'canonical AI disclosure')
  exactKeys(copy, DISCLOSURE_COPY_KEYS, label, 'canonical AI disclosure')
  if (Object.entries(expected).some(([key, expectedValue]) => copy[key] !== expectedValue)) {
    throw new Error(`canonical AI disclosure ${label} mismatch`)
  }
}

export function parseAiDisclosureArtifact(value) {
  const disclosure = plainRecord(value, 'root', 'canonical AI disclosure')
  exactKeys(disclosure, DISCLOSURE_ROOT_KEYS, 'root', 'canonical AI disclosure')
  if (disclosure.schema_version !== CANONICAL_DISCLOSURE.schema_version) {
    throw new Error('canonical AI disclosure schema_version mismatch')
  }
  if (disclosure.revision !== CANONICAL_DISCLOSURE.revision) {
    throw new Error('canonical AI disclosure revision mismatch')
  }
  parseDisclosureCopy(disclosure.entity_ai, CANONICAL_DISCLOSURE.entity_ai, 'entity_ai')
  parseDisclosureCopy(disclosure.placeholder, CANONICAL_DISCLOSURE.placeholder, 'placeholder')
  parseDisclosureCopy(disclosure.ugc_photo, CANONICAL_DISCLOSURE.ugc_photo, 'ugc_photo')
  const claims = denseArray(disclosure.forbidden_entity_image_claims, 'forbidden claims', 'canonical AI disclosure')
  if (
    claims.length !== CANONICAL_DISCLOSURE.forbidden_entity_image_claims.length
    || claims.some((claim, index) => claim !== CANONICAL_DISCLOSURE.forbidden_entity_image_claims[index])
  ) throw new Error('canonical AI disclosure forbidden claims mismatch')

  return deepFreeze({
    schema_version: 1,
    revision: 'ai-disclosure-v1',
    entity_ai: { ...CANONICAL_DISCLOSURE.entity_ai },
    placeholder: { ...CANONICAL_DISCLOSURE.placeholder },
    ugc_photo: { ...CANONICAL_DISCLOSURE.ugc_photo },
    forbidden_entity_image_claims: [...CANONICAL_DISCLOSURE.forbidden_entity_image_claims],
  })
}
