// @vitest-environment node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  initialRequestPageDecision,
  pageDecisionFromBase,
  parseMatchingEntityPolicy,
  refineEntityLaunchDecision,
} from '../server/utils/launch/entityPolicy'
import type { LaunchSafetyDecision } from '../types/launch'

import {
  LAUNCH_SAFETY_BASE_STATE_KEY,
  LAUNCH_SAFETY_ROUTE_STATE_KEY,
  LAUNCH_SAFETY_STATE_KEY,
  createLaunchGenerationGuard,
  useLaunchSafety,
} from '../composables/useLaunchSafety'

const fingerprint = 'b'.repeat(64)

const selectiveOpen: LaunchSafetyDecision = Object.freeze({
  operational_state: 'selective-open',
  indexing_posture: 'selective-open',
  policy_fingerprint: fingerprint,
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
  sitemap_batch_revision: null,
  sitemap_action: 'guarded-proxy',
  reason: 'valid-two-key-unlock',
})

const closed: LaunchSafetyDecision = Object.freeze({
  operational_state: 'closed',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'closed-empty',
  reason: 'closed-default',
})

function matchingEntityPolicy(
  indexable: boolean,
  kind: 'entity' | 'ward',
  overrides: Record<string, unknown> = {},
) {
  return {
    index_policy: {
      indexable,
      kind,
      policy_fingerprint: fingerprint,
      policy_revision: 'index-policy-v1',
      reasons: indexable ? [] : [
        kind === 'entity'
          ? 'description-below-130-words'
          : 'ward-below-child-and-summary-threshold',
      ],
      ...overrides,
    },
  }
}

