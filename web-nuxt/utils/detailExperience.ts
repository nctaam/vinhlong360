type UnknownRecord = Record<string, unknown>

export type DetailFetchResolution =
  | { kind: 'not_found' }
  | { kind: 'hidden'; retryable: false }
  | { kind: 'error'; retryable: true }

export type DetailActionContext = {
  family: 'entity' | 'ward'
  id: string
}

export type DetailAction = {
  id: 'directions' | 'call' | 'plan' | 'browse'
  label: string
  href: string
}

type DetailActionEntity = {
  coords?: unknown
  coordinates?: unknown
  phone?: unknown
}

function record(value: unknown): UnknownRecord | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as UnknownRecord
    : null
}

function detailValue(error: unknown): string {
  const source = record(error)
  if (!source) return ''
  const response = record(source.response)
  const responseData = record(response?._data)
  const data = record(source.data)
  const detail = responseData?.detail ?? data?.detail ?? source.detail ?? source.kind
  return typeof detail === 'string' ? detail.trim().toLowerCase() : ''
}

function statusValue(error: unknown): number | null {
  const source = record(error)
  if (!source) return null
  const response = record(source.response)
  const status = response?.status ?? source.statusCode ?? source.status
  return typeof status === 'number' && Number.isInteger(status) ? status : null
}

export function resolveDetailFetchError(error: unknown): DetailFetchResolution {
  const detail = detailValue(error)
  const status = statusValue(error)
  if (status === 404 && detail === 'not_found') return { kind: 'not_found' }
  if (detail === 'hidden' || detail === 'private') return { kind: 'hidden', retryable: false }
  return { kind: 'error', retryable: true }
}

function validCoordinates(value: unknown): [number, number] | null {
  if (Array.isArray(value) && value.length >= 2) {
    const lat = Number(value[0])
    const lng = Number(value[1])
    return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180
      ? [lat, lng]
      : null
  }
  const source = record(value)
  if (!source) return null
  return validCoordinates([source.lat, source.lng])
}

function validPhone(value: unknown): string {
  if (typeof value !== 'string') return ''
  const normalized = value.trim()
  if (!normalized || !/^\+?[\d\s().-]+$/.test(normalized)) return ''
  const digits = normalized.replace(/\D/g, '')
  return digits.length >= 4 && digits.length <= 15 ? normalized.replace(/[\s().-]+/g, '') : ''
}

export function resolveDetailAction(entity: DetailActionEntity, context: DetailActionContext): DetailAction {
  const coords = validCoordinates(entity.coords ?? entity.coordinates)
  if (coords) {
    const params = new URLSearchParams({
      ...(context.family === 'entity' ? { id: context.id } : {}),
      lat: String(coords[0]),
      lng: String(coords[1]),
    })
    return { id: 'directions', label: 'Chỉ đường', href: `/ban-do?${params.toString()}` }
  }

  const phone = validPhone(entity.phone)
  if (phone) return { id: 'call', label: 'Gọi', href: `tel:${phone}` }

  if (context.family === 'ward') {
    return { id: 'browse', label: 'Xem địa điểm trong khu vực', href: '/danh-ba' }
  }
  return {
    id: 'plan',
    label: 'Thêm vào lịch trình',
    href: `/tao-lich-trinh?add=${encodeURIComponent(context.id)}`,
  }
}
