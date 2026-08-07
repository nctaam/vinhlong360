import { describe, expect, it } from 'vitest'
import {
  launchRouteManifest,
  parseLaunchRouteManifest,
  type LaunchRouteManifest,
} from '../server/utils/launch/launchRouteManifest'

const validManifest = {
  schema_version: 1,
  revision: 'launch-indexing-policy-v1',
  canonical_origin: 'https://vinhlong360.vn',
  unknown_policy: 'noindex-follow-public',
  normalization: {
    percent_decode: 'utf8-once',
    encoded_separator_policy: 'reject',
    dot_segment_policy: 'reject',
    repeated_slash_policy: 'redirect-canonical',
    trailing_slash_policy: 'redirect-except-root',
    query_policy: 'noindex-except-sitemap-batch',
  },
  exact_routes: [
    { path: '/', classification: 'indexable-public', sitemap: true },
    { path: '/du-lich', classification: 'indexable-public', sitemap: true },
    { path: '/dia-diem', classification: 'indexable-public', sitemap: true },
    { path: '/san-pham', classification: 'indexable-public', sitemap: true },
    { path: '/ocop', classification: 'indexable-public', sitemap: true },
    { path: '/luu-tru', classification: 'indexable-public', sitemap: true },
    { path: '/le-hoi', classification: 'indexable-public', sitemap: true },
    { path: '/su-kien', classification: 'indexable-public', sitemap: true },
    { path: '/theo-mua', classification: 'indexable-public', sitemap: true },
    { path: '/ban-do', classification: 'indexable-public', sitemap: true },
    { path: '/tuyen-duong', classification: 'indexable-public', sitemap: true },
    { path: '/danh-ba', classification: 'indexable-public', sitemap: true },
    { path: '/gioi-thieu', classification: 'indexable-public', sitemap: true },
    { path: '/huong-dan', classification: 'indexable-public', sitemap: true },
    { path: '/huong-dan-thanh-vien', classification: 'indexable-public', sitemap: true },
    { path: '/lien-he', classification: 'indexable-public', sitemap: true },
    { path: '/chinh-sach-bao-mat', classification: 'indexable-public', sitemap: true },
    { path: '/dieu-khoan-su-dung', classification: 'indexable-public', sitemap: true },
    { path: '/kham-pha/am-thuc', classification: 'indexable-public', sitemap: true },
    { path: '/kham-pha/thien-nhien', classification: 'indexable-public', sitemap: true },
    { path: '/kham-pha/van-hoa', classification: 'indexable-public', sitemap: true },
    { path: '/kham-pha/lang-nghe', classification: 'indexable-public', sitemap: true },
    { path: '/kham-pha/mua-sam', classification: 'indexable-public', sitemap: true },
    { path: '/khu-vuc/vinh-long', classification: 'indexable-public', sitemap: true },
    { path: '/khu-vuc/ben-tre', classification: 'indexable-public', sitemap: true },
    { path: '/khu-vuc/tra-vinh', classification: 'indexable-public', sitemap: true },
    { path: '/tim-kiem', classification: 'noindex-follow-public', sitemap: false },
    { path: '/lich-van-nien', classification: 'noindex-follow-public', sitemap: false },
    { path: '/lich-trinh', classification: 'noindex-follow-public', sitemap: false },
    { path: '/tao-lich-trinh', classification: 'noindex-follow-public', sitemap: false },
    { path: '/cong-dong', classification: 'noindex-follow-public', sitemap: false },
    { path: '/bang-xep-hang', classification: 'noindex-follow-public', sitemap: false },
  ],
  sensitive_prefixes: [
    { prefix: '/_internal', classification: 'crawl-blocked-sensitive' },
    { prefix: '/admin', classification: 'crawl-blocked-sensitive' },
    { prefix: '/admin-api', classification: 'crawl-blocked-sensitive' },
    { prefix: '/analytics', classification: 'crawl-blocked-sensitive' },
    { prefix: '/api', classification: 'crawl-blocked-sensitive' },
    { prefix: '/auth', classification: 'crawl-blocked-sensitive' },
    { prefix: '/chat', classification: 'crawl-blocked-sensitive' },
    { prefix: '/events', classification: 'crawl-blocked-sensitive' },
    { prefix: '/feedback', classification: 'crawl-blocked-sensitive' },
    { prefix: '/freshness', classification: 'crawl-blocked-sensitive' },
    { prefix: '/health', classification: 'crawl-blocked-sensitive' },
    { prefix: '/reload', classification: 'crawl-blocked-sensitive' },
    { prefix: '/recommend', classification: 'crawl-blocked-sensitive' },
    { prefix: '/seo', classification: 'crawl-blocked-sensitive' },
    { prefix: '/system', classification: 'crawl-blocked-sensitive' },
    { prefix: '/weather', classification: 'crawl-blocked-sensitive' },
    { prefix: '/webhook', classification: 'crawl-blocked-sensitive' },
    { prefix: '/welcome', classification: 'crawl-blocked-sensitive' },
    { prefix: '/cai-dat', classification: 'crawl-blocked-sensitive' },
    { prefix: '/tai-khoan', classification: 'crawl-blocked-sensitive' },
    { prefix: '/da-luu', classification: 'crawl-blocked-sensitive' },
    { prefix: '/thong-bao', classification: 'crawl-blocked-sensitive' },
  ],
  backend_ingress_exceptions: [],
  dynamic_templates: [
    { template: '/dia-diem/{entity_id}', authority: 'backend-entity', sitemap: 'backend' },
    { template: '/xa-phuong/{ward_id}', authority: 'backend-ward', sitemap: 'backend' },
    { template: '/bai-viet/{id}', authority: 'fixed-noindex', sitemap: false },
    { template: '/nguoi-dung/{id}', authority: 'fixed-noindex', sitemap: false },
    { template: '/lich-trinh/{id}', authority: 'fixed-noindex', sitemap: false },
    { template: '/lich-trinh-chia-se/{id}', authority: 'fixed-noindex', sitemap: false },
  ],
}

