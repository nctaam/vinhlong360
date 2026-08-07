/**
 * useContactBeacon — đo lượt bấm CTA liên hệ (Gọi / Nhắn Zalo / Website / Chỉ đường).
 *
 * Bắn `POST /api/entities/{id}/view-contact?action=...` (agent/public_api.py:3382)
 * theo kiểu fire-and-forget. Backend chỉ ghi `entity_id`, `action`, timestamp và hash
 * rút gọn của IP — **không** có dữ liệu cá nhân nào do frontend gửi lên.
 *
 * BẤT BIẾN — đo KHÔNG được cản người dùng:
 *  1. Hàm này **đồng bộ** và không trả Promise. Không caller nào `await` được nó,
 *     nên `tel:` / `zalo.me` / bản đồ luôn điều hướng ngay trong cùng nhịp click.
 *  2. `keepalive: true` — bấm `tel:` là trình duyệt rời trang, request thường sẽ
 *     bị huỷ giữa chừng; keepalive cho phép nó chạy nốt sau khi document teardown.
 *  3. Mọi lỗi (mạng, 429, 500, fetch không tồn tại) đều bị nuốt im lặng. Endpoint
 *     chết thì nút vẫn hoạt động 100%.
 *  4. `credentials: 'omit'` — không gửi cookie phiên. Đo lưu lượng, không đo người.
 *
 * Chống gửi trùng: cùng (entity, action) trong `DEDUPE_MS` chỉ tính 1 lần — người
 * dùng bấm đúp / bấm lại vì trang chưa nhảy sẽ không đốt rate-limit (10 lượt/60s/IP).
 */

export type ContactAction = 'phone' | 'zalo' | 'website' | 'map'

const DEDUPE_MS = 2000
const MAX_TRACKED_KEYS = 64

/** Lần bắn gần nhất theo khoá `${entityId}:${action}`. Chỉ sống ở client. */
const lastSentAt = new Map<string, number>()

function pruneExpired(now: number) {
  for (const [key, at] of lastSentAt) {
    if (now - at >= DEDUPE_MS) lastSentAt.delete(key)
  }
}

/**
 * Ghi nhận một lượt bấm CTA liên hệ. Không bao giờ throw, không bao giờ chặn.
 * Trả về `true` nếu beacon được bắn, `false` nếu bị bỏ qua (trùng / thiếu id / SSR).
 * Giá trị trả về chỉ để test — caller trong template không cần dùng.
 */
export function trackContactView(entityId: unknown, action: ContactAction): boolean {
  try {
    if (!import.meta.client) return false
    if (typeof fetch !== 'function') return false

    const id = String(entityId ?? '').trim()
    if (!id) return false

    const key = `${id}:${action}`
    const now = Date.now()
    const last = lastSentAt.get(key)
    if (last !== undefined && now - last < DEDUPE_MS) return false

    if (lastSentAt.size >= MAX_TRACKED_KEYS) pruneExpired(now)
    lastSentAt.set(key, now)

    const url = `/api/entities/${encodeURIComponent(id)}/view-contact?action=${encodeURIComponent(action)}`
    const pending = fetch(url, {
      method: 'POST',
      keepalive: true,
      credentials: 'omit',
    })
    // Nuốt lỗi mạng — không để unhandled rejection nổi lên console/Sentry.
    if (pending && typeof (pending as Promise<unknown>).catch === 'function') {
      void (pending as Promise<unknown>).catch(() => {})
    }
    return true
  } catch {
    // Đo hỏng thì thôi; điều hướng của người dùng vẫn phải chạy.
    return false
  }
}

/** Chỉ dùng trong test — xoá bộ nhớ chống-trùng giữa các case. */
export function resetContactBeaconDedupe() {
  lastSentAt.clear()
}

export function useContactBeacon() {
  return { trackContactView, resetContactBeaconDedupe }
}
