// @vitest-environment node

import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import { finalizeLaunchResponse } from '../server/plugins/launch-response'
import {
  EMPTY_MEDIA_URLSET,
  EMPTY_SITEMAP_INDEX,
  EMPTY_URLSET,
  ROBOTS_CONTENT_TYPE,
  XML_CONTENT_TYPE,
  buildLaunchRobotsBody,
  createRootRobotsHandler,
  createRootSitemapHandler,
} from '../server/utils/launch/rootSeoBodies'
import { launchRouteManifest } from '../server/utils/launch/launchRouteManifest'
import type {
  InternalRawFetcher,
  RootSitemapDocument,
} from '../server/utils/launch/guardedSitemapProxy'
import type { LaunchSafetyDecision } from '../types/launch'

const batch = 'a'.repeat(64)
const fingerprint = 'b'.repeat(64)

const closedDecision: Readonly<LaunchSafetyDecision> = Object.freeze({
  operational_state: 'closed',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'closed-empty',
  reason: 'closed-default',
})

const selectiveOpenDecision: Readonly<LaunchSafetyDecision> = Object.freeze({
  operational_state: 'selective-open',
  indexing_posture: 'selective-open',
  policy_fingerprint: fingerprint,
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
  sitemap_batch_revision: null,
  sitemap_action: 'guarded-proxy',
  reason: 'valid-two-key-unlock',
})

const failedOpenDecision: Readonly<LaunchSafetyDecision> = Object.freeze({
  operational_state: 'failed-open',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'unavailable',
  reason: 'policy-attestation-unavailable',
})

type HeaderValue = string | number | readonly string[]

class ResponseStub {
  statusCode = 200
  private readonly headers = new Map<string, HeaderValue>()

  constructor(headers: Record<string, HeaderValue> = {}) {
    for (const [name, value] of Object.entries(headers)) this.headers.set(name, value)
  }

  getHeaders(): Record<string, HeaderValue> {
    return Object.fromEntries(this.headers)
  }

  getHeader(name: string): HeaderValue | undefined {
    const lower = name.toLowerCase()
    return [...this.headers].find(([candidate]) => candidate.toLowerCase() === lower)?.[1]
  }

  setHeader(name: string, value: HeaderValue): void {
    const lower = name.toLowerCase()
    for (const candidate of [...this.headers.keys()]) {
      if (candidate.toLowerCase() === lower) this.headers.delete(candidate)
    }
    this.headers.set(name, value)
  }

  removeHeader(name: string): void {
    const lower = name.toLowerCase()
    for (const candidate of [...this.headers.keys()]) {
      if (candidate.toLowerCase() === lower) this.headers.delete(candidate)
    }
  }
}

function rootEvent(path: string, decision?: Readonly<LaunchSafetyDecision>) {
  const response = new ResponseStub({
    'Cache-Control': 'public, max-age=3600',
    'X-Robots-Tag': 'stale',
    'X-Launch-Sitemap-Batch-Revision': 'stale',
    'X-Launch-Sitemap-Requested-Batch': 'stale',
  })
  return {
    path,
    method: 'GET',
    context: decision ? { launchSafety: decision } : {},
    node: {
      req: {
        method: 'GET',
        url: path,
        originalUrl: path,
        headers: {
          accept: '*/*',
          host: 'vinhlong360.vn',
          'x-forwarded-proto': 'https',
        },
      },
      res: response,
    },
  }
}

function lowerHeaders(event: ReturnType<typeof rootEvent>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(event.node.res.getHeaders()).map(([name, value]) => [name.toLowerCase(), String(value)]),
  )
}

function expectClosedHeaders(event: ReturnType<typeof rootEvent>, contentType: string): void {
  expect(lowerHeaders(event)).toEqual({
    'cache-control': 'no-store',
    'content-type': contentType,
    'x-launch-indexing-policy': 'closed',
  })
}

function expectFailedOpenHeaders(event: ReturnType<typeof rootEvent>, contentType: string): void {
  expect(lowerHeaders(event)).toEqual({
    'cache-control': 'no-store',
    'content-type': contentType,
    'x-launch-indexing-policy': 'failed-open',
  })
}

