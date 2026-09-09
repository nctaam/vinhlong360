import { getStatusCode } from '~/composables/useFetchError'
import { serializePlanStops, type PlannerStopFreshnessEvidence } from '~/composables/useItineraryOptimization'

export interface PlanStop {
  id: string
  name: string
  type: string
  place_name?: string
  coords: [number, number] | null
  time: string
  notes: string
  sourceFreshness?: PlannerStopFreshnessEvidence
}

export interface SavedPlan {
  id?: string          // có khi đồng-bộ tài-khoản (server); thiếu = plan local (khách)
  title: string
  stops: PlanStop[]
  savedAt: string
  is_public?: boolean
  revision?: number
  updatedAt?: string
}

export interface PlanSnapshot extends SavedPlan {
  id: string
  revision: number
  updatedAt: string
}

export interface PlannerConflictDifference {
  key: string
  name: string
  detail: string
}

export type OpeningHourConflict = {
  stopId: string
  requestedTime?: string | null
  openingHours?: string | null
  title?: string
  detail?: string
  code?: string
  severity?: string
}

export function positiveRevision(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0
}

export function plannerStopFromDraft(stop: PlanStop): PlanStop {
  const serialized = serializePlanStops([stop])[0] as PlanStop
  return stop.sourceFreshness
    ? { ...serialized, sourceFreshness: { ...stop.sourceFreshness } }
    : serialized
}

export function normalizePlanSnapshot(value: unknown): PlanSnapshot | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const candidate = value as Record<string, unknown>
  if (typeof candidate.id !== 'string' || !candidate.id.trim()
    || typeof candidate.title !== 'string'
    || !Array.isArray(candidate.stops)
    || typeof candidate.savedAt !== 'string'
    || !positiveRevision(candidate.revision)
    || typeof candidate.updatedAt !== 'string'
    || !candidate.updatedAt.trim()) return null
  return {
    id: candidate.id,
    title: candidate.title,
    stops: serializePlanStops(candidate.stops as PlanStop[]) as PlanStop[],
    savedAt: candidate.savedAt,
    revision: candidate.revision,
    updatedAt: candidate.updatedAt,
    ...(typeof candidate.is_public === 'boolean' ? { is_public: candidate.is_public } : {}),
  }
}

export function conflictSnapshot(error: unknown, expectedPlanId: string | null = null): PlanSnapshot | null {
  if (getStatusCode(error) !== 409) return null
  const failure = error as {
    response?: { _data?: Record<string, unknown> }
    data?: Record<string, unknown>
  }
  const payload = failure.response?._data ?? failure.data
  if (payload?.code !== 'plan_revision_conflict') return null
  const snapshot = normalizePlanSnapshot(payload.current)
  return snapshot?.id === expectedPlanId ? snapshot : null
}

export function diffPlannerPlanStops(local: PlanStop[], server: PlanStop[]): PlannerConflictDifference[] {
  const indexStops = (items: PlanStop[]) => {
    const occurrences = new Map<string, number>()
    const indexed = new Map<string, { stop: PlanStop; index: number }>()
    items.forEach((stop, index) => {
      const occurrence = occurrences.get(stop.id) ?? 0
      occurrences.set(stop.id, occurrence + 1)
      indexed.set(`${stop.id}:${occurrence}`, { stop, index })
    })
    return indexed
  }
  const localStops = indexStops(local)
  const serverStops = indexStops(server)
  const keys = [...new Set([...localStops.keys(), ...serverStops.keys()])]
  const labels: Record<string, string> = {
    name: 'Tên điểm',
    place_name: 'Khu vực',
    type: 'Loại điểm',
    coords: 'Tọa độ',
    time: 'Thời gian',
    notes: 'Ghi chú',
  }
  return keys.flatMap((key) => {
    const localEntry = localStops.get(key)
    const serverEntry = serverStops.get(key)
    const localStop = localEntry?.stop
    const serverStop = serverEntry?.stop
    const name = localStop?.name || serverStop?.name || key
    if (!localStop) return [{ key, name, detail: 'Chỉ có trên máy chủ' }]
    if (!serverStop) return [{ key, name, detail: 'Chỉ có trong bản cục bộ' }]
    const changed = Object.keys(labels).filter(field => (
      JSON.stringify(localStop[field as keyof PlanStop]) !== JSON.stringify(serverStop[field as keyof PlanStop])
    )).map(field => labels[field])
    if (localEntry.index !== serverEntry.index) changed.unshift('Thứ tự')
    return changed.length ? [{ key, name, detail: changed.join(', ') }] : []
  })
}
