// @vitest-environment node

import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import launchSafetyMiddleware, {
  launchBuildEvidence,
  resolveRequestLaunchSafety,
} from '../server/middleware/launch-safety'
import launchResponsePlugin, {
  finalizeLaunchResponse,
} from '../server/plugins/launch-response'
import {
  buildBaseLaunchResponseHeaders,
  buildLaunchResponseHeaders,
  writeLaunchResponseHeaders,
} from '../server/utils/launch/launchHeaders'
import type { LaunchPageDecision, LaunchSafetyDecision } from '../types/launch'

const batch = 'a'.repeat(64)
const fingerprint = 'b'.repeat(64)

const closedDecision: LaunchSafetyDecision = {
  operational_state: 'closed',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'closed-empty',
  reason: 'closed-default',
}

const selectiveOpenDecision: LaunchSafetyDecision = {
  operational_state: 'selective-open',
  indexing_posture: 'selective-open',
  policy_fingerprint: fingerprint,
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
  sitemap_batch_revision: null,
  sitemap_action: 'guarded-proxy',
  reason: 'valid-two-key-unlock',
}

const failedOpenDecision: LaunchSafetyDecision = {
  operational_state: 'failed-open',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'unavailable',
  reason: 'policy-attestation-unavailable',
}

const selectiveOpenPageDecision: LaunchPageDecision = {
  ...selectiveOpenDecision,
  robots: 'index, follow',
  sitemapDiscovery: true,
}

const selectiveNegativePageDecision: LaunchPageDecision = {
  ...selectiveOpenDecision,
  robots: 'noindex, follow',
  sitemapDiscovery: true,
}

const failedOpenPageDecision: LaunchPageDecision = {
  ...failedOpenDecision,
  robots: 'noindex, follow',
  sitemapDiscovery: false,
}

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
    this.headers.delete(name)
  }
}

function responseEvent(input: {
  path?: string
  method?: string
  accept?: string
  status?: number
  headers?: Record<string, HeaderValue>
  context?: Record<string, unknown>
} = {}) {
  const response = new ResponseStub(input.headers)
  response.statusCode = input.status ?? 200
  const path = input.path ?? '/du-lich'
  const accept = input.accept ?? 'text/html'
  return {
    path,
    method: input.method ?? 'GET',
    context: { ...(input.context ?? {}) },
    node: {
      req: {
        method: input.method ?? 'GET',
        url: path,
        headers: { accept },
      },
      res: response,
    },
  }
}

function stringHeaders(event: ReturnType<typeof responseEvent>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(event.node.res.getHeaders()).map(([name, value]) => [name, String(value)]),
  )
}

function lowerHeaders(event: ReturnType<typeof responseEvent>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(stringHeaders(event)).map(([name, value]) => [name.toLowerCase(), value]),
  )
}

