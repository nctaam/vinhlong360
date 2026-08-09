import { computed } from 'vue'
import { useRegionPref } from './useRegionPref'
import { usePersonalizationPreferences } from './usePersonalizationPreferences'
import type { ContextEnvelope } from '~/types/publicExperience'

export function usePublicContextEnvelope() {
  const region = useRegionPref()
  const envelope = computed<ContextEnvelope>(() => {
    const now = new Date()
    const snapshot = usePersonalizationPreferences().snapshot.value
    const selected = region.region.value && region.region.value !== 'all' ? { id: region.region.value } : undefined
    const source = snapshot.location_source
    const enabled = snapshot.location_enabled
    const inferred = source === 'gps' || source === 'ip'
    const locationMode = !enabled || (!selected && !inferred) ? 'unavailable' : inferred ? (snapshot.location_accuracy === 'ward' ? 'exact' : 'approximate') : 'selected'
    const locationConfidence = locationMode === 'exact' ? 'high' : locationMode === 'selected' ? 'medium' : locationMode === 'approximate' ? 'low' : 'low'
    const localParts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(now)
    const part = (type: string) => localParts.find(item => item.type === type)?.value || '00'
    return {
      version: 1, source: 'public-default', ttlSeconds: 300, ...(selected ? { area: selected } : {}),
      location: { mode: locationMode, confidence: locationConfidence, ...(source ? { source } : {}), ...(snapshot.location_accuracy ? { accuracy: snapshot.location_accuracy } : {}) },
      time: { localDate: `${part('year')}-${part('month')}-${part('day')}`, localTime: `${part('hour')}:${part('minute')}` },
      freshness: {}, accessibility: { reducedMotion: false, highContrast: false, textScale: 1 },
      network: 'online', explainableSignals: locationMode === 'selected' ? ['selected-region'] : locationMode === 'unavailable' ? [] : ['location-signal'],
    }
  })
  return { envelope }
}
