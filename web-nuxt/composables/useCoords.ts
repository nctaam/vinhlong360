// GĐ10.4: gom logic chuẩn hoá toạ độ (trước trùng ở ban-do.vue + dia-diem/[id].vue).
// Trả [lat, lng] hợp lệ hoặc null. Chấp nhận chuỗi JSON lồng, object {lat,lng}, mảng;
// tự hoán đổi nếu lat/lng bị đảo.
function coordinateMember(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string' || !value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function normalizeCoords(raw: unknown): [number, number] | null {
  let coords = raw
  for (let i = 0; i < 3 && typeof coords === 'string'; i++) {
    try { coords = JSON.parse(coords) } catch { return null }
  }
  if (coords && !Array.isArray(coords) && typeof coords === 'object') {
    const obj = coords as Record<string, unknown>
    coords = [obj.lat ?? obj.latitude, obj.lng ?? obj.lon ?? obj.longitude]
  }
  if (!Array.isArray(coords) || coords.length !== 2) return null
  let lat = coordinateMember(coords[0])
  let lng = coordinateMember(coords[1])
  if (lat === null || lng === null) return null
  if (Math.abs(lat) > 90 && Math.abs(lng) <= 90) {
    ;[lat, lng] = [lng, lat]
  }
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
  return [lat, lng]
}

export function useCoords() {
  return { normalizeCoords }
}