describe('exact launch response header authority', () => {
  it.each([
    [closedDecision, 'closed', false],
    [selectiveOpenDecision, 'selective-open', true],
    [failedOpenDecision, 'failed-open', false],
  ] as const)('builds exact %s policy headers', (decision, policy, hasEvidence) => {
    const headers = buildBaseLaunchResponseHeaders({ decision })

    expect(headers['Cache-Control']).toBe('no-store')
    expect(headers['X-Launch-Indexing-Policy']).toBe(policy)
    expect(Boolean(headers['X-Launch-Policy-Fingerprint'])).toBe(hasEvidence)
    expect(Object.keys(headers).sort()).toEqual(hasEvidence
      ? [
          'Cache-Control',
          'X-Launch-Backend-Policy-Revision',
          'X-Launch-Indexing-Policy',
          'X-Launch-Policy-Fingerprint',
          'X-Launch-Route-Manifest-Revision',
        ].sort()
      : ['Cache-Control', 'X-Launch-Indexing-Policy'].sort())
  })

  it('emits sitemap batch and requested-batch evidence only when both are validated', () => {
    const decision = { ...selectiveOpenDecision, sitemap_batch_revision: batch }

    expect(buildBaseLaunchResponseHeaders({ decision, sitemap: true })).toMatchObject({
      'X-Launch-Sitemap-Batch-Revision': batch,
    })
    expect(buildBaseLaunchResponseHeaders({ decision, sitemap: true, requestedBatch: batch })).toMatchObject({
      'X-Launch-Sitemap-Batch-Revision': batch,
      'X-Launch-Sitemap-Requested-Batch': batch,
    })
    expect(() => buildBaseLaunchResponseHeaders({
      decision: { ...decision, sitemap_batch_revision: null },
      sitemap: true,
    })).toThrow(/validated sitemap batch/i)
    expect(() => buildBaseLaunchResponseHeaders({
      decision,
      sitemap: true,
      requestedBatch: 'A'.repeat(64),
    })).toThrow(/requested sitemap batch/i)
    expect(() => buildBaseLaunchResponseHeaders({
      decision,
      sitemap: true,
      requestedBatch: 'c'.repeat(64),
    })).toThrow(/match the served batch/i)
    expect(() => buildBaseLaunchResponseHeaders({
      decision,
      requestedBatch: batch,
    })).toThrow(/requested sitemap batch/i)
  })

  it('adds robots only for HTML and mirrors the page decision exactly', () => {
    expect(buildLaunchResponseHeaders({
      decision: selectiveOpenPageDecision,
      html: true,
    })).toMatchObject({
      'X-Launch-Indexing-Policy': 'selective-open',
      'X-Robots-Tag': 'index, follow',
    })
    expect(buildLaunchResponseHeaders({
      decision: selectiveNegativePageDecision,
      html: true,
    })['X-Robots-Tag']).toBe('noindex, follow')
    expect(buildLaunchResponseHeaders({
      decision: selectiveOpenPageDecision,
    })).not.toHaveProperty('X-Robots-Tag')
  })

  it.each([
    { ...selectiveOpenDecision, policy_fingerprint: null },
    { ...selectiveOpenDecision, policy_fingerprint: 'B'.repeat(64) },
    { ...selectiveOpenDecision, route_manifest_revision: 'launch-indexing-policy-v0' },
    { ...selectiveOpenDecision, backend_policy_revision: 'index-policy-v0' },
    { ...selectiveOpenDecision, indexing_posture: 'closed' },
    { ...selectiveOpenDecision, reason: 'policy-mismatch' },
  ])('strictly rejects malformed selective-open decisions', (decision) => {
    expect(() => buildBaseLaunchResponseHeaders({ decision: decision as LaunchSafetyDecision }))
      .toThrow(/selective-open decision/i)
  })

  it.each([
    { ...closedDecision, reason: 'valid-two-key-unlock' },
    { ...closedDecision, policy_fingerprint: fingerprint },
    { ...closedDecision, sitemap_batch_revision: batch },
    { ...failedOpenDecision, reason: 'closed-default' },
    { ...failedOpenDecision, route_manifest_revision: 'launch-indexing-policy-v1' },
    { ...failedOpenDecision, sitemap_batch_revision: batch },
  ])('rejects closed/failed-open decisions with inconsistent reasons or stale evidence', (decision) => {
    expect(() => buildBaseLaunchResponseHeaders({ decision: decision as LaunchSafetyDecision }))
      .toThrow(/decision/i)
  })

  it('clears case-insensitive stale evidence and robots before safely downgrading malformed input', () => {
    const event = responseEvent({
      headers: {
        'x-launch-policy-fingerprint': 'stale-one',
        'X-LAUNCH-POLICY-FINGERPRINT': 'stale-two',
        'X-Launch-Route-Manifest-Revision': 'stale',
        'x-launch-backend-policy-revision': 'stale',
        'X-Launch-Sitemap-Batch-Revision': 'c'.repeat(64),
        'x-launch-sitemap-requested-batch': 'c'.repeat(64),
        'x-robots-tag': 'stale-one',
        'X-ROBOTS-TAG': 'stale-two',
      },
    })

    expect(() => writeLaunchResponseHeaders(event as never, {
      decision: { ...selectiveOpenDecision, policy_fingerprint: null },
      sitemap: true,
    })).not.toThrow()

    expect(lowerHeaders(event)).toEqual({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
    })
  })

  it('sets each public header once even when invoked repeatedly', () => {
    const event = responseEvent()
    writeLaunchResponseHeaders(event as never, { decision: selectiveOpenDecision })
    writeLaunchResponseHeaders(event as never, { decision: selectiveOpenDecision })

    const names = Object.keys(event.node.res.getHeaders()).map(name => name.toLowerCase())
    expect(names).toHaveLength(new Set(names).size)
    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'selective-open',
      'x-launch-policy-fingerprint': fingerprint,
    })
  })
})