const invalidRawPathCases = [
  ['C0 NUL', '/bad\u0000path'],
  ['C0 tab', '/bad\tpath'],
  ['DEL', '/bad\u007Fpath'],
  ['ASCII whitespace', '/bad path'],
  ['non-breaking whitespace', '/bad\u00A0path'],
  ['raw opening brace', '/bad{path'],
  ['raw closing brace', '/bad}path'],
] as const

const manifestArrayFields = [
  'exact_routes',
  'sensitive_prefixes',
  'backend_ingress_exceptions',
  'dynamic_templates',
] as const

type ManifestArrayField = typeof manifestArrayFields[number]

function cloneManifest(): typeof validManifest {
  return structuredClone(validManifest)
}

function cloneManifestArray(field: ManifestArrayField): unknown[] {
  return structuredClone(validManifest[field]) as unknown[]
}

function withManifestArray(field: ManifestArrayField, value: unknown[]): Record<string, unknown> {
  return { ...validManifest, [field]: value }
}

function assertReadonlyManifestTypes(manifest: LaunchRouteManifest): void {
  // @ts-expect-error parsed manifest root fields are readonly
  manifest.revision = 'changed'
  // @ts-expect-error normalization fields are readonly
  manifest.normalization.percent_decode = 'utf8-once'
  // @ts-expect-error parsed manifest arrays are readonly
  manifest.exact_routes.push(manifest.exact_routes[0]!)
  // @ts-expect-error exact route fields are readonly
  manifest.exact_routes[0]!.path = '/changed'
  // @ts-expect-error sensitive prefix fields are readonly
  manifest.sensitive_prefixes[0]!.prefix = '/changed'
  // @ts-expect-error ingress exception fields are readonly
  manifest.backend_ingress_exceptions[0]!.review_reason = 'changed'
  // @ts-expect-error dynamic template fields are readonly
  manifest.dynamic_templates[0]!.authority = 'fixed-noindex'
}

