import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  applyAccessibilityProfile,
  readAccessibilityPreferences,
  resolveAccessibilityProfile,
  useAccessibilityProfile,
} from '../composables/useAccessibilityProfile'

describe('public accessibility profile', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-density')
    document.documentElement.removeAttribute('data-reduced-motion')
    document.documentElement.removeAttribute('data-high-contrast')
    document.documentElement.removeAttribute('data-keyboard-first')
    document.documentElement.style.removeProperty('--a11y-text-scale')
  })

  it('disables ambient motion when reduced motion is requested', () => {
    const profile = resolveAccessibilityProfile({ reducedMotion: true, textScale: 2 })

    expect(profile.reducedMotion).toBe(true)
    expect(profile.textScale).toBe(2)
  })

  it('keeps Nocturne unless the user explicitly selects Parchment', () => {
    expect(resolveAccessibilityProfile({ theme: 'system', hour: 12 } as never).theme).toBe('nocturne')
    expect(resolveAccessibilityProfile({ theme: 'parchment' }).theme).toBe('parchment')
  })

  it('persists only user-selected theme, density and text scale', () => {
    const colorMode = { preference: 'dark' }
    const accessibility = useAccessibilityProfile({
      storage: localStorage,
      root: document.documentElement,
      colorMode,
      autoHydrate: false,
    })

    accessibility.setProfile({
      theme: 'parchment',
      density: 'compact',
      textScale: 2,
      reducedMotion: true,
      highContrast: true,
      keyboardFirst: true,
    })

    expect(readAccessibilityPreferences(localStorage)).toEqual({
      theme: 'parchment',
      density: 'compact',
      textScale: 2,
    })
    expect(colorMode.preference).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('parchment')
    expect(document.documentElement.dataset.density).toBe('compact')
    expect(document.documentElement.style.getPropertyValue('--a11y-text-scale')).toBe('2')
  })

  it('combines persisted choices with live accessibility media preferences', () => {
    localStorage.setItem('vl360-accessibility-profile', JSON.stringify({
      theme: 'parchment',
      density: 'compact',
      textScale: 1.5,
      reducedMotion: false,
    }))
    const matches = vi.fn((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)' || query === '(prefers-contrast: more)',
    }))
    const accessibility = useAccessibilityProfile({
      storage: localStorage,
      root: document.documentElement,
      matchMedia: matches,
      autoHydrate: false,
    })

    accessibility.hydrate()

    expect(accessibility.profile.value).toMatchObject({
      theme: 'parchment',
      density: 'compact',
      textScale: 1.5,
      reducedMotion: true,
      highContrast: true,
    })
    expect(matches).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)')
    expect(matches).toHaveBeenCalledWith('(prefers-contrast: more)')
  })

  it('applies profile state through semantic document attributes', () => {
    applyAccessibilityProfile(resolveAccessibilityProfile({
      reducedMotion: true,
      highContrast: true,
      keyboardFirst: true,
      textScale: 1.25,
    }), document.documentElement)

    expect(document.documentElement.dataset.reducedMotion).toBe('true')
    expect(document.documentElement.dataset.highContrast).toBe('true')
    expect(document.documentElement.dataset.keyboardFirst).toBe('true')
    expect(document.documentElement.style.getPropertyValue('--a11y-text-scale')).toBe('1.25')
  })
})