describe('entity launch policy refinement', () => {
  it('keeps a valid negative decision selective-open and discoverable', () => {
    const decision = refineEntityLaunchDecision({
      base: selectiveOpen,
      carrier: matchingEntityPolicy(false, 'entity'),
      expectedKind: 'entity',
      canonicalPath: true,
    })

    expect(decision).toEqual({
      ...selectiveOpen,
      robots: 'noindex, follow',
      sitemapDiscovery: true,
    })
    expect(Object.isFrozen(decision)).toBe(true)
  })

  it('indexes only a valid positive policy on its exact canonical path', () => {
    const positive = matchingEntityPolicy(true, 'entity')

    expect(refineEntityLaunchDecision({
      base: selectiveOpen,
      carrier: positive,
      expectedKind: 'entity',
      canonicalPath: true,
    }).robots).toBe('index, follow')

    const aliasDecision = refineEntityLaunchDecision({
      base: selectiveOpen,
      carrier: positive,
      expectedKind: 'entity',
      canonicalPath: false,
    })
    expect(aliasDecision).toMatchObject({
      operational_state: 'selective-open',
      policy_fingerprint: fingerprint,
      robots: 'noindex, follow',
      sitemapDiscovery: true,
    })
  })

  it('does not inspect a carrier while the base gate is closed', () => {
    let inspected = false
    const carrier = Object.defineProperty({}, 'index_policy', {
      get() {
        inspected = true
        throw new Error('must not inspect')
      },
    })

    expect(refineEntityLaunchDecision({
      base: closed,
      carrier,
      expectedKind: 'entity',
      canonicalPath: true,
    })).toEqual({
      ...closed,
      robots: 'noindex, follow',
      sitemapDiscovery: false,
    })
    expect(inspected).toBe(false)
  })

  it('isolates concurrent malformed and valid requests without mutating the base', async () => {
    const before = { ...selectiveOpen }
    const [failed, valid] = await Promise.all([
      Promise.resolve(refineEntityLaunchDecision({
        base: selectiveOpen,
        carrier: { index_policy: { indexable: true } },
        expectedKind: 'entity',
        canonicalPath: true,
      })),
      Promise.resolve(refineEntityLaunchDecision({
        base: selectiveOpen,
        carrier: matchingEntityPolicy(false, 'entity'),
        expectedKind: 'entity',
        canonicalPath: true,
      })),
    ])

    expect(failed).toMatchObject({
      operational_state: 'failed-open',
      reason: 'entity-policy-mismatch',
      policy_fingerprint: null,
      sitemapDiscovery: false,
    })
    expect(valid).toMatchObject({
      operational_state: 'selective-open',
      reason: 'valid-two-key-unlock',
      robots: 'noindex, follow',
      sitemapDiscovery: true,
    })
    expect(failed).not.toBe(valid)
    expect(selectiveOpen).toEqual(before)
  })

  it.each([
    ['missing policy', {}],
    ['carrier symbol key', (() => {
      const carrier = matchingEntityPolicy(false, 'entity') as Record<PropertyKey, unknown>
      carrier[Symbol('extra')] = true
      return carrier
    })()],
    ['carrier non-enumerable key', (() => {
      const carrier = matchingEntityPolicy(false, 'entity')
      Object.defineProperty(carrier, 'hidden', { value: true, enumerable: false })
      return carrier
    })()],
    ['carrier accessor', (() => {
      const policy = matchingEntityPolicy(false, 'entity').index_policy
      const carrier = {}
      Object.defineProperty(carrier, 'index_policy', { get: () => policy, enumerable: true })
      return carrier
    })()],
    ['inherited policy', Object.create({ index_policy: matchingEntityPolicy(false, 'entity').index_policy })],
    ['carrier null prototype', Object.assign(Object.create(null), matchingEntityPolicy(false, 'entity'))],
    ['extra policy key', matchingEntityPolicy(false, 'entity', { extra: true })],
    ['policy symbol key', (() => {
      const carrier = matchingEntityPolicy(false, 'entity')
      const policy = carrier.index_policy as Record<PropertyKey, unknown>
      policy[Symbol('extra')] = true
      return carrier
    })()],
    ['policy non-enumerable key', (() => {
      const carrier = matchingEntityPolicy(false, 'entity')
      Object.defineProperty(carrier.index_policy, 'hidden', { value: true, enumerable: false })
      return carrier
    })()],
    ['policy accessor', (() => {
      const source = matchingEntityPolicy(false, 'entity').index_policy
      const { kind: _kind, ...rest } = source
      const policy = { ...rest }
      Object.defineProperty(policy, 'kind', { get: () => 'entity', enumerable: true })
      return { index_policy: policy }
    })()],
    ['policy custom prototype', (() => {
      const policy = Object.assign(Object.create({ inherited: true }), matchingEntityPolicy(false, 'entity').index_policy)
      return { index_policy: policy }
    })()],
    ['missing policy key', (() => {
      const policy = { ...matchingEntityPolicy(false, 'entity').index_policy }
      delete (policy as Partial<typeof policy>).kind
      return { index_policy: policy }
    })()],
    ['wrong route kind', matchingEntityPolicy(false, 'ward')],
    ['non-boolean indexable', matchingEntityPolicy(false, 'entity', { indexable: 'false' })],
    ['non-array reasons', matchingEntityPolicy(false, 'entity', { reasons: 'thin' })],
    ['non-string reason', matchingEntityPolicy(false, 'entity', { reasons: ['thin', 1] })],
    ['sparse reasons', matchingEntityPolicy(false, 'entity', { reasons: new Array(1) })],
    ['empty reason', matchingEntityPolicy(false, 'entity', { reasons: [''] })],
    ['invalid fingerprint shape', matchingEntityPolicy(false, 'entity', { policy_fingerprint: 'not-a-digest' })],
    ['uppercase fingerprint', matchingEntityPolicy(false, 'entity', { policy_fingerprint: 'B'.repeat(64) })],
    ['mismatched fingerprint', matchingEntityPolicy(false, 'entity', { policy_fingerprint: 'c'.repeat(64) })],
    ['mismatched revision', matchingEntityPolicy(false, 'entity', { policy_revision: 'index-policy-v0' })],
    ['contradictory positive reasons', matchingEntityPolicy(true, 'entity', { reasons: ['description-below-130-words'] })],
    ['contradictory negative reasons', matchingEntityPolicy(false, 'entity', { reasons: [] })],
  ])('fails only the request for %s', (_name, carrier) => {
    const decision = refineEntityLaunchDecision({
      base: selectiveOpen,
      carrier,
      expectedKind: 'entity',
      canonicalPath: true,
    })

    expect(decision).toMatchObject({
      operational_state: 'failed-open',
      indexing_posture: 'closed',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
      sitemap_action: 'unavailable',
      reason: 'entity-policy-mismatch',
      robots: 'noindex, follow',
      sitemapDiscovery: false,
    })
    expect(Object.isFrozen(decision)).toBe(true)
  })

  it('rejects a policy inherited from a polluted Object.prototype', () => {
    const previous = Object.getOwnPropertyDescriptor(Object.prototype, 'index_policy')
    Object.defineProperty(Object.prototype, 'index_policy', {
      configurable: true,
      enumerable: false,
      value: matchingEntityPolicy(false, 'entity').index_policy,
    })

    try {
      expect(refineEntityLaunchDecision({
        base: selectiveOpen,
        carrier: {},
        expectedKind: 'entity',
        canonicalPath: true,
      })).toMatchObject({
        operational_state: 'failed-open',
        reason: 'entity-policy-mismatch',
        sitemapDiscovery: false,
      })
    } finally {
      if (previous) Object.defineProperty(Object.prototype, 'index_policy', previous)
      else delete (Object.prototype as { index_policy?: unknown }).index_policy
    }
  })

  it.each([undefined, null])('classifies an unavailable carrier separately: %s', (carrier) => {
    expect(refineEntityLaunchDecision({
      base: selectiveOpen,
      carrier,
      expectedKind: 'entity',
      canonicalPath: true,
    })).toMatchObject({
      operational_state: 'failed-open',
      reason: 'entity-policy-unavailable',
      policy_fingerprint: null,
      sitemapDiscovery: false,
    })
  })

  it('returns a detached immutable policy value', () => {
    const carrier = matchingEntityPolicy(false, 'entity')
    const policy = parseMatchingEntityPolicy(carrier, selectiveOpen, 'entity')

    expect(policy).toEqual(carrier.index_policy)
    expect(policy).not.toBe(carrier.index_policy)
    expect(policy && Object.isFrozen(policy)).toBe(true)
    expect(policy && Object.isFrozen(policy.reasons)).toBe(true)
  })

  it('builds an immutable initial page decision from the request base', () => {
    expect(pageDecisionFromBase(selectiveOpen)).toEqual({
      ...selectiveOpen,
      robots: 'noindex, follow',
      sitemapDiscovery: true,
    })
    expect(pageDecisionFromBase(selectiveOpen, true)).toEqual({
      ...selectiveOpen,
      robots: 'index, follow',
      sitemapDiscovery: true,
    })
    expect(pageDecisionFromBase(closed)).toEqual({
      ...closed,
      robots: 'noindex, follow',
      sitemapDiscovery: false,
    })
    expect(Object.isFrozen(pageDecisionFromBase(selectiveOpen))).toBe(true)
  })

  it('clears selective evidence until a non-static request is refined', () => {
    expect(initialRequestPageDecision(selectiveOpen, true, false)).toEqual({
      operational_state: 'failed-open',
      indexing_posture: 'closed',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
      sitemap_action: 'unavailable',
      reason: 'entity-policy-unavailable',
      robots: 'noindex, follow',
      sitemapDiscovery: false,
    })
    expect(initialRequestPageDecision(selectiveOpen, false, true)).toEqual(pageDecisionFromBase(selectiveOpen, true))
    expect(initialRequestPageDecision(selectiveOpen, false, false)).toEqual(pageDecisionFromBase(selectiveOpen))
    expect(initialRequestPageDecision(closed, true, false)).toEqual(pageDecisionFromBase(closed))
  })
})

