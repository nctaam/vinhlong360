import { onMounted, ref, type Ref } from 'vue'

import {
  DEFAULT_ACCESSIBILITY_PROFILE,
  type AccessibilityDensity,
  type AccessibilityPreferences,
  type AccessibilityProfile,
  type AccessibilityTextScale,
  type AccessibilityTheme,
} from '~/types/accessibility'

export const ACCESSIBILITY_STORAGE_KEY = 'vl360-accessibility-profile'

type AccessibilityStorage = Pick<Storage, 'getItem' | 'setItem'>
type AccessibilityRoot = Pick<HTMLElement, 'dataset' | 'style'>
type ColorModePreference = { preference: unknown }
type MediaMatcher = (query: string) => Pick<MediaQueryList, 'matches'>

export interface AccessibilityProfileOptions {
  storage?: AccessibilityStorage | null
  root?: AccessibilityRoot | null
  colorMode?: ColorModePreference | null
  matchMedia?: MediaMatcher | null
  autoHydrate?: boolean
}

const THEMES = new Set<AccessibilityTheme>(['nocturne', 'parchment'])
const DENSITIES = new Set<AccessibilityDensity>(['comfortable', 'compact'])
const TEXT_SCALES = new Set<AccessibilityTextScale>([1, 1.25, 1.5, 2])
let fallbackProfile: Ref<AccessibilityProfile> | null = null

function sharedProfileState(): Ref<AccessibilityProfile> {
  try {
    return useState<AccessibilityProfile>('vl360-accessibility-profile', () => ({ ...DEFAULT_ACCESSIBILITY_PROFILE }))
  } catch {
    // Direct unit tests may call the composable without a Nuxt app context.
    fallbackProfile ??= ref({ ...DEFAULT_ACCESSIBILITY_PROFILE })
    return fallbackProfile
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function theme(value: unknown): AccessibilityTheme {
  return THEMES.has(value as AccessibilityTheme) ? value as AccessibilityTheme : DEFAULT_ACCESSIBILITY_PROFILE.theme
}

function density(value: unknown): AccessibilityDensity {
  return DENSITIES.has(value as AccessibilityDensity) ? value as AccessibilityDensity : DEFAULT_ACCESSIBILITY_PROFILE.density
}

function textScale(value: unknown): AccessibilityTextScale {
  return TEXT_SCALES.has(value as AccessibilityTextScale) ? value as AccessibilityTextScale : DEFAULT_ACCESSIBILITY_PROFILE.textScale
}

export function resolveAccessibilityProfile(input: Partial<AccessibilityProfile> | Record<string, unknown> = {}): AccessibilityProfile {
  return {
    theme: theme(input.theme),
    density: density(input.density),
    textScale: textScale(input.textScale),
    reducedMotion: input.reducedMotion === true,
    highContrast: input.highContrast === true,
    keyboardFirst: input.keyboardFirst === true,
  }
}

export function readAccessibilityPreferences(storage: AccessibilityStorage | null | undefined): AccessibilityPreferences {
  if (!storage) return { theme: 'nocturne', density: 'comfortable', textScale: 1 }
  try {
    const parsed = JSON.parse(storage.getItem(ACCESSIBILITY_STORAGE_KEY) || 'null')
    const value = isRecord(parsed) ? parsed : {}
    return { theme: theme(value.theme), density: density(value.density), textScale: textScale(value.textScale) }
  } catch {
    return { theme: 'nocturne', density: 'comfortable', textScale: 1 }
  }
}

export function persistAccessibilityPreferences(profile: AccessibilityProfile, storage: AccessibilityStorage | null | undefined): void {
  if (!storage) return
  try {
    storage.setItem(ACCESSIBILITY_STORAGE_KEY, JSON.stringify({
      theme: profile.theme,
      density: profile.density,
      textScale: profile.textScale,
    } satisfies AccessibilityPreferences))
  } catch {
    // Storage failures must never block the public task.
  }
}

export function applyAccessibilityProfile(profile: AccessibilityProfile, root: AccessibilityRoot | null | undefined): void {
  if (!root) return
  root.dataset.theme = profile.theme
  root.dataset.density = profile.density
  root.dataset.reducedMotion = String(profile.reducedMotion)
  root.dataset.highContrast = String(profile.highContrast)
  root.dataset.keyboardFirst = String(profile.keyboardFirst)
  root.style.setProperty('--a11y-text-scale', String(profile.textScale))
  root.style.setProperty('--a11y-text-scale-percent', `${profile.textScale * 100}%`)
}

function browserStorage(): AccessibilityStorage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage
  } catch {
    return null
  }
}

function browserRoot(): AccessibilityRoot | null {
  return typeof document === 'undefined' ? null : document.documentElement
}

function browserMatchMedia(): MediaMatcher | null {
  return typeof window === 'undefined' || typeof window.matchMedia !== 'function'
    ? null
    : window.matchMedia.bind(window)
}

export function useAccessibilityProfile(options: AccessibilityProfileOptions = {}) {
  const profile = sharedProfileState()
  const storage = options.storage === undefined ? browserStorage() : options.storage
  const root = options.root === undefined ? browserRoot() : options.root
  const matchMedia = options.matchMedia === undefined ? browserMatchMedia() : options.matchMedia

  function syncTheme(next: AccessibilityTheme) {
    if (options.colorMode) options.colorMode.preference = next === 'parchment' ? 'light' : 'dark'
  }

  function hydrate() {
    const selected = readAccessibilityPreferences(storage)
    profile.value = resolveAccessibilityProfile({
      ...selected,
      reducedMotion: matchMedia?.('(prefers-reduced-motion: reduce)').matches === true,
      highContrast: matchMedia?.('(prefers-contrast: more)').matches === true,
    })
    syncTheme(profile.value.theme)
    applyAccessibilityProfile(profile.value, root)
    return profile.value
  }

  function setProfile(values: Partial<AccessibilityProfile>) {
    profile.value = resolveAccessibilityProfile({ ...profile.value, ...values })
    persistAccessibilityPreferences(profile.value, storage)
    syncTheme(profile.value.theme)
    applyAccessibilityProfile(profile.value, root)
    return profile.value
  }

  if (options.autoHydrate !== false) onMounted(hydrate)

  return { profile, hydrate, setProfile }
}
