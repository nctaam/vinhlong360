import { apiFetch } from '~/utils/apiFetch'
import type {
  GpsCoordinates,
  LocationResolution,
  PreferenceConsentState,
  PreferenceAgeBand,
  PreferenceLocationAccuracy,
  PreferenceLocationSource,
  PreferenceMutationResult,
  PreferencePatch,
  PreferenceRegionChoice,
  PreferenceRegionScope,
  PreferenceSnapshot,
} from '~/types/personalization'
import { emptyPreferenceSnapshot } from '~/types/personalization'

const REGION_SCOPES = new Set<PreferenceRegionScope>(['ward', 'district', 'province', 'all', 'unknown'])
const LOCATION_SOURCES = new Set<PreferenceLocationSource>(['manual', 'gps', 'ip', 'default'])
const LOCATION_ACCURACIES = new Set<PreferenceLocationAccuracy>(['ward', 'district', 'province', 'unknown'])
const CONSENT_STATES = new Set<PreferenceConsentState>(['unknown', 'granted', 'denied', 'off', 'expired'])
const AGE_BANDS = new Set<PreferenceAgeBand>(['under_18', '18_24', '25_34', '35_49', '50_plus', 'unknown'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function nullableText(value: unknown): value is string | null {
  return value === null || typeof value === 'string'
}

function normalizeInterests(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null
  const values: string[] = []
  const seen = new Set<string>()
  for (const item of value) {
    if (typeof item !== 'string') return null
    const normalized = item.trim()
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    values.push(normalized)
    if (values.length === 12) break
  }
  return values
}

function isSnapshot(value: unknown): value is PreferenceSnapshot {
  if (!isRecord(value)) return false
  const revision = value.revision
  return Number.isInteger(revision) && Number(revision) >= 0
    && nullableText(value.region_id)
    && nullableText(value.region_label)
    && REGION_SCOPES.has(value.region_scope as PreferenceRegionScope)
    && LOCATION_SOURCES.has(value.location_source as PreferenceLocationSource)
    && LOCATION_ACCURACIES.has(value.location_accuracy as PreferenceLocationAccuracy)
    && CONSENT_STATES.has(value.location_consent_state as PreferenceConsentState)
    && typeof value.location_enabled === 'boolean'
    && typeof value.personalization_enabled === 'boolean'
    && normalizeInterests(value.explicit_interests) !== null
    && nullableText(value.recommendation_reset_at)
    && nullableText(value.consent_version)
    && (value.derived_age_band === undefined || AGE_BANDS.has(value.derived_age_band as PreferenceAgeBand))
}

function normalizeSnapshot(value: unknown): PreferenceSnapshot {
  if (!isSnapshot(value)) return emptyPreferenceSnapshot()
  return {
    region_id: value.region_id,
    region_label: value.region_label,
    region_scope: value.region_scope,
    location_source: value.location_source,
    location_accuracy: value.location_accuracy,
    location_consent_state: value.location_consent_state,
    location_enabled: value.location_enabled,
    personalization_enabled: value.personalization_enabled,
    explicit_interests: normalizeInterests(value.explicit_interests) || [],
    recommendation_reset_at: value.recommendation_reset_at,
    consent_version: value.consent_version,
    revision: value.revision,
    ...(value.derived_age_band ? { derived_age_band: value.derived_age_band } : {}),
  }
}

function normalizeResolution(value: unknown, source: Extract<PreferenceLocationSource, 'gps' | 'ip'>): LocationResolution {
  if (!isRecord(value)) {
    return {
      region_id: null,
      region_label: null,
      region_scope: 'unknown',
      location_source: source,
      location_accuracy: 'unknown',
    }
  }
  const regionId = nullableText(value.region_id) ? value.region_id : null
  const regionLabel = nullableText(value.region_label) ? value.region_label : null
  const regionScope = REGION_SCOPES.has(value.region_scope as PreferenceRegionScope)
    ? value.region_scope as PreferenceRegionScope
    : 'unknown'
  const locationAccuracy = LOCATION_ACCURACIES.has(value.location_accuracy as PreferenceLocationAccuracy)
    ? value.location_accuracy as PreferenceLocationAccuracy
    : 'unknown'
  return {
    region_id: regionId,
    region_label: regionLabel,
    region_scope: regionScope,
    location_source: source,
    location_accuracy: locationAccuracy,
  }
}

function errorMessage(error: unknown, fallback: string): string {
  if (isRecord(error)) {
    const data = isRecord(error.data) ? error.data : isRecord(error.response) && isRecord(error.response._data) ? error.response._data : null
    if (data && typeof data.detail === 'string') return data.detail
    if (data && typeof data.message === 'string') return data.message
  }
  return fallback
}

function conflictSnapshot(error: unknown): PreferenceSnapshot | null {
  if (!isRecord(error)) return null
  const data = isRecord(error.data) ? error.data : isRecord(error.response) && isRecord(error.response._data) ? error.response._data : null
  return isSnapshot(data) ? normalizeSnapshot(data) : null
}

function errorStatus(error: unknown): number | null {
  if (!isRecord(error)) return null
  const responseStatus = isRecord(error.response) ? error.response.status : null
  const status = responseStatus ?? error.statusCode ?? error.status
  return typeof status === 'number' && Number.isInteger(status) ? status : null
}

export function usePersonalizationPreferences() {
  const { user, isLoggedIn, authHeaders, fetchCsrf } = useAuth()
  const snapshot = useState<PreferenceSnapshot>('personalization-preferences-snapshot', emptyPreferenceSnapshot)
  const loading = useState<boolean>('personalization-preferences-loading', () => false)
  const error = useState<string | null>('personalization-preferences-error', () => null)
  const ownerId = useState<string | null>('personalization-preferences-owner', () => null)
  const ownerGeneration = useState<number>('personalization-preferences-generation', () => 0)
  const readGeneration = useState<number>('personalization-preferences-read-generation', () => 0)
  const writeGeneration = useState<number>('personalization-preferences-write-generation', () => 0)
  const resolutionGeneration = useState<number>('personalization-preferences-resolution-generation', () => 0)
  const pendingOperations = useState<number>('personalization-preferences-pending-operations', () => 0)
  const activeWrites = useState<number>('personalization-preferences-active-writes', () => 0)

  function currentOwner(): string | null {
    return isLoggedIn.value ? user.value?.id || null : null
  }

  function syncOwner(): string | null {
    const owner = currentOwner()
    if (ownerId.value !== owner) {
      ownerId.value = owner
      snapshot.value = emptyPreferenceSnapshot()
      loading.value = false
      error.value = null
      pendingOperations.value = 0
      activeWrites.value = 0
      ownerGeneration.value += 1
      readGeneration.value += 1
      writeGeneration.value += 1
      resolutionGeneration.value += 1
    }
    return owner
  }

  function beginOperation(owner: string) {
    pendingOperations.value += 1
    loading.value = true
    error.value = null
    return { owner, ownerToken: ownerGeneration.value }
  }

  function isCurrentOwner(operation: { owner: string; ownerToken: number }) {
    if (ownerId.value !== currentOwner()) syncOwner()
    return ownerGeneration.value === operation.ownerToken
      && ownerId.value === operation.owner
      && currentOwner() === operation.owner
  }

  function finishOperation(operation: { owner: string; ownerToken: number }) {
    if (!isCurrentOwner(operation)) return
    pendingOperations.value = Math.max(0, pendingOperations.value - 1)
    loading.value = pendingOperations.value > 0
  }

  function beginRead(owner: string) {
    return {
      ...beginOperation(owner),
      readToken: ++readGeneration.value,
      writeToken: writeGeneration.value,
    }
  }

  function isCurrentRead(operation: ReturnType<typeof beginRead>) {
    return isCurrentOwner(operation)
      && readGeneration.value === operation.readToken
      && writeGeneration.value === operation.writeToken
      && activeWrites.value === 0
  }

  function beginWrite(owner: string) {
    activeWrites.value += 1
    return {
      ...beginOperation(owner),
      writeToken: ++writeGeneration.value,
    }
  }

  function isCurrentWrite(operation: ReturnType<typeof beginWrite>) {
    return isCurrentOwner(operation) && writeGeneration.value === operation.writeToken
  }

  function finishWrite(operation: ReturnType<typeof beginWrite>, invalidateReads: boolean) {
    if (isCurrentOwner(operation)) {
      activeWrites.value = Math.max(0, activeWrites.value - 1)
      if (invalidateReads && writeGeneration.value === operation.writeToken) {
        writeGeneration.value += 1
      }
    }
    finishOperation(operation)
  }

  function beginResolution(owner: string) {
    return {
      ...beginOperation(owner),
      resolutionToken: ++resolutionGeneration.value,
    }
  }

  function isCurrentResolution(operation: ReturnType<typeof beginResolution>) {
    return isCurrentOwner(operation) && resolutionGeneration.value === operation.resolutionToken
  }

  function mutationResult(ok: boolean, status: number | null = null): PreferenceMutationResult {
    return { ok, snapshot: snapshot.value, status }
  }

  syncOwner()
  watch(() => [isLoggedIn.value, user.value?.id] as const, syncOwner)

  async function refresh(): Promise<boolean> {
    const owner = syncOwner()
    if (!owner) return false
    const operation = beginRead(owner)
    try {
      const response = await apiFetch<unknown>('/api/me/preferences', {
        credentials: 'include',
        headers: authHeaders(),
      })
      if (!isCurrentRead(operation)) return false
      snapshot.value = normalizeSnapshot(response)
      return true
    } catch (reason) {
      if (isCurrentRead(operation)) {
        error.value = errorMessage(reason, 'Không thể tải thiết lập cá nhân hóa.')
      }
      return false
    } finally {
      finishOperation(operation)
    }
  }

  async function patch(values: PreferencePatch): Promise<PreferenceMutationResult> {
    const owner = syncOwner()
    if (!owner) return mutationResult(false)
    const operation = beginWrite(owner)
    const revision = snapshot.value.revision
    let invalidateReads = false
    try {
      await fetchCsrf()
      if (!isCurrentWrite(operation)) return mutationResult(false)
      const response = await apiFetch<unknown>('/api/me/preferences', {
        method: 'PATCH',
        credentials: 'include',
        headers: authHeaders(),
        body: { ...values, revision },
      })
      if (!isCurrentWrite(operation)) return mutationResult(false)
      const normalized = normalizeSnapshot(response)
      snapshot.value = normalized
      invalidateReads = true
      return mutationResult(true)
    } catch (reason) {
      const status = errorStatus(reason)
      if (!isCurrentWrite(operation)) return mutationResult(false)
      if (status === 409) {
        const current = conflictSnapshot(reason)
        if (current) snapshot.value = current
      }
      error.value = errorMessage(reason, 'Không thể lưu thiết lập cá nhân hóa.')
      invalidateReads = true
      return mutationResult(false, status)
    } finally {
      finishWrite(operation, invalidateReads)
    }
  }

  async function resolveLocation(mode: Extract<PreferenceLocationSource, 'gps' | 'ip'>, coords?: GpsCoordinates) {
    const owner = syncOwner()
    if (!owner) return normalizeResolution(null, mode)
    const operation = beginResolution(owner)
    try {
      await fetchCsrf()
      if (!isCurrentResolution(operation)) return normalizeResolution(null, mode)
      const body = mode === 'gps'
        ? { mode, latitude: coords?.latitude, longitude: coords?.longitude }
        : { mode }
      const response = await apiFetch<unknown>('/api/me/location/resolve', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders(),
        body,
      })
      if (!isCurrentResolution(operation)) return normalizeResolution(null, mode)
      return normalizeResolution(response, mode)
    } catch {
      if (isCurrentResolution(operation)) error.value = 'Không thể xác định khu vực lúc này.'
      return normalizeResolution(null, mode)
    } finally {
      finishOperation(operation)
    }
  }

  async function resetRecommendations(): Promise<PreferenceMutationResult> {
    const owner = syncOwner()
    if (!owner) return mutationResult(false)
    const operation = beginWrite(owner)
    let invalidateReads = false
    try {
      await fetchCsrf()
      if (!isCurrentWrite(operation)) return mutationResult(false)
      const response = await apiFetch<unknown>('/api/me/recommendations/reset', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders(),
      })
      if (!isCurrentWrite(operation)) return mutationResult(false)
      const normalized = normalizeSnapshot(response)
      snapshot.value = normalized
      invalidateReads = true
      return mutationResult(true)
    } catch (reason) {
      const status = errorStatus(reason)
      if (!isCurrentWrite(operation)) return mutationResult(false)
      error.value = errorMessage(reason, 'Không thể đặt lại đề xuất lúc này.')
      invalidateReads = true
      return mutationResult(false, status)
    } finally {
      finishWrite(operation, invalidateReads)
    }
  }

  async function setRegion(region: PreferenceRegionChoice) {
    const accuracy: PreferenceLocationAccuracy = region.scope === 'ward' || region.scope === 'district' || region.scope === 'province'
      ? region.scope
      : 'unknown'
    return patch({
      region_id: region.id,
      region_label: region.id ? region.label : null,
      region_scope: region.scope,
      location_source: 'manual',
      location_accuracy: accuracy,
    })
  }

  async function setInterests(interests: string[]) {
    const bounded: string[] = []
    const seen = new Set<string>()
    for (const interest of interests) {
      if (typeof interest !== 'string') continue
      const normalized = interest.trim()
      if (!normalized || seen.has(normalized)) continue
      seen.add(normalized)
      bounded.push(normalized)
      if (bounded.length === 3) break
    }
    return patch({ explicit_interests: bounded })
  }

  async function revokeLocation() {
    return patch({ location_enabled: false, location_consent_state: 'off' })
  }

  return {
    snapshot,
    loading,
    error,
    refresh,
    patch,
    resolveLocation,
    resetRecommendations,
    setRegion,
    setInterests,
    revokeLocation,
  }
}