describe('request-local launch state bridge', () => {
  it.each([
    ['positive', pageDecisionFromBase(selectiveOpen, true)],
    ['valid negative', pageDecisionFromBase(selectiveOpen)],
  ])('preserves a hydrated %s decision until real navigation begins', (_name, hydrated) => {
    const request = seedRequest('/dia-diem/a', hydrated)
    request.runtime.client = true
    request.runtime.server = false

    const launch = useLaunchSafety(request.runtime)
    const guard = createLaunchGenerationGuard(() => launch.resetForNavigation())

    expect(guard.initialize()).toBe(1)
    expect(launch.decision.value).toEqual(hydrated)
    expect(Object.isFrozen(launch.decision.value)).toBe(true)

    expect(guard.begin()).toBe(2)
    expect(launch.decision.value).toMatchObject({
      operational_state: 'failed-open',
      reason: 'entity-policy-unavailable',
      robots: 'noindex, follow',
      sitemapDiscovery: false,
    })
  })

  it('uses a monotonic generation instead of route identity for stale-response rejection', () => {
    const resets: number[] = []
    const guard = createLaunchGenerationGuard(() => { resets.push(1) })

    const generationA = guard.begin()
    const generationB = guard.begin()
    const generationAAgain = guard.begin()

    expect(generationB).toBeGreaterThan(generationA)
    expect(generationAAgain).toBeGreaterThan(generationB)
    expect(guard.current()).toBe(generationAAgain)
    expect(guard.isCurrent(generationA)).toBe(false)
    expect(guard.isCurrent(generationB)).toBe(false)
    expect(guard.isCurrent(generationAAgain)).toBe(true)
    expect(resets).toHaveLength(3)
  })

  function seedRequest(path: string, initial: LaunchSafetyDecision | ReturnType<typeof pageDecisionFromBase>) {
    const event = { context: {} as Record<string, unknown>, node: { req: { url: path } } }
    const page = 'robots' in initial ? initial : pageDecisionFromBase(initial)
    const states = new Map<string, { value: unknown }>([
      [LAUNCH_SAFETY_BASE_STATE_KEY, { value: selectiveOpen }],
      [LAUNCH_SAFETY_STATE_KEY, { value: { ...page } }],
      [LAUNCH_SAFETY_ROUTE_STATE_KEY, { value: path }],
    ])
    const route = { fullPath: path }
    const runtime = {
      client: false,
      server: true,
      useNuxtApp: () => ({ $refineEntityLaunchDecision: refineEntityLaunchDecision }),
      useRequestEvent: () => event,
      useRoute: () => route,
      useState: <T>(key: string, init: () => T) => {
        if (!states.has(key)) states.set(key, { value: init() })
        return states.get(key) as { value: T }
      },
    }
    return { event, route, runtime, states }
  }

  it('re-freezes hydrated state and shares the exact object with the event context', () => {
    const hydrated = pageDecisionFromBase(selectiveOpen, true)
    const { event, runtime, states } = seedRequest('/dia-diem/a', hydrated)

    const launch = useLaunchSafety(runtime)
    const stored = states.get(LAUNCH_SAFETY_STATE_KEY)?.value

    expect(Object.isFrozen(stored)).toBe(true)
    expect(event.context.launchSafety).toBe(stored)
    expect(launch.decision.value).toBe(stored)
  })

  it('stores one frozen refined object in state and only the current event', async () => {
    const requestA = seedRequest('/dia-diem/a', initialRequestPageDecision(selectiveOpen, true, false))
    const launchA = useLaunchSafety(requestA.runtime)
    const decisionA = await launchA.refineEntityPolicy({
      carrier: matchingEntityPolicy(true, 'entity'),
      expectedKind: 'entity',
      canonicalPath: '/dia-diem/a',
    })

    const stateA = requestA.states.get(LAUNCH_SAFETY_STATE_KEY)?.value
    expect(decisionA).toBe(stateA)
    expect(requestA.event.context.launchSafety).toBe(stateA)
    expect(Object.isFrozen(stateA)).toBe(true)

    const requestB = seedRequest('/dia-diem/b', pageDecisionFromBase(closed))
    requestB.states.set(LAUNCH_SAFETY_BASE_STATE_KEY, { value: closed })
    const launchB = useLaunchSafety(requestB.runtime)
    const decisionB = await launchB.refineEntityPolicy({
      carrier: matchingEntityPolicy(true, 'entity'),
      expectedKind: 'entity',
      canonicalPath: '/dia-diem/b',
    })

    expect(decisionB.operational_state).toBe('closed')
    expect(requestB.event.context.launchSafety).toBe(requestB.states.get(LAUNCH_SAFETY_STATE_KEY)?.value)
    expect(requestA.event.context.launchSafety).toBe(requestA.states.get(LAUNCH_SAFETY_STATE_KEY)?.value)
    expect(requestA.event.context.launchSafety).not.toBe(requestB.event.context.launchSafety)
  })

  it('resets a stale positive decision when a different client page mounts', () => {
    const request = seedRequest('/dia-diem/a', pageDecisionFromBase(selectiveOpen, true))
    request.route.fullPath = '/xa-phuong/b'
    request.runtime.client = true
    request.runtime.server = false

    const launch = useLaunchSafety(request.runtime)

    expect(launch.decision.value).toMatchObject({
      operational_state: 'failed-open',
      reason: 'entity-policy-unavailable',
      policy_fingerprint: null,
      robots: 'noindex, follow',
    })
    expect(request.states.get(LAUNCH_SAFETY_ROUTE_STATE_KEY)?.value).toBe('/xa-phuong/b')
  })
})

