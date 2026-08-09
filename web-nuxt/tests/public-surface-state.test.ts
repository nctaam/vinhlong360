import { describe, expect, it } from 'vitest'
import { surfaceState } from '~/composables/useSurfaceState'

describe('public surface state', () => {
  it('keeps partial data when one panel fails', () => {
    const state = surfaceState({ kind: 'partial', data: { facts: true }, failedPanels: ['media'] })
    expect(state.value.kind).toBe('partial')
    expect(state.value).toEqual({ kind: 'partial', data: { facts: true }, failedPanels: ['media'] })
  })
  it('supports explicit loading and offline transitions', () => {
    const surface = surfaceState<{ ok: boolean }>()
    expect(surface.value.kind).toBe('loading')
    surface.value = { kind: 'offline', cached: { ok: true } }
    expect(surface.value.kind).toBe('offline')
  })
})
