export type PreferenceRegionScope = 'ward' | 'district' | 'province' | 'all' | 'unknown'
export type PreferenceLocationSource = 'manual' | 'gps' | 'ip' | 'default'
export type PreferenceLocationAccuracy = 'ward' | 'district' | 'province' | 'unknown'
export type PreferenceConsentState = 'unknown' | 'granted' | 'denied' | 'off' | 'expired'
export type PreferenceAgeBand = 'under_18' | '18_24' | '25_34' | '35_49' | '50_plus' | 'unknown'

export interface PreferenceSnapshot {
  region_id: string | null
  region_label: string | null
  region_scope: PreferenceRegionScope
  location_source: PreferenceLocationSource
  location_accuracy: PreferenceLocationAccuracy
  location_consent_state: PreferenceConsentState
  location_enabled: boolean
  personalization_enabled: boolean
  explicit_interests: string[]
  recommendation_reset_at: string | null
  consent_version: string | null
  revision: number
  derived_age_band?: PreferenceAgeBand
}

export interface PreferenceRegionChoice {
  id: string | null
  label: string
  scope: PreferenceRegionScope
}

export interface LocationResolution {
  region_id: string | null
  region_label: string | null
  region_scope: PreferenceRegionScope
  location_source: Extract<PreferenceLocationSource, 'gps' | 'ip'>
  location_accuracy: PreferenceLocationAccuracy
  confirmation_token?: string
}

export interface GpsCoordinates {
  latitude: number
  longitude: number
}

export interface PreferencePatch {
  region_id?: string | null
  region_label?: string | null
  region_scope?: PreferenceRegionScope
  location_source?: PreferenceLocationSource
  location_accuracy?: PreferenceLocationAccuracy
  location_consent_state?: PreferenceConsentState
  location_enabled?: boolean
  personalization_enabled?: boolean
  explicit_interests?: string[]
  recommendation_reset_at?: string | null
  consent_version?: string | null
  location_confirmation_token?: string
}

export interface PreferenceMutationResult {
  ok: boolean
  snapshot: PreferenceSnapshot
  status: number | null
}

export const DEFAULT_PREFERENCE_SNAPSHOT: PreferenceSnapshot = {
  region_id: null,
  region_label: null,
  region_scope: 'unknown',
  location_source: 'default',
  location_accuracy: 'unknown',
  location_consent_state: 'unknown',
  location_enabled: false,
  personalization_enabled: false,
  explicit_interests: [],
  recommendation_reset_at: null,
  consent_version: null,
  revision: 0,
}

export function emptyPreferenceSnapshot(): PreferenceSnapshot {
  return {
    ...DEFAULT_PREFERENCE_SNAPSHOT,
    explicit_interests: [],
  }
}
