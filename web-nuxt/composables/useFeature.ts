import { featureFlagDefault } from '~/utils/featureFlags'

/**
 * A4 — read feature flags from the CMS.
 * `enabled(key)`: explicit override in `features.flags` → registry default →
 * true. Default-true means nothing disappears until an admin opts out.
 */
export function useFeature() {
  const { get } = useSiteSettings()
  const flags = computed<Record<string, boolean>>(
    () => (get('features.flags', {}) as Record<string, boolean>) || {},
  )

  function enabled(key: string): boolean {
    const v = flags.value?.[key]
    return typeof v === 'boolean' ? v : featureFlagDefault(key)
  }

  return { flags, enabled }
}
