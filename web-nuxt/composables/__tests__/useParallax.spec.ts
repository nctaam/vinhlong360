// @vitest-environment happy-dom
import { describe, it, expect, vi, afterEach } from 'vitest'
import { useParallax } from '../useParallax'

afterEach(() => { vi.unstubAllGlobals() })

describe('useParallax (guard / SSR-safety)', () => {
  it('does not throw and sets no --parallax when reduced-motion is preferred', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }))
    const el = document.createElement('div')
    expect(() => useParallax(() => [el])).not.toThrow()
    expect(el.style.getPropertyValue('--parallax')).toBe('')
  })

  it('does not throw when IntersectionObserver is unavailable', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }))
    vi.stubGlobal('IntersectionObserver', undefined)
    const el = document.createElement('div')
    expect(() => useParallax(() => [el])).not.toThrow()
    expect(el.style.getPropertyValue('--parallax')).toBe('')
  })
})
