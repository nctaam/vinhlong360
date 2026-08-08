import { computed, onMounted, watch } from 'vue'
import { usePersonalizationPreferences } from './usePersonalizationPreferences'
import type { PreferenceRegionChoice, PreferenceSnapshot } from '~/types/personalization'

const STORAGE_KEY = 'vl360-region-pref'
const VISIT_KEY = 'vl360-visit-count'

export type RegionSlug = 'vinh-long' | 'ben-tre' | 'tra-vinh' | 'all'

const API_REGIONS: Record<Exclude<RegionSlug, 'all'>, PreferenceRegionChoice> = {
  'vinh-long': { id: 'province-vl', label: 'Vĩnh Long', scope: 'province' },
  'ben-tre': { id: 'province-bt', label: 'Bến Tre', scope: 'province' },
  'tra-vinh': { id: 'province-tv', label: 'Trà Vinh', scope: 'province' },
}

function regionFromSnapshot(snapshot: PreferenceSnapshot): RegionSlug {
  if ((snapshot.location_source === 'gps' || snapshot.location_source === 'ip') && !snapshot.location_enabled) return 'all'
  if (snapshot.region_id === 'province-vl') return 'vinh-long'
  if (snapshot.region_id === 'province-bt') return 'ben-tre'
  if (snapshot.region_id === 'province-tv') return 'tra-vinh'
  if (snapshot.region_label === 'Vĩnh Long') return 'vinh-long'
  if (snapshot.region_label === 'Bến Tre') return 'ben-tre'
  if (snapshot.region_label === 'Trà Vinh') return 'tra-vinh'
  return 'all'
}

export function useRegionPref() {
  const { isLoggedIn } = useAuth()
  const preferences = usePersonalizationPreferences()
  const cachedRegion = useState<RegionSlug | null>('regionPref', () => null)
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
      const stored = localStorage.getItem(STORAGE_KEY) as RegionSlug | null
      if (stored && ['vinh-long', 'ben-tre', 'tra-vinh', 'all'].includes(stored)) cachedRegion.value = stored

      const vc = parseInt(localStorage.getItem(VISIT_KEY) || '0', 10)
      visitCount.value = vc + 1
      try { localStorage.setItem(VISIT_KEY, String(visitCount.value)) } catch { /* quota */ }

      if (isLoggedIn.value) void preferences.refresh()
    })
  }

  watch(() => isLoggedIn.value, (authenticated) => {
    if (import.meta.client && authenticated) void preferences.refresh()
  })

  async function setRegion(slug: RegionSlug) {
    if (isLoggedIn.value) {
      const choice = slug === 'all'
        ? { id: null, label: 'Toàn tỉnh', scope: 'all' as const }
        : API_REGIONS[slug]
      await preferences.setRegion(choice)
      return
    }
    cachedRegion.value = slug
    if (import.meta.client) {
      try { localStorage.setItem(STORAGE_KEY, slug) } catch { /* quota */ }
    }
  }

  function sortByRegion<T extends { place_area?: string; area?: string }>(items: T[]): T[] {
    if (!region.value || region.value === 'all') return items
    const pref = region.value
    return [...items].sort((a, b) => {
      const aMatch = (a.place_area || a.area) === pref ? 1 : 0
      const bMatch = (b.place_area || b.area) === pref ? 1 : 0
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
