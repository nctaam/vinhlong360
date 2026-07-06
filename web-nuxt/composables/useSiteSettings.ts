// Single shared handler + options so EVERY caller of the 'site-settings' key uses
// the same useAsyncData registration. Passing different closures/options across
// callers triggers Nuxt's "Incompatible options detected (different handler)"
// warning and breaks SSR-payload sharing → the brand wordmark flashes its fallback
// then swaps. One reference = one dedup = one render.
const SETTINGS_KEY = 'site-settings'
const fetchSiteSettings = () => apiFetch<Record<string, unknown>>('/api/site-settings')
const SETTINGS_OPTS = { server: true, default: () => ({}) }

/** Underlying shared useAsyncData for site settings — used by useSiteSettings()
 *  and by plugins/site-overrides.ts (awaited) so both share one fetch. */
export function useSiteSettingsData() {
  return useAsyncData(SETTINGS_KEY, fetchSiteSettings, SETTINGS_OPTS)
}

export function useSiteSettings() {
  const { data } = useSiteSettingsData()

  function get<T>(key: string, fallback: T): T {
    const val = (data.value as Record<string, unknown> | null | undefined)?.[key]
    return (val !== undefined && val !== null ? val : fallback) as T
  }

  return { settings: data, get }
}
