export type RegionalAccent = 'clay' | 'leaf' | 'river' | 'amber' | 'neutral'
export type SourceTier = 'official' | 'verified' | 'community' | 'unknown'
export type FreshnessStatus = 'fresh' | 'aging' | 'stale' | 'unknown'

const REGIONAL_ACCENT_BY_CATEGORY: Readonly<Record<string, RegionalAccent>> = Object.freeze({
  craft: 'clay',
  craft_village: 'clay',
  pottery: 'clay',
  product: 'clay',
  nature: 'leaf',
  agriculture: 'leaf',
  orchard: 'leaf',
  experience: 'river',
  accommodation: 'river',
  transport: 'river',
  river: 'river',
  dish: 'amber',
  food: 'amber',
  event: 'amber',
  festival: 'amber',
  season: 'amber',
})

const SOURCE_TIER_ALIASES: Readonly<Record<string, SourceTier>> = Object.freeze({
  official: 'official',
  government: 'official',
  gov: 'official',
  verified: 'verified',
  partner: 'verified',
  community: 'community',
  ugc: 'community',
})

export function resolveRegionalAccent(category?: string | null): RegionalAccent {
  if (typeof category !== 'string') return 'neutral'
  return REGIONAL_ACCENT_BY_CATEGORY[category.trim().toLowerCase()] || 'neutral'
}

export function resolveSourceTier(sourceTier?: unknown): SourceTier {
  if (typeof sourceTier !== 'string') return 'unknown'
  return SOURCE_TIER_ALIASES[sourceTier.trim().toLowerCase()] || 'unknown'
}

export function resolveFreshnessStatus(status?: unknown): FreshnessStatus {
  return status === 'fresh' || status === 'aging' || status === 'stale' ? status : 'unknown'
}
