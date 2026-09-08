import { ref, watch, nextTick, onUnmounted, type ComputedRef } from 'vue'
import type { Router, RouteLocationNormalizedLoaded } from 'vue-router'
import { normalizeRouteParam } from '~/utils/routePaths'

export type HeroImageRef = HTMLImageElement | { $el?: unknown } | null

type HeroNavigationAttempt = {
  readonly fromFullPath: string
  readonly toFullPath: string
}

export interface UseDetailHeroTransitionOptions {
  router: Router
  route: RouteLocationNormalizedLoaded
  heroImageIdentity: ComputedRef<string>
}

export function useDetailHeroTransition(options: UseDetailHeroTransitionOptions) {
  const { router, route, heroImageIdentity } = options
  const heroLoaded = ref(false)
  const heroImage = ref<HeroImageRef>(null)

  let pendingHeroNavigation: HeroNavigationAttempt | null = null

  function changesHeroRouteIdentity(to: RouteLocationNormalizedLoaded, from: RouteLocationNormalizedLoaded): boolean {
    return to.name !== from.name || normalizeRouteParam(to.params.id) !== normalizeRouteParam(from.params.id)
  }

  const removeHeroNavigationGuard = router.beforeEach((to, from) => {
    if (!changesHeroRouteIdentity(to as any, from as any)) return
    pendingHeroNavigation = { fromFullPath: from.fullPath, toFullPath: to.fullPath }
    heroLoaded.value = false
  })

  const removeHeroNavigationCompletionHook = router.afterEach((to, from, failure) => {
    const pending = pendingHeroNavigation
    if (!pending) return
    const completesPendingNavigation = (
      pending.fromFullPath === from.fullPath && pending.toFullPath === to.fullPath
    ) || to.redirectedFrom?.fullPath === pending.toFullPath
    if (!completesPendingNavigation) return
    pendingHeroNavigation = null
    if (failure || !changesHeroRouteIdentity(to as any, from as any)) void revealHeroImageAfterUpdate()
  })

  onUnmounted(() => {
    removeHeroNavigationGuard()
    removeHeroNavigationCompletionHook()
  })

  function revealHeroImage(event?: Event) {
    const eventTarget = event?.currentTarget
    const refTarget = heroImage.value
    const image = eventTarget instanceof HTMLImageElement
      ? eventTarget
      : refTarget instanceof HTMLImageElement
        ? refTarget
        : refTarget?.$el instanceof HTMLImageElement
          ? refTarget.$el
          : null
    if (!image?.complete || image.naturalWidth <= 0) return
    heroLoaded.value = true
  }

  async function revealHeroImageAfterUpdate() {
    await nextTick()
    revealHeroImage()
  }

  // Reset stale route state before Vue reuses the hero, then inspect the committed replacement ref.
  watch(heroImageIdentity, () => {
    heroLoaded.value = false
  }, { flush: 'sync' })

  watch(heroImageIdentity, () => {
    void revealHeroImageAfterUpdate()
  }, { flush: 'post' })

  return {
    heroLoaded,
    heroImage,
    revealHeroImage,
    revealHeroImageAfterUpdate,
  }
}
