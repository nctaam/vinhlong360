import { computed, onMounted, watch } from 'vue'
import { usePersonalizationPreferences } from './usePersonalizationPreferences'
import type { PreferenceRegionChoice, PreferenceSnapshot } from '~/types/personalization'
import { entityMatchesAreaScope } from '~/utils/safe'

const STORAGE_KEY = 'vl360-region-pref'
const VISIT_KEY = 'vl360-visit-count'

export type RegionSlug = 'vinh-long' | 'ben-tre' | 'tra-vinh' | 'all'

const API_REGIONS: Record<'vinh-long', PreferenceRegionChoice> = {
  'vinh-long': { id: 'province-vl', label: 'Vĩnh Long', scope: 'province' },
}

function regionFromSnapshot(snapshot: PreferenceSnapshot): RegionSlug {
  if ((snapshot.location_source === 'gps' || snapshot.location_source === 'ip') && !snapshot.location_enabled) return 'all'
  if (snapshot.region_id === 'province-vl') return 'vinh-long'
  if (snapshot.region_id === 'province-bt' || snapshot.region_id === 'province-tv') return 'vinh-long'
  if (snapshot.region_label === 'Vĩnh Long') return 'vinh-long'
  if (snapshot.region_label === 'Bến Tre' || snapshot.region_label === 'Trà Vinh') return 'vinh-long'
  return 'all'
}

export function useRegionPref() {
  const { isLoggedIn } = useAuth()
  const preferences = usePersonalizationPreferences()
  const cachedRegion = useState<RegionSlug | null>('regionPref', () => null)
  const hydrated = useState<boolean>('regionPrefHydrated', () => false)
  const watcherBound = useState<boolean>('regionPrefWatcherBound', () => false)
  const region = computed<RegionSlug | null>(() => isLoggedIn.value ? regionFromSnapshot(preferences.snapshot.value) : cachedRegion.value)
  const visitCount = useState<number>('visitCount', () => 0)
  const isReturning = computed(() => visitCount.value > 1)
  const hasChosen = computed(() => isLoggedIn.value
    ? preferences.snapshot.value.location_source === 'manual' || !!preferences.snapshot.value.region_id
    : cachedRegion.value !== null)

  // Read persisted prefs only AFTER hydration. Applying localStorage during
  // setup desyncs SSR (region=null, unsorted) from the client (region=stored,
  // region-sorted), reordering lists mid-hydration — which binds clicks/save
  // buttons to the wrong card in production and floods dev with mismatch warnings.
  if (import.meta.client) {
    onMounted(() => {
      if (hydrated.value) return
      hydrated.value = true

      let stored: RegionSlug | null = null
      let rawVc = '0'
      try {
        stored = localStorage.getItem(STORAGE_KEY) as RegionSlug | null
        rawVc = localStorage.getItem(VISIT_KEY) || '0'
      } catch { /* storage blocked */ }

      if (stored === 'ben-tre' || stored === 'tra-vinh') {
        cachedRegion.value = 'vinh-long'
        try { localStorage.setItem(STORAGE_KEY, 'vinh-long') } catch { /* quota */ }
      }
      else if (stored === 'vinh-long' || stored === 'all') cachedRegion.value = stored

      const parsedVc = Number.parseInt(rawVc, 10)
      const safeVc = Number.isFinite(parsedVc) && parsedVc >= 0 ? parsedVc : 0
      visitCount.value = safeVc + 1
      try { localStorage.setItem(VISIT_KEY, String(visitCount.value)) } catch { /* quota */ }

      if (isLoggedIn.value) void preferences.refresh()
    })

    if (!watcherBound.value) {
      watcherBound.value = true
      watch(() => isLoggedIn.value, (authenticated) => {
        if (authenticated) void preferences.refresh()
      })
    }
  }

  async function setRegion(slug: RegionSlug) {
    const normalizedSlug: 'vinh-long' | 'all' = slug === 'ben-tre' || slug === 'tra-vinh' ? 'vinh-long' : slug
    if (isLoggedIn.value) {
      const choice = normalizedSlug === 'all'
        ? { id: null, label: 'Toàn tỉnh', scope: 'all' as const }
        : API_REGIONS[normalizedSlug]
      await preferences.setRegion(choice)
      return
    }
    cachedRegion.value = normalizedSlug
    if (import.meta.client) {
      try { localStorage.setItem(STORAGE_KEY, normalizedSlug) } catch { /* quota */ }
    }
  }

  function sortByRegion<T extends { place_area?: string; area?: string }>(items: T[]): T[] {
    if (!region.value || region.value === 'all') return items
    const pref = region.value
    return [...items].sort((a, b) => {
      const aMatch = entityMatchesAreaScope(a, pref) ? 1 : 0
      const bMatch = entityMatchesAreaScope(b, pref) ? 1 : 0
      return bMatch - aMatch
    })
  }

  function orderedAreaKeys(keys: string[]): string[] {
    if (!region.value || region.value === 'all') return keys
    const pref = region.value
    return [...keys].sort((a, b) => {
      if (a === pref) return -1
      if (b === pref) return 1
      return 0
    })
  }

  return { region, visitCount, isReturning, hasChosen, setRegion, sortByRegion, orderedAreaKeys }
}
