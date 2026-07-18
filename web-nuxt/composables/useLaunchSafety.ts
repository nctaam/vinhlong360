import { readonly, computed, type ComputedRef } from 'vue'

import type { LaunchPageDecision, LaunchSafetyDecision } from '~/types/launch'

type EntityPolicyKind = 'entity' | 'ward'

export const LAUNCH_SAFETY_STATE_KEY = 'launch-safety-page-decision'
export const LAUNCH_SAFETY_BASE_STATE_KEY = 'launch-safety-base-decision'
export const LAUNCH_SAFETY_ROUTE_STATE_KEY = 'launch-safety-request-target'

export function canonicalLaunchRequestTarget(target: string): string {
  const fragment = target.indexOf('#')
  return fragment < 0 ? target : target.slice(0, fragment)
}

export function buildLaunchHead(decision: Readonly<LaunchPageDecision>) {
  return {
    meta: [{ name: 'robots', content: decision.robots }],
    link: decision.sitemapDiscovery
      ? [{ rel: 'sitemap', type: 'application/xml', href: '/sitemap-index.xml' }]
      : [],
  }
}

export function createLaunchGenerationGuard(onBegin: () => void) {
  let activeGeneration = 0
  return Object.freeze({
    initialize(): number {
      if (activeGeneration === 0) activeGeneration = 1
      return activeGeneration
    },
    begin(): number {
      activeGeneration += 1
      onBegin()
      return activeGeneration
    },
    current(): number {
      return activeGeneration
    },
    isCurrent(generation: unknown): generation is number {
      return Number.isSafeInteger(generation) && generation === activeGeneration
    },
  })
}

export function isCurrentLaunchResult<T extends {
  readonly generation: number
  readonly requestId: string
}>(
  guard: { readonly isCurrent: (generation: unknown) => boolean },
  result: T | null | undefined,
  requestId: string,
): result is T {
  return !!result && guard.isCurrent(result.generation) && result.requestId === requestId
}

function freezeDecision(decision: LaunchPageDecision): LaunchPageDecision {
  return Object.isFrozen(decision) ? decision : Object.freeze({ ...decision })
}

function fallbackDecision(): LaunchPageDecision {
  return Object.freeze({
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
}

export interface EntityPolicyRefinementInput {
  readonly carrier: unknown
  readonly expectedKind: EntityPolicyKind
  readonly canonicalPath: string
}

interface LaunchSafetyEvent {
  readonly node: { readonly req: { readonly url?: string } }
  readonly context: Record<string, unknown>
}

interface LaunchSafetyRuntime {
  readonly client: boolean
  readonly server: boolean
  readonly useNuxtApp: () => {
    readonly $refineEntityLaunchDecision?: (input: {
      readonly base: Readonly<LaunchSafetyDecision>
      readonly carrier: unknown
      readonly expectedKind: EntityPolicyKind
      readonly canonicalPath: boolean
    }) => LaunchPageDecision
  }
  readonly useRequestEvent: () => LaunchSafetyEvent | undefined
  readonly useRoute: () => { readonly fullPath: string }
  readonly useState: <T>(key: string, init: () => T) => { value: T }
}

export function useLaunchSafety(runtime?: Partial<LaunchSafetyRuntime>) {
  const state = runtime?.useState ?? useState
  const getEvent = runtime?.useRequestEvent ?? useRequestEvent
  const getRoute = runtime?.useRoute ?? useRoute
  const getNuxtApp = runtime?.useNuxtApp ?? useNuxtApp
  const isServer = runtime?.server ?? import.meta.server
  const isClient = runtime?.client ?? import.meta.client

  const decision = state<LaunchPageDecision>(LAUNCH_SAFETY_STATE_KEY, fallbackDecision)
  const base = state<LaunchSafetyDecision>(LAUNCH_SAFETY_BASE_STATE_KEY, fallbackDecision)
  const requestTarget = state<string>(LAUNCH_SAFETY_ROUTE_STATE_KEY, () => '')
  const event = isServer ? getEvent() : undefined

  let currentTarget = canonicalLaunchRequestTarget(event?.node.req.url || '')
  if (!currentTarget) {
    try {
      currentTarget = canonicalLaunchRequestTarget(getRoute().fullPath)
    } catch {
      currentTarget = ''
    }
  }

  // useState is app-scoped in the browser. Reset before a newly mounted entity
  // or ward page can observe a previous route's positive decision.
  if (isClient && requestTarget.value !== currentTarget) {
    decision.value = fallbackDecision()
  }
  if (currentTarget) requestTarget.value = currentTarget

  // Nuxt payload serialization does not preserve Object.freeze(). Re-freeze
  // both values on hydration before exposing them to page/head consumers.
  decision.value = freezeDecision(decision.value)
  if (!Object.isFrozen(base.value)) base.value = Object.freeze({ ...base.value })
  if (event) event.context.launchSafety = decision.value

  function baseDecision(): LaunchSafetyDecision {
    return base.value
  }

  function setDecision(next: LaunchPageDecision): LaunchPageDecision {
    const immutable = freezeDecision(next)
    decision.value = immutable
    if (event) event.context.launchSafety = immutable
    return immutable
  }

  const canRefineEntityPolicy: ComputedRef<boolean> = computed(() =>
    isServer
      && base.value.operational_state === 'selective-open'
      && base.value.indexing_posture === 'selective-open',
  )

  /**
   * Compare the raw request target, not a normalized route path. Query strings,
   * trailing slashes, and alternate percent-encoding must stay noindex.
   */
  function isCanonicalPath(canonicalPath: string): boolean {
    if (typeof canonicalPath !== 'string' || !canonicalPath) return false
    const rawTarget = event?.node.req.url
    if (typeof rawTarget === 'string') {
      return canonicalLaunchRequestTarget(rawTarget) === canonicalLaunchRequestTarget(canonicalPath)
    }
    try {
      return canonicalLaunchRequestTarget(getRoute().fullPath) === canonicalLaunchRequestTarget(canonicalPath)
    } catch {
      return false
    }
  }

  async function refineEntityPolicy(input: EntityPolicyRefinementInput): Promise<LaunchPageDecision> {
    // The final SSR decision is already serialized during hydration. Client
    // navigation is reset to fail-closed and cannot reuse server-only policy
    // authority without a fresh HTML request.
    if (isClient) return decision.value

    const refiner = getNuxtApp().$refineEntityLaunchDecision
    if (typeof refiner !== 'function') return setDecision(fallbackDecision())
    const refined = refiner({
      base: baseDecision(),
      carrier: input.carrier,
      expectedKind: input.expectedKind,
      canonicalPath: isCanonicalPath(input.canonicalPath),
    })
    return setDecision(refined)
  }

  function resetForNavigation(): LaunchPageDecision {
    // Client-side navigation has no fresh base attestation. Keep it fail-closed
    // until the next SSR request establishes a new request-local decision.
    if (isClient) {
      try {
        requestTarget.value = canonicalLaunchRequestTarget(getRoute().fullPath)
      } catch {
        requestTarget.value = ''
      }
    }
    return setDecision(fallbackDecision())
  }

  // Keep the object shape stable for SSR payload hydration and avoid exposing a
  // mutable module-level singleton/currentDecision.
  return {
    decision: readonly(decision),
    canRefineEntityPolicy,
    isCanonicalPath,
    refineEntityPolicy,
    resetForNavigation,
  }
}
