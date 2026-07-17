// @vitest-environment node

import { beforeEach, describe, expect, it, vi } from 'vitest'

const runtimeConfigState = vi.hoisted(() => ({ apiBase: 'http://agent.internal:8360' }))

vi.mock('nitropack/runtime', () => ({
  useRuntimeConfig: () => ({ apiBase: runtimeConfigState.apiBase }),
}))

import type { LaunchSafetyDecision } from '../types/launch'
import {
  createInternalSitemapFetcher,
  proxyGuardedSitemap,
  validateSitemapQuery,
  type InternalRawSitemapResponse,
  type RootSitemapDocument,
} from '../server/utils/launch/guardedSitemapProxy'

const fingerprint = 'a'.repeat(64)
const batch = 'a'.repeat(64)

const matchingDecision: LaunchSafetyDecision = {
  operational_state: 'selective-open',
  indexing_posture: 'selective-open',
  policy_fingerprint: fingerprint,
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
  sitemap_batch_revision: null,
  sitemap_action: 'guarded-proxy',
  reason: 'valid-two-key-unlock',
}

function upstreamFor(document: RootSitemapDocument = 'sitemap.xml'): InternalRawSitemapResponse {
  const headers: Record<string, string> = {
    'x-launch-policy-fingerprint': fingerprint,
    'x-launch-route-manifest-revision': 'launch-indexing-policy-v1',
    'x-launch-backend-policy-revision': 'index-policy-v1',
    'x-launch-sitemap-batch-revision': batch,
  }
  if (document !== 'sitemap-index.xml') headers['x-launch-sitemap-requested-batch'] = batch
  return { status: 200, body: `<urlset>${document}</urlset>`, headers }
}

function withHeader(upstream: InternalRawSitemapResponse, name: string, value: string): InternalRawSitemapResponse {
  return { ...upstream, headers: { ...upstream.headers, [name]: value } }
}

function withoutHeader(upstream: InternalRawSitemapResponse, name: string): InternalRawSitemapResponse {
  const headers = { ...upstream.headers }
  delete headers[name]
  return { ...upstream, headers }
}

function upstreamStatus(status: number): InternalRawSitemapResponse {
  return { status, body: '', headers: {} }
}

function urlFor(document: RootSitemapDocument, query: string): URL {
  return new URL(`https://vinhlong360.vn/${document}${query}`)
}

async function runGuardedProxy(input: {
  document: RootSitemapDocument
  query: string
  upstream: InternalRawSitemapResponse | Error
  decision?: LaunchSafetyDecision
}) {
  return proxyGuardedSitemap({
    event: {} as never,
    document: input.document,
    decision: input.decision ?? matchingDecision,
    url: urlFor(input.document, input.query),
    fetchRaw: vi.fn().mockImplementation(async () => {
      if (input.upstream instanceof Error) throw input.upstream
      return input.upstream
    }),
  })
}

