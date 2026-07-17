import type { LaunchPageDecision, LaunchSafetyDecision } from '~/types/launch'
import {
  failedOpenPageDecision,
  initialRequestPageDecision,
  refineEntityLaunchDecision,
} from '~/server/utils/launch/entityPolicy'
import { failedOpenLaunchDecision } from '~/server/utils/launch/launchHeaders'
import {
  classifyRequestTarget,
  launchRouteManifest,
} from '~/server/utils/launch/launchRouteManifest'
import {
  LAUNCH_SAFETY_BASE_STATE_KEY,
  LAUNCH_SAFETY_ROUTE_STATE_KEY,
  LAUNCH_SAFETY_STATE_KEY,
} from '~/composables/useLaunchSafety'

/**
 * Bridge the request middleware's base decision into a hydratable page state.
 * The object is immutable and assigned to the current H3 event only; no module
 * singleton is used, so parallel SSR requests cannot overwrite one another.
 */
export default defineNuxtPlugin(() => {
  const event = useRequestEvent()
  const contextual = (event?.context.launchSafety as LaunchSafetyDecision | undefined) ?? failedOpenLaunchDecision
  const base = Object.isFrozen(contextual) ? contextual : Object.freeze({ ...contextual })
  const target = event?.node.req.url || event?.path || '/'
  const method = event?.method || event?.node.req.method || 'GET'
  const routeClassification = event
    ? classifyRequestTarget(target, launchRouteManifest, method).classification
    : 'crawl-blocked-sensitive'
  const requiresEntityPolicy = routeClassification === 'backend-entity' || routeClassification === 'backend-ward'
  const routeIsKnownCanonical = !target.includes('?') && routeClassification === 'indexable-public'
  const initial: LaunchPageDecision = event
    ? initialRequestPageDecision(base, requiresEntityPolicy, routeIsKnownCanonical)
    : failedOpenPageDecision('entity-policy-unavailable')

  const state = useState<LaunchPageDecision>(LAUNCH_SAFETY_STATE_KEY, () => initial)
  const baseState = useState<LaunchSafetyDecision>(LAUNCH_SAFETY_BASE_STATE_KEY, () => base)
  const routeState = useState<string>(LAUNCH_SAFETY_ROUTE_STATE_KEY, () => target)
  baseState.value = base
  routeState.value = target
  state.value = initial
  if (event) event.context.launchSafety = initial

  return {
    provide: { refineEntityLaunchDecision },
  }
})