void assertReadonlyManifestTypes

describe('parseLaunchRouteManifest', () => {
  it('accepts the canonical placeholder grammar and canonical manifest', () => {
    const parsed = parseLaunchRouteManifest(validManifest)

    expect(parsed).toEqual(validManifest)
    expect(launchRouteManifest).toEqual(validManifest)
    expect(parsed.dynamic_templates.map(item => item.template)).toContain('/dia-diem/{entity_id}')
  })

  it('does not mutate the input and deeply freezes the parsed manifest', () => {
    const input = cloneManifest()
    const before = structuredClone(input)
    const parsed = parseLaunchRouteManifest(input)

    expect(input).toEqual(before)
    expect(parsed).not.toBe(input)
    expect(parsed.normalization).not.toBe(input.normalization)
    expect(parsed.exact_routes).not.toBe(input.exact_routes)
    expect(Object.isFrozen(parsed)).toBe(true)
    expect(Object.isFrozen(parsed.normalization)).toBe(true)
    expect(Object.isFrozen(parsed.exact_routes)).toBe(true)
    expect(Object.isFrozen(parsed.exact_routes[0])).toBe(true)
    expect(Object.isFrozen(input)).toBe(false)
  })

  it.each([
    ['missing normalization key', { normalization: { percent_decode: 'utf8-once' } }],
    ['unknown top-level key', { extra: true }],
    ['invalid exact classification', {
      exact_routes: [{ path: '/', classification: 'public', sitemap: true }],
    }],
    ['empty ingress review', {
      backend_ingress_exceptions: [{ prefix: '/hook', upstream: 'agent', review_reason: ' ' }],
    }],
  ])('rejects %s', (_name, override) => {
    expect(() => parseLaunchRouteManifest({ ...validManifest, ...override }))
      .toThrow(/route manifest/i)
  })

  it('rejects duplicate dynamic signatures with the ambiguity error', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      dynamic_templates: [
        { template: '/dia-diem/{entity_id}', authority: 'backend-entity', sitemap: 'backend' },
        { template: '/dia-diem/{id}', authority: 'backend-entity', sitemap: 'backend' },
      ],
    })).toThrow(/ambiguous dynamic template/i)
  })

  it.each([
    '/admin/',
    'admin',
    '/ad?min',
    '/ad#min',
    '/ad//min',
    '/ad%2Fmin',
    '/ad\\min',
    '/admin/.',
    '/admin/../private',
  ])('rejects an invalid canonical sensitive prefix: %s', (prefix) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      sensitive_prefixes: [{ prefix, classification: 'crawl-blocked-sensitive' }],
    })).toThrow(/sensitive prefix.*canonical/i)
  })

  it.each([
    ['exact path with a dotted segment', {
      exact_routes: [{ path: '/release/v1.0', classification: 'indexable-public', sitemap: true }],
    }],
    ['sensitive prefix with a leading hyphen', {
      sensitive_prefixes: [{ prefix: '/-well-known', classification: 'crawl-blocked-sensitive' }],
    }],
    ['ingress prefix with an RFC unreserved tilde', {
      backend_ingress_exceptions: [{
        prefix: '/foo~bar', upstream: 'agent', review_reason: 'reviewed endpoint',
      }],
    }],
    ['exact path with a double hyphen', {
      exact_routes: [{ path: '/foo--bar', classification: 'indexable-public', sitemap: true }],
    }],
  ])('accepts reviewed-shape canonical %s', (_name, override) => {
    expect(() => parseLaunchRouteManifest({ ...validManifest, ...override })).not.toThrow()
  })

  it.each(invalidRawPathCases)('rejects %s in an exact path', (_name, path) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      exact_routes: [{ path, classification: 'indexable-public', sitemap: true }],
    })).toThrow(/exact path.*canonical/i)
  })

  it.each(invalidRawPathCases)('rejects %s in a sensitive prefix', (_name, prefix) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      sensitive_prefixes: [{ prefix, classification: 'crawl-blocked-sensitive' }],
    })).toThrow(/sensitive prefix.*canonical/i)
  })

  it.each(invalidRawPathCases)('rejects %s in an ingress prefix', (_name, prefix) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      backend_ingress_exceptions: [{ prefix, upstream: 'agent', review_reason: 'reviewed' }],
    })).toThrow(/ingress prefix.*canonical/i)
  })

  it.each([
    '/dia-diem/{entity_id',
    '/dia-diem/entity_id}',
    '/dia-diem/{}',
    '/dia-diem/{EntityId}',
    '/dia-diem/prefix-{entity_id}',
    '/dia-diem/{entity_id}-suffix',
    '/dia-diem/{entity_id}/{entity_id}',
  ])('rejects malformed or duplicate placeholder grammar: %s', (template) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      dynamic_templates: [{ template, authority: 'backend-entity', sitemap: 'backend' }],
    })).toThrow(/dynamic template/i)
  })

  it('rejects dynamic templates that can match the same concrete path', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      dynamic_templates: [
        { template: '/foo/{id}/bar', authority: 'fixed-noindex', sitemap: false },
        { template: '/foo/baz/{slug}', authority: 'fixed-noindex', sitemap: false },
      ],
    })).toThrow(/overlapping dynamic template/i)
  })

  it('accepts dynamic templates separated by conflicting literal segments', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      dynamic_templates: [
        { template: '/foo/{id}/bar', authority: 'fixed-noindex', sitemap: false },
        { template: '/foo/{slug}/qux', authority: 'fixed-noindex', sitemap: false },
      ],
    })).not.toThrow()
  })

  it('rejects duplicate exact routes', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      exact_routes: [validManifest.exact_routes[0], validManifest.exact_routes[0]],
    })).toThrow(/duplicate exact route/i)
  })

  it('rejects duplicate sensitive prefixes', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      sensitive_prefixes: [validManifest.sensitive_prefixes[0], validManifest.sensitive_prefixes[0]],
    })).toThrow(/duplicate sensitive prefix/i)
  })

  it('rejects duplicate ingress exception prefixes', () => {
    const exception = { prefix: '/hook', upstream: 'bot-gateway', review_reason: 'reviewed alias' }

    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      backend_ingress_exceptions: [exception, exception],
    })).toThrow(/duplicate ingress exception/i)
  })

  it.each(manifestArrayFields)('rejects an own array method on %s', (field) => {
    const values = cloneManifestArray(field)
    Object.defineProperty(values, 'map', { enumerable: true, value: () => [] })

    expect(() => parseLaunchRouteManifest(withManifestArray(field, values)))
      .toThrow(/plain dense JSON array/i)
  })

  it.each(manifestArrayFields)('rejects a sparse %s array', (field) => {
    const values = new Array<unknown>(1)

    expect(() => parseLaunchRouteManifest(withManifestArray(field, values)))
      .toThrow(/plain dense JSON array/i)
  })

  it.each(manifestArrayFields)('rejects an Array subclass for %s', (field) => {
    class ManifestArray extends Array<unknown> {}
    const values = new ManifestArray(...cloneManifestArray(field))

    expect(() => parseLaunchRouteManifest(withManifestArray(field, values)))
      .toThrow(/plain dense JSON array/i)
  })

  it.each(manifestArrayFields)('rejects an extra own property on %s', (field) => {
    const values = cloneManifestArray(field)
    Object.defineProperty(values, 'reviewed', { enumerable: true, value: true })

    expect(() => parseLaunchRouteManifest(withManifestArray(field, values)))
      .toThrow(/plain dense JSON array/i)
  })

  it('rejects an array with a custom prototype', () => {
    const values = cloneManifestArray('exact_routes')
    Object.setPrototypeOf(values, Object.create(Array.prototype))

    expect(() => parseLaunchRouteManifest(withManifestArray('exact_routes', values)))
      .toThrow(/plain dense JSON array/i)
  })

  it.each([
    ['custom root prototype', { inherited: true }],
    ['null root prototype', null],
  ])('rejects a manifest with a %s', (_name, prototype) => {
    const candidate = cloneManifest()
    Object.setPrototypeOf(candidate, prototype)

    expect(() => parseLaunchRouteManifest(candidate)).toThrow(/plain JSON object/i)
  })

  it('rejects a route item with an unusual prototype', () => {
    const route = { path: '/', classification: 'indexable-public', sitemap: true }
    Object.setPrototypeOf(route, { inherited: true })

    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      exact_routes: [route],
    })).toThrow(/plain JSON object/i)
  })

  it.each([
    ['null root', null],
    ['array root', []],
    ['wrong schema type', { ...validManifest, schema_version: true }],
    ['wrong revision', { ...validManifest, revision: 'launch-indexing-policy-v2' }],
    ['wrong canonical origin', { ...validManifest, canonical_origin: 'https://example.com' }],
    ['wrong unknown policy', { ...validManifest, unknown_policy: 'indexable-public' }],
    ['wrong normalization value', {
      ...validManifest,
      normalization: { ...validManifest.normalization, percent_decode: 'twice' },
    }],
    ['non-array exact routes', { ...validManifest, exact_routes: {} }],
    ['extra exact route key', {
      ...validManifest,
      exact_routes: [{ path: '/', classification: 'indexable-public', sitemap: true, extra: true }],
    }],
    ['non-boolean exact sitemap', {
      ...validManifest,
      exact_routes: [{ path: '/', classification: 'indexable-public', sitemap: 'true' }],
    }],
    ['invalid sensitive classification', {
      ...validManifest,
      sensitive_prefixes: [{ prefix: '/admin', classification: 'noindex-follow-public' }],
    }],
    ['invalid ingress upstream', {
      ...validManifest,
      backend_ingress_exceptions: [{ prefix: '/hook', upstream: 'nuxt', review_reason: 'reviewed' }],
    }],
    ['non-string ingress review', {
      ...validManifest,
      backend_ingress_exceptions: [{ prefix: '/hook', upstream: 'agent', review_reason: 1 }],
    }],
    ['extra template key', {
      ...validManifest,
      dynamic_templates: [{
        template: '/dia-diem/{id}', authority: 'backend-entity', sitemap: 'backend', extra: true,
      }],
    }],
    ['invalid template authority', {
      ...validManifest,
      dynamic_templates: [{ template: '/dia-diem/{id}', authority: 'nuxt', sitemap: 'backend' }],
    }],
    ['backend authority with false sitemap', {
      ...validManifest,
      dynamic_templates: [{ template: '/dia-diem/{id}', authority: 'backend-entity', sitemap: false }],
    }],
    ['fixed-noindex authority with backend sitemap', {
      ...validManifest,
      dynamic_templates: [{ template: '/bai-viet/{id}', authority: 'fixed-noindex', sitemap: 'backend' }],
    }],
  ])('rejects exact keys, types, and fixed values: %s', (_name, candidate) => {
    expect(() => parseLaunchRouteManifest(candidate)).toThrow(/route manifest/i)
  })

  it('rejects root prefixes, ingress-sensitive overlap, and exact-template ambiguity', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      sensitive_prefixes: [{ prefix: '/', classification: 'crawl-blocked-sensitive' }],
    })).toThrow(/sensitive prefix cannot be root/i)
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      backend_ingress_exceptions: [{ prefix: '/', upstream: 'agent', review_reason: 'reviewed' }],
    })).toThrow(/ingress prefix cannot be root/i)
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      backend_ingress_exceptions: [{
        prefix: '/webhook/callback', upstream: 'bot-gateway', review_reason: 'reviewed callback',
      }],
    })).toThrow(/ingress\/sensitive ambiguity/i)
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      exact_routes: [
        ...validManifest.exact_routes,
        { path: '/dia-diem/example', classification: 'indexable-public', sitemap: true },
      ],
    })).toThrow(/exact\/template ambiguity/i)
  })
})
