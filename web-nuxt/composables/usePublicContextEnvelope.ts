import { computed } from 'vue'
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
  const envelope = computed<ContextEnvelope>(() => {
    const now = new Date()
    const snapshot = preferences.snapshot.value
    const location = projectLocation(region.region.value, snapshot)
    const localParts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(now)
    const part = (type: string) => localParts.find(item => item.type === type)?.value || '00'
    return {
      version: 1, source: 'public-default', ttlSeconds: 300, ...(location.selected ? { area: location.selected } : {}),
      location: { mode: location.mode, confidence: location.confidence, ...(location.source ? { source: location.source } : {}), ...(location.accuracy ? { accuracy: location.accuracy } : {}) },
      time: { localDate: `${part('year')}-${part('month')}-${part('day')}`, localTime: `${part('hour')}:${part('minute')}` },
      freshness: {}, accessibility: { reducedMotion: false, highContrast: false, textScale: 1 },
      network: 'online', explainableSignals: location.mode === 'selected' ? ['selected-region'] : location.mode === 'unavailable' ? [] : ['location-signal'],
    }
  })
  return { envelope }
}