describe('request-scoped launch decision middleware', () => {
  it('uses the exact raw canonical artifact bytes for build evidence', () => {
    const route = readFileSync(resolve(process.cwd(), '../config/launch-indexing-policy.json'))
    const disclosure = readFileSync(resolve(process.cwd(), '../config/ai-disclosure.json'))

    expect(launchBuildEvidence).toEqual({
      routeRevision: 'launch-indexing-policy-v1',
      routeDigest: createHash('sha256').update(route).digest('hex'),
      disclosureRevision: 'ai-disclosure-v1',
      disclosureDigest: createHash('sha256').update(disclosure).digest('hex'),
    })
    expect(Object.isFrozen(launchBuildEvidence)).toBe(true)
  })

  it('stores an immutable closed decision without making a backend call', async () => {
    const event = responseEvent()
    const fetchAttestation = vi.fn()

    const decision = await resolveRequestLaunchSafety(event as never, {
      env: {},
      build: launchBuildEvidence,
      fetchAttestation,
    })

    expect(decision).toMatchObject({ operational_state: 'closed', reason: 'closed-default' })
    expect(Object.isFrozen(decision)).toBe(true)
    expect(event.context.launchSafety).toBe(decision)
    expect(fetchAttestation).not.toHaveBeenCalled()
  })

  it('does not resolve or attest assets, API calls, or non-GET requests', async () => {
    for (const event of [
      responseEvent({ path: '/_nuxt/app.js', accept: '*/*' }),
      responseEvent({ path: '/api/entities', accept: 'application/json' }),
      responseEvent({ path: '/du-lich', method: 'POST' }),
    ]) {
      const fetchAttestation = vi.fn()
      await resolveRequestLaunchSafety(event as never, {
        env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
        build: launchBuildEvidence,
        fetchAttestation,
      })
      expect(event.context).not.toHaveProperty('launchSafety')
      expect(fetchAttestation).not.toHaveBeenCalled()
    }
  })

  it('keeps concurrent request decisions isolated without shared mutable state', async () => {
    const first = responseEvent({ path: '/du-lich' })
    const second = responseEvent({ path: '/san-pham' })
    let releaseFirst!: () => void
    const firstBlocked = new Promise<void>((resolvePromise) => { releaseFirst = resolvePromise })

    const firstRun = resolveRequestLaunchSafety(first as never, {
      env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
      build: launchBuildEvidence,
      fetchAttestation: async () => {
        await firstBlocked
        throw new Error('first unavailable')
      },
    })
    const secondRun = resolveRequestLaunchSafety(second as never, {
      env: {},
      build: launchBuildEvidence,
      fetchAttestation: vi.fn(),
    })

    await expect(secondRun).resolves.toMatchObject({ operational_state: 'closed' })
    expect(first.context.launchSafety).toMatchObject({ operational_state: 'failed-open' })
    expect(second.context.launchSafety).toMatchObject({ operational_state: 'closed' })
    releaseFirst()
    await expect(firstRun).resolves.toMatchObject({ operational_state: 'failed-open' })
    expect(first.context.launchSafety).not.toBe(second.context.launchSafety)
  })

  it('allocates a distinct immutable fallback before each concurrent attestation await', async () => {
    const first = responseEvent({ path: '/du-lich' })
    const second = responseEvent({ path: '/san-pham' })
    let release!: () => void
    const blocked = new Promise<void>((resolvePromise) => { release = resolvePromise })
    const dependencies = {
      env: { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' },
      build: launchBuildEvidence,
      fetchAttestation: async () => {
        await blocked
        throw new Error('unavailable')
      },
    }

    const firstRun = resolveRequestLaunchSafety(first as never, dependencies)
    const secondRun = resolveRequestLaunchSafety(second as never, dependencies)
    expect(Object.isFrozen(first.context.launchSafety)).toBe(true)
    expect(Object.isFrozen(second.context.launchSafety)).toBe(true)
    expect(first.context.launchSafety).not.toBe(second.context.launchSafety)

    release()
    await Promise.all([firstRun, secondRun])
  })

  it('provides the default event handler without cross-request state', async () => {
    const event = responseEvent()
    await launchSafetyMiddleware(event as never)
    expect(event.context.launchSafety).toMatchObject({ operational_state: 'closed' })
  })
})

describe('final response lifecycle', () => {
  it.each([
    ['success HTML', 200, selectiveOpenPageDecision, 'selective-open', 'index, follow'],
    ['valid-negative HTML', 200, selectiveNegativePageDecision, 'selective-open', 'noindex, follow'],
    ['404 HTML', 404, selectiveOpenPageDecision, 'selective-open', 'noindex, follow'],
    ['error HTML', 500, failedOpenPageDecision, 'failed-open', 'noindex, follow'],
  ] as const)('finalizes %s after the final status without dropping valid evidence', (_label, status, decision, policy, robots) => {
    const event = responseEvent({
      status,
      headers: { 'content-type': 'text/html; charset=utf-8', 'X-Robots-Tag': 'stale' },
      context: { launchSafety: decision },
    })

    expect(() => finalizeLaunchResponse(event as never)).not.toThrow()
    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': policy,
      'x-robots-tag': robots,
    })
    if (decision.operational_state === 'selective-open') {
      expect(lowerHeaders(event)['x-launch-policy-fingerprint']).toBe(fingerprint)
    }
    expect(event.context.launchSafety).toMatchObject({ robots })
  })

  it('finalizes a dotted 404 HTML response from response evidence even when request heuristics reject it', () => {
    const event = responseEvent({
      path: '/foo.bar',
      accept: 'application/json',
      status: 404,
      headers: {
        'Content-Type': 'TEXT/HTML; CHARSET=UTF-8',
        'x-robots-tag': 'stale-one',
        'X-Robots-Tag': 'stale-two',
      },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
    expect(Object.keys(event.node.res.getHeaders()).filter(name => name.toLowerCase() === 'x-robots-tag'))
      .toHaveLength(1)
  })

  it('fails closed for a browser-like error hook before Content-Type exists', () => {
    const event = responseEvent({
      path: '/missing.page',
      accept: 'TEXT/HTML,APPLICATION/XHTML+XML;q=0.9',
      status: 500,
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
  })

  it.each([
    '/api/entities',
    '/auth/session',
    '/admin-api/users',
    '/chat/stream',
    '/health',
    '/feedback/report',
    '/events',
    '/_nuxt/app.js',
  ])('skips missing-type non-HTML error paths even with browser Accept: %s', (path) => {
    const event = responseEvent({
      path,
      accept: 'text/html,application/xhtml+xml',
      status: 404,
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).not.toHaveProperty('cache-control')
    expect(lowerHeaders(event)).not.toHaveProperty('x-launch-indexing-policy')
    expect(lowerHeaders(event)).not.toHaveProperty('x-robots-tag')
  })

  it('uses the launch candidate classification for a normal 200 response without Content-Type', () => {
    const event = responseEvent({ path: '/du-lich', accept: 'text/html', status: 200 })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
  })

  it('prioritizes an existing middleware decision for wildcard HTML requests without Content-Type', () => {
    const event = responseEvent({
      path: '/du-lich',
      accept: '*/*',
      status: 200,
      context: { launchSafety: failedOpenDecision },
    })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
  })

  it.each([
    '/robots.txt',
    '/sitemap.xml',
    '/sitemap-media.xml',
    '/sitemap-index.xml',
  ])('adds exact policy headers but no robots header to root SEO response %s', (path) => {
    const event = responseEvent({
      path,
      accept: '*/*',
      headers: { 'content-type': path === '/robots.txt' ? 'text/plain' : 'application/xml' },
      context: { launchSafety: closedDecision },
    })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'closed',
    })
    expect(lowerHeaders(event)).not.toHaveProperty('x-robots-tag')
  })

  it('fails root SEO closed when middleware context is missing and never adds robots', () => {
    const event = responseEvent({ path: '/robots.txt', accept: '*/*' })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
    })
    expect(lowerHeaders(event)).not.toHaveProperty('x-robots-tag')
  })

  it('does not add launch or robots headers to non-HTML assets and APIs', () => {
    for (const event of [
      responseEvent({ path: '/_nuxt/app.js', accept: '*/*', headers: { 'content-type': 'text/javascript' } }),
      responseEvent({ path: '/api/entities', accept: 'application/json', headers: { 'content-type': 'application/json' } }),
    ]) {
      finalizeLaunchResponse(event as never)
      expect(lowerHeaders(event)).not.toHaveProperty('cache-control')
      expect(lowerHeaders(event)).not.toHaveProperty('x-launch-indexing-policy')
      expect(lowerHeaders(event)).not.toHaveProperty('x-robots-tag')
    }
  })

  it('removes a stale robots header while leaving non-HTML responses otherwise untouched', () => {
    const event = responseEvent({
      path: '/api/entities',
      accept: 'application/json',
      headers: {
        'content-type': 'application/json',
        'X-Robots-Tag': 'stale',
      },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)['x-robots-tag']).toBe('stale')
    expect(lowerHeaders(event)).not.toHaveProperty('cache-control')
    expect(lowerHeaders(event)).not.toHaveProperty('x-launch-indexing-policy')
  })

  it.each([
    '/api/entities',
    '/events',
    '/cai-dat',
    '/_internal/launch-policy-attestation',
  ])('skips manifest-sensitive paths even when an error body declares HTML: %s', (path) => {
    const event = responseEvent({
      path,
      accept: 'text/html',
      status: 500,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'X-Robots-Tag': 'noindex, follow',
      },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({ 'x-robots-tag': 'noindex, follow' })
    expect(lowerHeaders(event)).not.toHaveProperty('cache-control')
    expect(lowerHeaders(event)).not.toHaveProperty('x-launch-indexing-policy')
  })

  it('lets an explicit JSON response override an existing public middleware decision', () => {
    const event = responseEvent({
      path: '/du-lich',
      accept: '*/*',
      status: 200,
      headers: { 'content-type': 'application/json' },
      context: { launchSafety: selectiveOpenPageDecision },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).not.toHaveProperty('cache-control')
    expect(lowerHeaders(event)).not.toHaveProperty('x-launch-indexing-policy')
    expect(lowerHeaders(event)).not.toHaveProperty('x-robots-tag')
  })

  it('protects an unknown dotted path when its 404 response is actually HTML', () => {
    const event = responseEvent({
      path: '/foo.js',
      accept: 'application/json',
      status: 404,
      headers: { 'content-type': 'text/html; charset=utf-8' },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
  })

  it('falls back synchronously to failed-open and clears stale headers when context is missing', () => {
    const event = responseEvent({
      status: 500,
      headers: {
        'content-type': 'text/html',
        'X-Launch-Policy-Fingerprint': 'stale',
      },
    })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'cache-control': 'no-store',
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
    expect(lowerHeaders(event)).not.toHaveProperty('x-launch-policy-fingerprint')
  })

  it('keeps the final HTML context aligned when malformed evidence is downgraded', () => {
    const event = responseEvent({
      headers: { 'content-type': 'text/html' },
      context: {
        launchSafety: {
          ...selectiveOpenPageDecision,
          policy_fingerprint: null,
        },
      },
    })

    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'x-launch-indexing-policy': 'failed-open',
      'x-robots-tag': 'noindex, follow',
    })
    expect(event.context.launchSafety).toMatchObject({
      operational_state: 'failed-open',
      policy_fingerprint: null,
      robots: 'noindex, follow',
    })
  })

  it('preserves a root handler sitemap input during the generic final hook', () => {
    const decision = Object.freeze({ ...selectiveOpenDecision, sitemap_batch_revision: batch })
    const event = responseEvent({
      path: '/sitemap.xml',
      accept: '*/*',
      headers: { 'content-type': 'application/xml' },
      context: { launchSafety: decision },
    })
    writeLaunchResponseHeaders(event as never, { decision, sitemap: true, requestedBatch: batch })
    finalizeLaunchResponse(event as never)

    expect(lowerHeaders(event)).toMatchObject({
      'x-launch-sitemap-batch-revision': batch,
      'x-launch-sitemap-requested-batch': batch,
    })
  })

  it('registers both final-response and synchronous error hooks', () => {
    const hook = vi.fn()
    launchResponsePlugin({ hooks: { hook } } as never)

    expect(hook).toHaveBeenCalledWith('beforeResponse', expect.any(Function))
    expect(hook).toHaveBeenCalledWith('error', expect.any(Function))
  })

  it('has no other dynamic X-Robots-Tag writer under server/', () => {
    const serverRoot = resolve(process.cwd(), 'server')
    const walk = (directory: string): string[] => readdirSync(directory, { withFileTypes: true })
      .flatMap(entry => entry.isDirectory()
        ? walk(resolve(directory, entry.name))
        : entry.name.endsWith('.ts') ? [resolve(directory, entry.name)] : [])
    const candidates = walk(serverRoot)
    const writers = candidates.filter((path) => {
      const source = readFileSync(path, 'utf8')
      return source.includes('X-Robots-Tag')
    })

    expect(writers).toEqual([resolve(serverRoot, 'utils/launch/launchHeaders.ts')])
  })
})
