// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'

import type { LaunchSafetyDecision } from '../types/launch'
import { buildPolicyFingerprint } from '../server/utils/launch/launchEvidence'
import { resolveBaseLaunchSafetyDecision } from '../server/utils/launch/launchSafetyDecision'
import {
  createLaunchReadinessHandler,
  type LaunchReadinessDependencies,
} from '../server/routes/_internal/launch-readiness.get'

const routeDigest = '1'.repeat(64)
const disclosureDigest = '2'.repeat(64)
const activeBatch = '3'.repeat(64)
const evidence = Object.freeze({
  routeRevision: 'launch-indexing-policy-v1',
  routeDigest,
  disclosureRevision: 'ai-disclosure-v1',
  disclosureDigest,
})
const checks = Object.freeze([
  Object.freeze({ name: 'manifest-schema', ok: true, reason: 'manifest-valid' }),
  Object.freeze({ name: 'artifact-evidence', ok: true, reason: 'artifact-evidence-valid' }),
])
const fingerprint = buildPolicyFingerprint(evidence)
const exactOpenEnv = Object.freeze({
  LAUNCH_INDEXING_MODE: 'selective-open',
  LAUNCH_INDEXING_OWNER_APPROVED: 'true',
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

function failedOpenDecision(reason: LaunchSafetyDecision['reason']): Readonly<LaunchSafetyDecision> {
  return Object.freeze({
    operational_state: 'failed-open',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'unavailable',
    reason,
  })
}

type HeaderValue = string | number | readonly string[]

class ResponseStub {
  statusCode = 200
  private readonly headers = new Map<string, HeaderValue>()

  getHeaders(): Record<string, HeaderValue> {
    return Object.fromEntries(this.headers)
  }

  getHeader(name: string): HeaderValue | undefined {
    return this.headers.get(name.toLowerCase())
  }

  setHeader(name: string, value: HeaderValue): void {
    this.headers.set(name.toLowerCase(), value)
  }

  removeHeader(name: string): void {
    this.headers.delete(name.toLowerCase())
  }
}

function readinessEvent() {
  const launchSafety = Object.freeze({ sentinel: true })
  return {
    context: { launchSafety },
    method: 'GET',
    path: '/_internal/launch-readiness',
    node: {
      req: {
        method: 'GET',
        url: '/_internal/launch-readiness',
        headers: { accept: 'application/json' },
      },
      res: new ResponseStub(),
    },
  }
}

function matchingAttestation() {
  return {
    policy_fingerprint: fingerprint,
    route_manifest_revision: 'launch-indexing-policy-v1',
    backend_policy_revision: 'index-policy-v1',
  }
}

function successfulActiveSitemap(batch: string | null = activeBatch) {
  return Object.freeze({
    status: 200 as const,
    body: '<sitemapindex/>',
    contentType: 'application/xml; charset=utf-8' as const,
    decision: Object.freeze({ ...selectiveOpenDecision, sitemap_batch_revision: batch }),
    requestedBatch: null,
    failureReason: null,
  })
}

function unavailableActiveSitemap(reason: 'sitemap-batch-unavailable' | 'sitemap-evidence-mismatch') {
  return Object.freeze({
    status: 503 as const,
    body: '' as const,
    contentType: 'application/xml; charset=utf-8' as const,
    decision: failedOpenDecision(reason),
    requestedBatch: null,
    failureReason: reason,
  })
}

function dependencies(input: {
  env?: NodeJS.ProcessEnv
  loadManifest?: LaunchReadinessDependencies['loadManifest']
  resolveDecision?: LaunchReadinessDependencies['resolveDecision']
  fetchAttestation?: LaunchReadinessDependencies['fetchAttestation']
  fetchActiveSitemap?: LaunchReadinessDependencies['fetchActiveSitemap']
} = {}) {
  return {
    env: input.env ?? {},
    loadManifest: input.loadManifest ?? vi.fn(() => ({ evidence, checks })),
    resolveDecision: input.resolveDecision ?? vi.fn(resolveBaseLaunchSafetyDecision),
    fetchAttestation: input.fetchAttestation ?? vi.fn().mockResolvedValue(matchingAttestation()),
    fetchActiveSitemap: input.fetchActiveSitemap ?? vi.fn().mockResolvedValue(successfulActiveSitemap()),
  } satisfies LaunchReadinessDependencies
}

async function runReadiness(deps: LaunchReadinessDependencies) {
  const event = readinessEvent()
  const originalLaunchSafety = event.context.launchSafety
  const handler = createLaunchReadinessHandler(deps)
  const body = await handler(event as never)
  const headers = event.node.res.getHeaders()

  expect(headers).toEqual({ 'cache-control': 'no-store' })
  expect(Object.keys(headers).some(name => name.startsWith('x-launch-'))).toBe(false)
  expect(headers).not.toHaveProperty('x-robots-tag')
  expect(event.context.launchSafety).toBe(originalLaunchSafety)

  return { body, status: event.node.res.statusCode, event }
}

describe('process-local launch readiness endpoint', () => {
  it('validates the manifest before returning a backend-independent safe closed response', async () => {
    const order: string[] = []
    const deps = dependencies({
      loadManifest: vi.fn(() => {
        order.push('manifest')
        return { evidence, checks }
      }),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(200)
    expect(response.body).toEqual({ ok: true, state: 'closed', checks })
    expect(order).toEqual(['manifest'])
    expect(deps.resolveDecision).not.toHaveBeenCalled()
    expect(deps.fetchAttestation).not.toHaveBeenCalled()
    expect(deps.fetchActiveSitemap).not.toHaveBeenCalled()
  })

  it.each([
    ['mode only', { LAUNCH_INDEXING_MODE: 'selective-open' }],
    ['owner only', { LAUNCH_INDEXING_OWNER_APPROVED: 'true' }],
    ['malformed mode', { LAUNCH_INDEXING_MODE: ' selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }],
    ['malformed owner approval', { LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'TRUE' }],
  ])('keeps %s launch intent safely closed without backend calls', async (_label, env) => {
    const deps = dependencies({ env })

    const response = await runReadiness(deps)

    expect(response.status).toBe(200)
    expect(response.body).toEqual({ ok: true, state: 'closed', checks })
    expect(deps.loadManifest).toHaveBeenCalledOnce()
    expect(deps.resolveDecision).not.toHaveBeenCalled()
    expect(deps.fetchAttestation).not.toHaveBeenCalled()
    expect(deps.fetchActiveSitemap).not.toHaveBeenCalled()
  })

  it('returns a sanitized build-isolation failure before any decision or backend call', async () => {
    const deps = dependencies({
      env: exactOpenEnv,
      loadManifest: vi.fn(() => {
        throw new Error('manifest contains secret digest and C:\\private\\output path')
      }),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(503)
    expect(response.body).toEqual({ ok: false, reason: 'build-isolation-unsafe' })
    expect(JSON.stringify(response.body)).not.toContain('secret')
    expect(deps.resolveDecision).not.toHaveBeenCalled()
    expect(deps.fetchAttestation).not.toHaveBeenCalled()
    expect(deps.fetchActiveSitemap).not.toHaveBeenCalled()
  })

  it('runs exact-open checks in manifest, decision, attestation, sitemap order', async () => {
    const order: string[] = []
    const fetchAttestation = vi.fn(async () => {
      order.push('attestation')
      return matchingAttestation()
    })
    const fetchActiveSitemap = vi.fn(async () => {
      order.push('sitemap')
      return successfulActiveSitemap()
    })
    const deps = dependencies({
      env: exactOpenEnv,
      loadManifest: vi.fn(() => {
        order.push('manifest')
        return { evidence, checks }
      }),
      resolveDecision: vi.fn(async (input) => {
        order.push('decision')
        return resolveBaseLaunchSafetyDecision(input)
      }),
      fetchAttestation,
      fetchActiveSitemap,
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(200)
    expect(response.body).toEqual({
      ok: true,
      state: 'selective-open',
      active_batch: activeBatch,
      checks,
    })
    expect(order).toEqual(['manifest', 'decision', 'attestation', 'sitemap'])
    expect(deps.resolveDecision).toHaveBeenCalledWith({
      env: exactOpenEnv,
      build: evidence,
      fetchAttestation: expect.any(Function),
    })
    expect(fetchActiveSitemap).toHaveBeenCalledWith(response.event, selectiveOpenDecision)
  })

  it('returns a sanitized attestation-unavailable reason without checking sitemaps', async () => {
    const deps = dependencies({
      env: exactOpenEnv,
      fetchAttestation: vi.fn().mockRejectedValue(new Error('connect failed with API_BASE=http://secret.internal')),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(503)
    expect(response.body).toEqual({ ok: false, reason: 'policy-attestation-unavailable' })
    expect(JSON.stringify(response.body)).not.toContain('secret.internal')
    expect(deps.fetchAttestation).toHaveBeenCalledOnce()
    expect(deps.fetchActiveSitemap).not.toHaveBeenCalled()
  })

  it('returns policy-mismatch for mismatched attestation without checking sitemaps', async () => {
    const deps = dependencies({
      env: exactOpenEnv,
      fetchAttestation: vi.fn().mockResolvedValue({
        ...matchingAttestation(),
        policy_fingerprint: 'f'.repeat(64),
      }),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(503)
    expect(response.body).toEqual({ ok: false, reason: 'policy-mismatch' })
    expect(deps.fetchAttestation).toHaveBeenCalledOnce()
    expect(deps.fetchActiveSitemap).not.toHaveBeenCalled()
  })

  it.each([
    'sitemap-batch-unavailable',
    'sitemap-evidence-mismatch',
  ] as const)('preserves the exact %s guarded sitemap failure reason', async (reason) => {
    const deps = dependencies({
      env: exactOpenEnv,
      fetchActiveSitemap: vi.fn().mockResolvedValue(unavailableActiveSitemap(reason)),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(503)
    expect(response.body).toEqual({ ok: false, reason })
    expect(deps.fetchAttestation).toHaveBeenCalledOnce()
    expect(deps.fetchActiveSitemap).toHaveBeenCalledOnce()
  })

  it.each([
    ['null', null],
    ['uppercase', 'A'.repeat(64)],
    ['short', activeBatch.slice(1)],
  ] as const)('rejects a status-200 sitemap result with a %s active batch', async (_label, batch) => {
    const deps = dependencies({
      env: exactOpenEnv,
      fetchActiveSitemap: vi.fn().mockResolvedValue(successfulActiveSitemap(batch)),
    })

    const response = await runReadiness(deps)

    expect(response.status).toBe(503)
    expect(response.body).toEqual({ ok: false, reason: 'sitemap-evidence-mismatch' })
    expect(deps.fetchAttestation).toHaveBeenCalledOnce()
    expect(deps.fetchActiveSitemap).toHaveBeenCalledOnce()
  })
})
