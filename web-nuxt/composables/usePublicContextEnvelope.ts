import { computed } from 'vue'
import { useRegionPref } from './useRegionPref'
import type { ContextEnvelope } from '~/types/publicExperience'

export function usePublicContextEnvelope() {
  const region = useRegionPref()
  const envelope = computed<ContextEnvelope>(() => {
    const now = new Date()
    const selected = region.region.value && region.region.value !== 'all' ? { id: region.region.value } : undefined
    return {
      version: 1, source: 'public-default', ttlSeconds: 300, ...(selected ? { area: selected } : {}),
      location: { mode: selected ? 'selected' : 'unavailable', confidence: selected ? 'medium' : 'low' },
      time: { localDate: now.toISOString().slice(0, 10), localTime: now.toISOString().slice(11, 16) },
      freshness: {}, accessibility: { reducedMotion: false, highContrast: false, textScale: 1 },
      network: 'online', explainableSignals: selected ? ['selected-region'] : [],
    }
  })
  return { envelope }
}
