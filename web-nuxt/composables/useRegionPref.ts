const STORAGE_KEY = 'vl360-region-pref'
const VISIT_KEY = 'vl360-visit-count'

export type RegionSlug = 'vinh-long' | 'ben-tre' | 'tra-vinh' | 'all'

export function useRegionPref() {
  const region = useState<RegionSlug | null>('regionPref', () => null)
  const visitCount = useState<number>('visitCount', () => 0)
  const isReturning = computed(() => visitCount.value > 1)
  const hasChosen = computed(() => region.value !== null)

  // Read persisted prefs only AFTER hydration. Applying localStorage during
  // setup desyncs SSR (region=null, unsorted) from the client (region=stored,
  // region-sorted), reordering lists mid-hydration — which binds clicks/save
  // buttons to the wrong card in production and floods dev with mismatch warnings.
  if (import.meta.client) {
    onMounted(() => {
      const stored = localStorage.getItem(STORAGE_KEY) as RegionSlug | null
      if (stored) region.value = stored

      const vc = parseInt(localStorage.getItem(VISIT_KEY) || '0', 10)
      visitCount.value = vc + 1
      localStorage.setItem(VISIT_KEY, String(visitCount.value))
    })
  }

  function setRegion(slug: RegionSlug) {
    region.value = slug
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, slug)
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