function upstreamFor(document: RootSitemapDocument): ReturnType<InternalRawFetcher> {
  const requestedBatch = document === 'sitemap-index.xml' ? null : batch
  return Promise.resolve({
    status: 200,
    body: `<${document}>validated</${document}>`,
    headers: {
      'x-launch-policy-fingerprint': fingerprint,
      'x-launch-route-manifest-revision': 'launch-indexing-policy-v1',
      'x-launch-backend-policy-revision': 'index-policy-v1',
      'x-launch-sitemap-batch-revision': batch,
      ...(requestedBatch === null ? {} : { 'x-launch-sitemap-requested-batch': requestedBatch }),
    },
  })
}

const sitemapCases = [
  ['sitemap.xml', `?batch=${batch}`, EMPTY_URLSET],
  ['sitemap-media.xml', `?batch=${batch}`, EMPTY_MEDIA_URLSET],
  ['sitemap-index.xml', '', EMPTY_SITEMAP_INDEX],
] as const satisfies ReadonlyArray<readonly [RootSitemapDocument, string, string]>

describe('Nuxt-owned root SEO endpoints', () => {
  it.each(sitemapCases)('serves exact closed %s without constructing or calling a backend fetcher', async (
    document,
    query,
    closedBody,
  ) => {
    const createFetcher = vi.fn<() => InternalRawFetcher>(() => vi.fn())
    const proxySitemap = vi.fn()
    const handler = createRootSitemapHandler(document, { createFetcher, proxySitemap })
    const event = rootEvent(`/${document}${query}`, closedDecision)

    await expect(handler(event as never)).resolves.toBe(closedBody)

    expect(event.node.res.statusCode).toBe(200)
    expectClosedHeaders(event, XML_CONTENT_TYPE)
    expect(createFetcher).not.toHaveBeenCalled()
    expect(proxySitemap).not.toHaveBeenCalled()
    expect(event.context).toMatchObject({
      launchResponseHeaderInput: {
        decision: closedDecision,
        sitemap: true,
        requestedBatch: null,
      },
    })

    finalizeLaunchResponse(event as never)
    expectClosedHeaders(event, XML_CONTENT_TYPE)
    expect(event.context).toMatchObject({
      launchResponseHeaderInput: {
        decision: closedDecision,
        sitemap: true,
        requestedBatch: null,
      },
    })
  })

  it.each(sitemapCases)('returns %s unavailable from a failed-open middleware decision', async (
    document,
    query,
  ) => {
    const createFetcher = vi.fn<() => InternalRawFetcher>(() => vi.fn())
    const proxySitemap = vi.fn()
    const handler = createRootSitemapHandler(document, { createFetcher, proxySitemap })
    const event = rootEvent(`/${document}${query}`, failedOpenDecision)

    await expect(handler(event as never)).resolves.toBe('')

    expect(event.node.res.statusCode).toBe(503)
    expectFailedOpenHeaders(event, XML_CONTENT_TYPE)
    expect(event.context.launchSafety).toBe(failedOpenDecision)
    expect(createFetcher).not.toHaveBeenCalled()
    expect(proxySitemap).not.toHaveBeenCalled()
  })

  it.each(sitemapCases)('proxies and validates selective-open %s with the actual request URL', async (
    document,
    query,
  ) => {
    const fetchRaw = vi.fn<InternalRawFetcher>(upstreamFor)
    const createFetcher = vi.fn(() => fetchRaw)
    const handler = createRootSitemapHandler(document, { createFetcher })
    const event = rootEvent(`/${document}${query}`, selectiveOpenDecision)

    await expect(handler(event as never)).resolves.toBe(`<${document}>validated</${document}>`)

    expect(event.node.res.statusCode).toBe(200)
    expect(createFetcher).toHaveBeenCalledOnce()
    expect(fetchRaw).toHaveBeenCalledWith(document, document === 'sitemap-index.xml' ? null : batch)
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'selective-open',
      sitemap_batch_revision: batch,
    })
    const expected = {
      'cache-control': 'no-store',
      'content-type': XML_CONTENT_TYPE,
      'x-launch-backend-policy-revision': 'index-policy-v1',
      'x-launch-indexing-policy': 'selective-open',
      'x-launch-policy-fingerprint': fingerprint,
      'x-launch-route-manifest-revision': 'launch-indexing-policy-v1',
      'x-launch-sitemap-batch-revision': batch,
      ...(document === 'sitemap-index.xml' ? {} : { 'x-launch-sitemap-requested-batch': batch }),
    }
    expect(lowerHeaders(event)).toEqual(expected)

    finalizeLaunchResponse(event as never)
    expect(lowerHeaders(event)).toEqual(expected)
    expect(event.context).toMatchObject({
      launchResponseHeaderInput: {
        decision: event.context.launchSafety,
        sitemap: true,
        requestedBatch: document === 'sitemap-index.xml' ? null : batch,
      },
    })
  })

  it.each([
    ['sitemap.xml', ''],
    ['sitemap.xml', '?batch=ABC'],
    ['sitemap.xml', `?batch=${batch}&extra=1`],
    ['sitemap-media.xml', ''],
    ['sitemap-media.xml', `?batch=${batch}&extra=1`],
    ['sitemap-index.xml', `?batch=${batch}`],
    ['sitemap-index.xml', '?extra=1'],
  ] as const)('fails invalid selective-open query protocol for %s%s before backend I/O', async (document, query) => {
    const fetchRaw = vi.fn<InternalRawFetcher>(upstreamFor)
    const handler = createRootSitemapHandler(document, { createFetcher: () => fetchRaw })
    const event = rootEvent(`/${document}${query}`, selectiveOpenDecision)

    await expect(handler(event as never)).resolves.toBe('')

    expect(event.node.res.statusCode).toBe(503)
    expectFailedOpenHeaders(event, XML_CONTENT_TYPE)
    expect(fetchRaw).not.toHaveBeenCalled()
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'failed-open',
      sitemap_action: 'unavailable',
      reason: 'sitemap-batch-unavailable',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
    })
  })

  it.each(sitemapCases)('clears all evidence when selective-open %s transport fails', async (document, query) => {
    const fetchRaw = vi.fn<InternalRawFetcher>().mockRejectedValue(new Error('transport unavailable'))
    const handler = createRootSitemapHandler(document, { createFetcher: () => fetchRaw })
    const event = rootEvent(`/${document}${query}`, selectiveOpenDecision)

    await expect(handler(event as never)).resolves.toBe('')

    expect(event.node.res.statusCode).toBe(503)
    expectFailedOpenHeaders(event, XML_CONTENT_TYPE)
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'failed-open',
      reason: 'sitemap-batch-unavailable',
    })
  })

  it('clears all evidence and requested-batch echo when upstream evidence mismatches', async () => {
    const fetchRaw = vi.fn<InternalRawFetcher>().mockResolvedValue({
      status: 200,
      body: '<urlset>stale</urlset>',
      headers: {
        'x-launch-policy-fingerprint': fingerprint,
        'x-launch-route-manifest-revision': 'launch-indexing-policy-v1',
        'x-launch-backend-policy-revision': 'index-policy-v1',
        'x-launch-sitemap-batch-revision': batch,
        'x-launch-sitemap-requested-batch': 'c'.repeat(64),
      },
    })
    const handler = createRootSitemapHandler('sitemap.xml', { createFetcher: () => fetchRaw })
    const event = rootEvent(`/sitemap.xml?batch=${batch}`, selectiveOpenDecision)

    await expect(handler(event as never)).resolves.toBe('')

    expect(event.node.res.statusCode).toBe(503)
    expectFailedOpenHeaders(event, XML_CONTENT_TYPE)
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'failed-open',
      reason: 'sitemap-evidence-mismatch',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
    })
  })

  it('fails missing middleware context unavailable without backend I/O', async () => {
    const fetchRaw = vi.fn<InternalRawFetcher>(upstreamFor)
    const handler = createRootSitemapHandler('sitemap-index.xml', { createFetcher: () => fetchRaw })
    const event = rootEvent('/sitemap-index.xml')

    await expect(handler(event as never)).resolves.toBe('')

    expect(event.node.res.statusCode).toBe(503)
    expectFailedOpenHeaders(event, XML_CONTENT_TYPE)
    expect(fetchRaw).not.toHaveBeenCalled()
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'failed-open',
      sitemap_action: 'unavailable',
    })
  })

  it.each([
    ['closed', closedDecision, false],
    ['selective-open', selectiveOpenDecision, true],
    ['failed-open', failedOpenDecision, false],
  ] as const)('serves deterministic %s robots with manifest-sensitive blocks', async (_state, decision, discoverable) => {
    const handler = createRootRobotsHandler()
    const event = rootEvent('/robots.txt', decision)
    const expectedBody = buildLaunchRobotsBody(decision)

    expect(handler(event as never)).toBe(expectedBody)

    expect(event.node.res.statusCode).toBe(200)
    expect(lowerHeaders(event)).toEqual({
      'cache-control': 'no-store',
      'content-type': ROBOTS_CONTENT_TYPE,
      'x-launch-indexing-policy': decision.operational_state,
      ...(discoverable
        ? {
            'x-launch-backend-policy-revision': 'index-policy-v1',
            'x-launch-policy-fingerprint': fingerprint,
            'x-launch-route-manifest-revision': 'launch-indexing-policy-v1',
          }
        : {}),
    })
    expect(expectedBody).toContain('User-agent: *\nAllow: /')
    expect(expectedBody).toContain('Crawl-delay: 2')
    expect(expectedBody).toContain('Host: https://vinhlong360.vn')
    expect((expectedBody.match(/^Sitemap: https:\/\/vinhlong360\.vn\/sitemap-index\.xml$/gmu) ?? []))
      .toHaveLength(discoverable ? 1 : 0)

    const groups = ['*', 'Googlebot', 'GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended']
    for (const [index, agent] of groups.entries()) {
      const nextAgent = groups[index + 1]
      const start = expectedBody.indexOf(`User-agent: ${agent}\n`)
      const end = nextAgent ? expectedBody.indexOf(`User-agent: ${nextAgent}\n`, start) : expectedBody.length
      const group = expectedBody.slice(start, end)
      expect(start).toBeGreaterThanOrEqual(0)
      expect(group).toContain('Allow: /')
      for (const { prefix } of launchRouteManifest.sensitive_prefixes) {
        expect(group).toContain(`Disallow: ${prefix}\n`)
      }
    }
  })

  it('uses the exact closed XML constants', () => {
    expect(EMPTY_URLSET).toBe('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
    expect(EMPTY_MEDIA_URLSET).toBe('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>')
    expect(EMPTY_SITEMAP_INDEX).toBe('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>')
  })

  it('owns each root SEO path exactly once and leaves no legacy root proxy routeRule', () => {
    const configSource = readFileSync(resolve(process.cwd(), 'nuxt.config.ts'), 'utf8')
    const routesRoot = resolve(process.cwd(), 'server/routes')
    const routeFiles = readdirSync(routesRoot, { recursive: true, withFileTypes: true })
      .filter(entry => entry.isFile())
      .map(entry => resolve(entry.parentPath, entry.name))
    const documents = ['robots.txt', 'sitemap.xml', 'sitemap-media.xml', 'sitemap-index.xml']

    for (const document of documents) {
      expect(configSource).not.toMatch(new RegExp(`['\"]/${document.replaceAll('.', '\\.') }['\"]\\s*:\\s*\\{[^}]*\\bproxy\\s*:`))
      const routePattern = new RegExp(`(?:^|[\\\\/])${document.replaceAll('.', '\\.')}(?:\\.get)?\\.ts$`)
      expect(routeFiles.filter(path => routePattern.test(path))).toEqual([
        resolve(routesRoot, `${document}.ts`),
      ])
    }
  })
})