describe('request-scoped integration source', () => {
  const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8')

  it('uses the entity response as its own carrier and fetches the exact ward carrier', () => {
    const entityPage = source('pages/dia-diem/[id].vue')
    const wardPage = source('pages/xa-phuong/[id].vue')

    expect(entityPage).toContain("expectedKind: 'entity'")
    expect(entityPage).toMatch(/carrier:\s*entityStatus\.value === 'error'\s*\|\| fetchError\.value \? null : entity\.value/u)
    expect(entityPage).toContain('entity.value.id !== id.value')
    expect(wardPage).toContain("expectedKind: 'ward'")
    expect(wardPage).toContain('`/api/entities/${encodedId.value}`')
    expect(wardPage).toContain('wardPolicyCarrier.value')
    expect(wardPage).toContain('__launchRequestId')
    expect(wardPage).toContain('data.value.place.id === id.value')
    expect(wardPage).toContain('wardPolicyCarrier.value?.requestId === id.value')
    expect(wardPage).toContain('wardPolicyCarrier.value.carrier?.id === id.value')
  })

  it('bridges only request-local context and hydratable Nuxt state', () => {
    const composable = source('composables/useLaunchSafety.ts')
    const plugin = source('plugins/launch-safety.server.ts')

    expect(composable).toContain('runtime?.useRequestEvent ?? useRequestEvent')
    expect(composable).toContain('event.context.launchSafety')
    expect(composable).not.toContain("from '~/server/utils/launch/entityPolicy'")
    expect(composable).toContain('getNuxtApp().$refineEntityLaunchDecision')
    expect(composable).toContain('decision.value = freezeDecision(decision.value)')
    expect(composable).toContain('requestTarget.value !== currentTarget')
    expect(composable).toContain('decision.value = fallbackDecision()')
    expect(composable).not.toMatch(/(?:let|const|var)\s+currentDecision\b/)
    expect(plugin).toContain('useState<LaunchPageDecision>')
    expect(plugin).toContain('state.value = initial')
    expect(plugin).toContain('event.context.launchSafety = initial')
  })
})
