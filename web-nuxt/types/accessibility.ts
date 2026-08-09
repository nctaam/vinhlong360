export type AccessibilityTheme = 'nocturne' | 'parchment'
export type AccessibilityDensity = 'comfortable' | 'compact'
export type AccessibilityTextScale = 1 | 1.25 | 1.5 | 2

export interface AccessibilityProfile {
  theme: AccessibilityTheme
  density: AccessibilityDensity
  textScale: AccessibilityTextScale
  reducedMotion: boolean
  highContrast: boolean
  keyboardFirst: boolean
}

export type AccessibilityPreferences = Pick<AccessibilityProfile, 'theme' | 'density' | 'textScale'>

export const DEFAULT_ACCESSIBILITY_PROFILE: AccessibilityProfile = Object.freeze({
  theme: 'nocturne',
  density: 'comfortable',
  textScale: 1,
  reducedMotion: false,
  highContrast: false,
  keyboardFirst: false,
})
