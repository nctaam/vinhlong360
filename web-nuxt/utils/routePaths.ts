export type RouteParamLike = string | number | Array<string | number> | null | undefined

export function normalizeRouteParam(value: RouteParamLike): string {
  const first = Array.isArray(value) ? value[0] : value
  return String(first ?? '').trim()
}

export function encodePathId(id: RouteParamLike): string {
  return encodeURIComponent(normalizeRouteParam(id))
}

export function entityPath(id: RouteParamLike): string {
  return `/dia-diem/${encodePathId(id)}`
}

export function postPath(id: RouteParamLike): string {
  return `/bai-viet/${encodePathId(id)}`
}

export function userPath(id: RouteParamLike): string {
  return `/nguoi-dung/${encodePathId(id)}`
}

export function itineraryPath(id: RouteParamLike): string {
  return `/lich-trinh/${encodePathId(id)}`
}

export function savedItemPath(item: {
  id?: RouteParamLike
  kind?: string | null
  type?: string | null
  ref_type?: string | null
}): string {
  const rawId = normalizeRouteParam(item?.id)
  const kind = String(item?.kind || item?.type || item?.ref_type || '').toLowerCase()
  if (kind === 'post') return postPath(rawId)
  if (kind === 'itinerary') {
    const id = rawId.startsWith('itinerary-') ? rawId.slice('itinerary-'.length) : rawId
    return itineraryPath(id)
  }
  if (rawId.startsWith('itinerary-')) return itineraryPath(rawId.slice('itinerary-'.length))
  return entityPath(rawId)
}

export function notificationTargetPath(n: { ref_type?: string | null; ref_id?: RouteParamLike }): string | null {
  if (!n?.ref_id) return null
  if (n.ref_type === 'post') return postPath(n.ref_id)
  if (n.ref_type === 'entity') return entityPath(n.ref_id)
  if (n.ref_type === 'itinerary') return itineraryPath(n.ref_id)
  if (n.ref_type === 'user') return userPath(n.ref_id)
  return null
}
