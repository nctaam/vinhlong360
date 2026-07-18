import {
  defineEventHandler,
  setHeader,
  setResponseStatus,
  type EventHandler,
  type H3Event,
} from 'h3'
import { useRuntimeConfig } from 'nitropack/runtime'

import type { BackendAttestation, LaunchSafetyDecision } from '../../../types/launch'
import { fetchBackendAttestation } from '../../utils/launch/backendAttestation'
import {
  fetchAndValidateActiveSitemapIndex,
  type GuardedSitemapResult,
} from '../../utils/launch/guardedSitemapProxy'
import { readLaunchIntent } from '../../utils/launch/launchIntent'
import {
  resolveBaseLaunchSafetyDecision,
  type ResolveBaseLaunchSafetyDecisionInput,
} from '../../utils/launch/launchSafetyDecision'
import {
  loadAndValidateReadinessManifest,
  type LoadedReadinessManifest,
} from '../../utils/launch/readinessManifest'

type ReadinessBody =
  | { readonly ok: true; readonly state: 'closed'; readonly checks: LoadedReadinessManifest['checks'] }
  | {
      readonly ok: true
      readonly state: 'selective-open'
      readonly active_batch: string | null
      readonly checks: LoadedReadinessManifest['checks']
    }
  | { readonly ok: false; readonly reason: LaunchSafetyDecision['reason'] }

export interface LaunchReadinessDependencies {
  readonly env: NodeJS.ProcessEnv
  readonly loadManifest: () => LoadedReadinessManifest
  readonly resolveDecision: (
    input: ResolveBaseLaunchSafetyDecisionInput,
  ) => Promise<LaunchSafetyDecision>
  readonly fetchAttestation: (event: H3Event) => Promise<BackendAttestation | unknown>
  readonly fetchActiveSitemap: (
    event: H3Event,
    decision: Readonly<LaunchSafetyDecision>,
  ) => Promise<GuardedSitemapResult>
}

function unsafe(event: H3Event, reason: LaunchSafetyDecision['reason']): ReadinessBody {
  setResponseStatus(event, 503)
  return { ok: false, reason }
}

function defaultDependencies(): LaunchReadinessDependencies {
  return {
    env: process.env,
    loadManifest: loadAndValidateReadinessManifest,
    resolveDecision: resolveBaseLaunchSafetyDecision,
    fetchAttestation: async (event) => {
      const runtimeConfig = useRuntimeConfig(event) as { apiBase?: unknown }
      const baseURL = typeof runtimeConfig.apiBase === 'string' ? runtimeConfig.apiBase : ''
      return fetchBackendAttestation({ baseURL })
    },
    fetchActiveSitemap: fetchAndValidateActiveSitemapIndex,
  }
}

export function createLaunchReadinessHandler(
  dependencies: LaunchReadinessDependencies,
): EventHandler<H3Event, Promise<ReadinessBody>> {
  return defineEventHandler(async (event): Promise<ReadinessBody> => {
    setHeader(event, 'Cache-Control', 'no-store')

    let build: LoadedReadinessManifest
    try {
      build = dependencies.loadManifest()
    } catch {
      return unsafe(event, 'build-isolation-unsafe')
    }

    if (!readLaunchIntent(dependencies.env).openIntent) {
      return { ok: true, state: 'closed', checks: build.checks }
    }

    let decision: LaunchSafetyDecision
    try {
      decision = await dependencies.resolveDecision({
        env: dependencies.env,
        build: build.evidence,
        fetchAttestation: () => dependencies.fetchAttestation(event),
      })
    } catch {
      return unsafe(event, 'policy-attestation-unavailable')
    }
    if (decision.operational_state !== 'selective-open') {
      return unsafe(event, decision.reason)
    }

    let active: GuardedSitemapResult
    try {
      active = await dependencies.fetchActiveSitemap(event, decision)
    } catch {
      return unsafe(event, 'sitemap-batch-unavailable')
    }
    if (active.status === 503) return unsafe(event, active.failureReason)

    return {
      ok: true,
      state: 'selective-open',
      active_batch: active.decision.sitemap_batch_revision,
      checks: build.checks,
    }
  })
}

export default defineEventHandler(async (event) => {
  const handler = createLaunchReadinessHandler(defaultDependencies())
  return handler(event)
})