describe('guarded Nuxt sitemap proxy', () => {
  it.each([
    ['sitemap.xml', `?batch=${batch}`, 200, null],
    ['sitemap.xml', '', 503, 'sitemap-batch-unavailable'],
    ['sitemap.xml', '?batch=ABC', 503, 'sitemap-batch-unavailable'],
    ['sitemap.xml', `?batch=${batch}&x=1`, 503, 'sitemap-batch-unavailable'],
    ['sitemap-media.xml', `?batch=${batch}`, 200, null],
    ['sitemap-index.xml', '', 200, null],
  ] as const)('guards %s %s', async (document, query, expected, failureReason) => {
    const response = await runGuardedProxy({ document, query, upstream: upstreamFor(document) })
    expect(response.status).toBe(expected)
    if (expected === 200) {
      expect(response.decision).toMatchObject({
        operational_state: 'selective-open',
        sitemap_batch_revision: batch,
      })
      expect(response.body).toContain(document)
      expect(response.failureReason).toBeNull()
    } else {
      expect(response).toMatchObject({
        status: 503,
        body: '',
        contentType: 'application/xml; charset=utf-8',
        decision: {
          operational_state: 'failed-open',
          policy_fingerprint: null,
          route_manifest_revision: null,
          backend_policy_revision: null,
          sitemap_batch_revision: null,
        },
        failureReason,
      })
    }
  })

  it.each([
    '?b%61tch=' + batch,
    '?%62atch=' + batch,
    '?batch%3D' + batch,
    '?batch=' + batch.toUpperCase(),
    '?batch=' + 'a'.repeat(63),
    '?batch=' + 'a'.repeat(65),
    '?batch=' + batch + '&',
    '?batch=' + batch + '&&',
    '?batch=' + batch + ';x=1',
    '?batch=' + batch + '&x=1',
    '?batch=' + batch + '&batch=' + batch,
    '?batch=' + batch + '&batch=',
    '?batch',
    '?batch=',
  ])('rejects non-canonical pinned query %s', async query => {
    const response = await runGuardedProxy({ document: 'sitemap.xml', query, upstream: upstreamFor() })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-batch-unavailable' })
  })

  it.each([
    ['sitemap.xml', `https://vinhlong360.vn/sitemap.xml/?batch=${batch}`],
    ['sitemap.xml', `https://vinhlong360.vn/sitemap-media.xml?batch=${batch}`],
    ['sitemap.xml', `https://vinhlong360.vn/sitemap.xml?batch=${batch}#fragment`],
    ['sitemap.xml', `https://vinhlong360.vn/sitemap.xml?batch=${batch}#`],
    ['sitemap-index.xml', 'https://vinhlong360.vn/sitemap-index.xml/'],
  ] as const)('rejects a non-canonical %s URL %s without fetching upstream', async (document, rawUrl) => {
    const fetchRaw = vi.fn().mockResolvedValue(upstreamFor(document))
    const response = await proxyGuardedSitemap({
      event: {} as never,
      document,
      decision: matchingDecision,
      url: new URL(rawUrl),
      fetchRaw,
    })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-batch-unavailable' })
    expect(fetchRaw).not.toHaveBeenCalled()
  })

  it.each([
    '?batch=' + batch,
    '?x=1',
    '?batch=' + batch + '&x=1',
  ])('rejects any active index query %s', async query => {
    const response = await runGuardedProxy({
      document: 'sitemap-index.xml',
      query,
      upstream: upstreamFor('sitemap-index.xml'),
    })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-batch-unavailable' })
  })

  it.each([
    ['x-launch-policy-fingerprint', 'f'.repeat(64)],
    ['x-launch-route-manifest-revision', 'stale-route-v0'],
    ['x-launch-backend-policy-revision', 'stale-policy-v0'],
    ['x-launch-sitemap-batch-revision', 'b'.repeat(64)],
    ['x-launch-sitemap-requested-batch', 'b'.repeat(64)],
  ] as const)('fails closed when %s mismatches', async (header, value) => {
    const response = await runGuardedProxy({
      document: 'sitemap.xml',
      query: `?batch=${batch}`,
      upstream: withHeader(upstreamFor(), header, value),
    })
    expect(response).toMatchObject({
      status: 503,
      decision: {
        operational_state: 'failed-open',
        policy_fingerprint: null,
        route_manifest_revision: null,
        backend_policy_revision: null,
        sitemap_batch_revision: null,
      },
      failureReason: 'sitemap-evidence-mismatch',
    })
  })

  it.each([
    ['backend 404', upstreamStatus(404)],
    ['backend 503 / no active bundle', upstreamStatus(503)],
    ['backend 500', upstreamStatus(500)],
    ['transport rejection', new Error('connect failed')],
  ] as const)('classifies %s as unavailable', async (_name, upstream) => {
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-batch-unavailable' })
    expect(response.decision.reason).toBe('sitemap-batch-unavailable')
  })

  it('classifies a pinned served-batch mismatch as evidence mismatch', async () => {
    const upstream = withHeader(
      withHeader(upstreamFor(), 'x-launch-sitemap-requested-batch', batch),
      'x-launch-sitemap-batch-revision', 'b'.repeat(64),
    )
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-evidence-mismatch' })
  })

  it.each([
    ['missing fingerprint', withoutHeader(upstreamFor(), 'x-launch-policy-fingerprint')],
    ['malformed fingerprint', withHeader(upstreamFor(), 'x-launch-policy-fingerprint', 'not-a-digest')],
    ['missing route revision', withoutHeader(upstreamFor(), 'x-launch-route-manifest-revision')],
    ['missing backend revision', withoutHeader(upstreamFor(), 'x-launch-backend-policy-revision')],
    ['malformed batch revision', withHeader(upstreamFor(), 'x-launch-sitemap-batch-revision', 'ABC')],
    ['missing requested-batch echo', withoutHeader(upstreamFor(), 'x-launch-sitemap-requested-batch')],
  ] as const)('classifies %s as evidence mismatch', async (_name, upstream) => {
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-evidence-mismatch' })
  })

  it('requires no requested-batch echo for the active index', async () => {
    const response = await runGuardedProxy({
      document: 'sitemap-index.xml',
      query: '',
      upstream: withHeader(upstreamFor('sitemap-index.xml'), 'x-launch-sitemap-requested-batch', batch),
    })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-evidence-mismatch' })
  })

  it('rejects even an empty requested-batch echo for the active index', async () => {
    const response = await runGuardedProxy({
      document: 'sitemap-index.xml',
      query: '',
      upstream: withHeader(upstreamFor('sitemap-index.xml'), 'x-launch-sitemap-requested-batch', ''),
    })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-evidence-mismatch' })
  })

  it.each([
    ['case-duplicate', {
      ...upstreamFor().headers,
      'X-Launch-Policy-Fingerprint': fingerprint,
    }],
    ['comma-joined duplicate', {
      ...upstreamFor().headers,
      'x-launch-policy-fingerprint': `${fingerprint}, ${fingerprint}`,
    }],
    ['trimmed variant', {
      ...upstreamFor().headers,
      'x-launch-policy-fingerprint': ` ${fingerprint}`,
    }],
    ['array value', {
      ...upstreamFor().headers,
      'x-launch-policy-fingerprint': [fingerprint],
    }],
  ])('rejects %s launch evidence headers', async (_name, headers) => {
    const upstream = { ...upstreamFor(), headers } as unknown as InternalRawSitemapResponse
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream })
    expect(response).toMatchObject({ status: 503, failureReason: 'sitemap-evidence-mismatch' })
  })

  it('does not forward upstream launch headers in the proxy result', async () => {
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream: upstreamFor() })
    expect(response.status).toBe(200)
    expect(response).not.toHaveProperty('headers')
  })

  it('returns the refined successful decision as an immutable object', async () => {
    const response = await runGuardedProxy({ document: 'sitemap.xml', query: `?batch=${batch}`, upstream: upstreamFor() })
    expect(Object.isFrozen(response.decision)).toBe(true)
    expect(response.decision).not.toBe(matchingDecision)
  })

  it('snapshots the decision before awaiting transport', async () => {
    let release!: (value: InternalRawSitemapResponse) => void
    const pending = new Promise<InternalRawSitemapResponse>((resolve) => { release = resolve })
    const mutableDecision = { ...matchingDecision }
    const responsePromise = proxyGuardedSitemap({
      event: {} as never,
      document: 'sitemap.xml',
      decision: mutableDecision,
      url: urlFor('sitemap.xml', `?batch=${batch}`),
      fetchRaw: vi.fn().mockReturnValue(pending),
    })

    mutableDecision.policy_fingerprint = 'b'.repeat(64)
    mutableDecision.route_manifest_revision = 'mutated-route'
    release(upstreamFor())

    await expect(responsePromise).resolves.toMatchObject({
      status: 200,
      decision: {
        policy_fingerprint: fingerprint,
        route_manifest_revision: 'launch-indexing-policy-v1',
      },
    })
  })
})

