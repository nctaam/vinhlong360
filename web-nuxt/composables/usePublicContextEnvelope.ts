import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAccessibilityProfile } from './useAccessibilityProfile'
import { useRegionPref } from './useRegionPref'
import { usePersonalizationPreferences } from './usePersonalizationPreferences'
import type { ContextEnvelope } from '~/types/publicExperience'
import type { PreferenceSnapshot } from '~/types/personalization'

export function projectLocation(regionId: string | null, snapshot: PreferenceSnapshot) {
  const selected = regionId && regionId !== 'all' ? { id: regionId } : undefined
  const source = snapshot.location_source
  const inferred = source === 'gps' || source === 'ip'
  const mode = selected && source === 'manual' ? 'selected' : !snapshot.location_enabled || (!selected && !inferred) ? 'unavailable' : inferred ? (snapshot.location_accuracy === 'ward' ? 'exact' : 'approximate') : 'selected'
  const confidence = mode === 'exact' ? 'high' : mode === 'selected' ? 'medium' : 'low'
  return { mode, confidence, selected, source, accuracy: snapshot.location_accuracy } as const
}

export function usePublicContextEnvelope() {
  const region = useRegionPref()
  const preferences = usePersonalizationPreferences()
  const { profile } = useAccessibilityProfile()
  const ttlSeconds = 300
  // Nuxt serializes this shared sample so server and client begin with one time.
  const sampledAt = useState<number>('public-context-envelope-sampled-at', () => Date.now())
  const network = ref<ContextEnvelope['network']>('online')
  let refreshTimer: number | undefined

  function refreshTime() {
    sampledAt.value = Date.now()
  }

  function refreshNetwork() {
    network.value = typeof navigator !== 'undefined' && navigator.onLine === false ? 'offline' : 'online'
  }

  function markOnline() {
    network.value = 'online'
  }

  function markOffline() {
    network.value = 'offline'
  }

  onMounted(() => {
    refreshTime()
    refreshNetwork()
    window.addEventListener('online', markOnline)
    window.addEventListener('offline', markOffline)
    refreshTimer = window.setInterval(refreshTime, ttlSeconds * 1000)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('online', markOnline)
    window.removeEventListener('offline', markOffline)
    if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
  })

  const envelope = computed<ContextEnvelope>(() => {
    const now = new Date(sampledAt.value)
    const snapshot = preferences.snapshot.value
    const location = projectLocation(region.region.value, snapshot)
    const localParts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(now)
    const part = (type: string) => localParts.find(item => item.type === type)?.value || '00'
    return {
      version: 1, source: 'public-default', ttlSeconds, ...(location.selected ? { area: location.selected } : {}),
      location: { mode: location.mode, confidence: location.confidence, ...(location.source ? { source: location.source } : {}), ...(location.accuracy ? { accuracy: location.accuracy } : {}) },
      time: { localDate: `${part('year')}-${part('month')}-${part('day')}`, localTime: `${part('hour')}:${part('minute')}` },
      freshness: {},
      accessibility: {
        reducedMotion: profile.value.reducedMotion,
        highContrast: profile.value.highContrast,
        textScale: profile.value.textScale,
      },
      network: network.value,
      explainableSignals: location.mode === 'selected' ? ['selected-region'] : location.mode === 'unavailable' ? [] : ['location-signal'],
    }
  })
  return { envelope }
}
