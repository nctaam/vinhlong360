import { ref, type Ref } from 'vue'
import type { FreshnessMeta, RecoveryAction, RetryAction, SurfaceState } from '~/types/publicExperience'

export function surfaceState<T>(initial: SurfaceState<T> = { kind: 'loading' }): Ref<SurfaceState<T>> {
  return ref(initial) as Ref<SurfaceState<T>>
}

export function useSurfaceState<T>(initial?: SurfaceState<T>) {
  const state = surfaceState(initial)
  return {
    state,
    loading: () => { state.value = { kind: 'loading' } },
    ready: (data: T, freshness?: FreshnessMeta) => { state.value = { kind: 'ready', data, ...(freshness ? { freshness } : {}) } },
    partial: (data: T, failedPanels: string[]) => { state.value = { kind: 'partial', data, failedPanels: [...failedPanels] } },
    stale: (data: T, updatedAt: string) => { state.value = { kind: 'stale', data, updatedAt } },
    empty: (recovery: RecoveryAction) => { state.value = { kind: 'empty', recovery } },
    error: (retry: RetryAction, fallback?: T) => { state.value = { kind: 'error', retry, ...(fallback === undefined ? {} : { fallback }) } },
    offline: (cached?: T, cachedAt?: string) => { state.value = { kind: 'offline', ...(cached === undefined ? {} : { cached }), ...(cachedAt ? { cachedAt } : {}) } },
  }
}