describe('sitemap query validation', () => {
  it('accepts only the empty active index query', () => {
    expect(validateSitemapQuery('sitemap-index.xml', new URL('https://example.test/sitemap-index.xml')))
      .toEqual({ requestedBatch: null })
  })

  it('accepts only a lowercase hexadecimal pinned batch', () => {
    expect(validateSitemapQuery('sitemap-media.xml', new URL(`https://example.test/sitemap-media.xml?batch=${batch}`)))
      .toEqual({ requestedBatch: batch })
  })
})

describe('internal sitemap fetcher', () => {
  beforeEach(() => {
    runtimeConfigState.apiBase = 'http://agent.internal:8360'
  })

  it('uses private runtime apiBase, exact internal route, canonical query, and manual redirects', async () => {
    const rawFetcher = vi.fn().mockResolvedValue({
      status: 200,
      _data: '<xml/>',
      headers: new Headers({
        'X-Launch-Policy-Fingerprint': fingerprint,
        'X-Launch-Route-Manifest-Revision': 'launch-indexing-policy-v1',
      }),
    })
    runtimeConfigState.apiBase = 'http://agent.internal:8360/'

    const fetchRaw = createInternalSitemapFetcher({} as never, rawFetcher)
    await expect(fetchRaw('sitemap.xml', batch)).resolves.toMatchObject({ status: 200, body: '<xml/>' })
    expect(rawFetcher).toHaveBeenCalledWith(
      `http://agent.internal:8360/_internal/launch-sitemaps/sitemap.xml?batch=${batch}`,
      expect.objectContaining({
        method: 'GET',
        redirect: 'manual',
        responseType: 'text',
        ignoreResponseError: true,
        retry: false,
        headers: { accept: 'application/xml' },
      }),
    )
    expect(rawFetcher.mock.calls[0]?.[1]).not.toHaveProperty('headers.cookie')
    expect(rawFetcher.mock.calls[0]?.[1]).not.toHaveProperty('headers.authorization')
  })

  it('never follows a redirect and returns normalized response headers', async () => {
    const rawFetcher = vi.fn().mockResolvedValue({
      status: 302,
      _data: '',
      headers: new Headers({ Location: 'https://public.example.test/sitemap.xml' }),
    })
    const fetchRaw = createInternalSitemapFetcher({} as never, rawFetcher)

    await expect(fetchRaw('sitemap-index.xml', null)).resolves.toMatchObject({
      status: 302,
      headers: { location: 'https://public.example.test/sitemap.xml' },
    })
    expect(rawFetcher.mock.calls[0]?.[0]).toBe('http://agent.internal:8360/_internal/launch-sitemaps/sitemap-index.xml')
    expect(rawFetcher.mock.calls[0]?.[1]).toMatchObject({ redirect: 'manual' })
  })

  it.each([
    '',
    'agent.internal:8360',
    'ftp://agent.internal',
    'http://user:secret@agent.internal:8360',
    'http://agent.internal:8360/api',
    'http://agent.internal:8360?x=1',
    'http://agent.internal:8360#fragment',
  ])('rejects unsafe private apiBase %s only when fetching', async apiBase => {
    runtimeConfigState.apiBase = apiBase
    const rawFetcher = vi.fn()
    const fetchRaw = createInternalSitemapFetcher({} as never, rawFetcher)

    await expect(fetchRaw('sitemap-index.xml', null)).rejects.toThrow(/apiBase/i)
    expect(rawFetcher).not.toHaveBeenCalled()
  })
})
