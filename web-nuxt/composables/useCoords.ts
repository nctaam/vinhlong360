// GĐ10.4: gom logic chuẩn hoá toạ độ (trước trùng ở ban-do.vue + dia-diem/[id].vue).
// Trả [lat, lng] hợp lệ hoặc null. Chấp nhận chuỗi JSON lồng, object {lat,lng}, mảng;
// tự hoán đổi nếu lat/lng bị đảo.
export function normalizeCoords(raw: unknown): [number, number] | null {
  let coords = raw
  for (let i = 0; i < 3 && typeof coords === 'string'; i++) {
    try { coords = JSON.parse(coords) } catch { return null }
  }
  if (coords && !Array.isArray(coords) && typeof coords === 'object') {
    coords = [coords.lat ?? coords.latitude, coords.lng ?? coords.lon ?? coords.longitude]
  }
  if (!Array.isArray(coords) || coords.length !== 2) return null
  let lat = Number(coords[0])
  let lng = Number(coords[1])
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
  if (Math.abs(lat) > 90 && Math.abs(lng) <= 90) {
    ;[lat, lng] = [lng, lat]
  }
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
  return [lat, lng]
}

export function useCoords() {
  return { normalizeCoords }
}
