import { SITE_URL } from '../composables/useSeoHelpers'
import { encodePathId } from './routePaths'

/**
 * Đơn vị hành chính cấp xã/phường cho breadcrumb + structured data (§1.6 CLAUDE.md).
 *
 * Từ 1/7/2025 tỉnh Vĩnh Long mới chạy hành chính 2 CẤP: tỉnh → 124 xã/phường
 * (35 phường + 89 xã). KHÔNG còn cấp huyện, và hai tỉnh đã sáp nhập vào cũng
 * không còn là đơn vị hành chính.
 * Trường `area` (`ben-tre` / `tra-vinh` / `vinh-long`) là VÙNG CŨ — chỉ để tra
 * cứu/lọc dữ liệu — nên nó không được đứng trong breadcrumb như một cấp hành chính.
 * Mắt xích giữa phải lấy theo `entity.placeId` → entity `type=place`.
 *
 * Phân biệt phường/xã lấy từ đâu: entity place có field `level`
 * ('phuong' | 'xa' | 'tinh') VÀ `name` đã mang sẵn tiền tố ('Phường …' / 'Xã …' /
 * 'Tỉnh …'). Đối chiếu web/data.json (2026-08-07): 125 place, `level` khớp tiền tố
 * tên 125/125 (35 phuong + 89 xa + 1 tinh) — không có ca lệch. API công khai
 * (`_enrich_entity_place`, agent/public_api.py:1014) chỉ trả `place_name`, KHÔNG
 * trả `level`, nên mặc định suy tiền tố từ tên; tham số `level` là đường mở sẵn
 * (additive-first) cho ngày backend gửi kèm.
 */

export const PROVINCE_LABEL = 'Vĩnh Long'

export type AdminUnitLevel = 'phuong' | 'xa' | 'tinh' | string | null | undefined

export interface AdminUnitCrumb {
  /** Nhãn hiển thị, ví dụ 'P. An Hội' / 'Xã Long Hòa'. Không bao giờ rỗng. */
  label: string
  /** Đường dẫn tới trang xã/phường; rỗng khi không có placeId → render text thường. */
  to: string
}

interface AdminUnitCarrier {
  id?: string | null
  type?: string | null
  placeId?: string | null
  place_name?: string | null
  place_level?: AdminUnitLevel
}

const PREFIX_PATTERN = /^(Phường|Xã|Tỉnh)\s+(.+)$/i
const PREFIX_LEVEL: Readonly<Record<string, 'phuong' | 'xa' | 'tinh'>> = Object.freeze({
  'phường': 'phuong',
  'xã': 'xa',
  'tỉnh': 'tinh',
})

/**
 * 'Phường An Hội' → 'P. An Hội'; 'Xã Long Hòa' → 'Xã Long Hòa';
 * 'Tỉnh Vĩnh Long' → 'Vĩnh Long'. Tên không nhận diện được → giữ nguyên văn
 * (không bao giờ trả 'undefined' hay chuỗi rỗng cho một tên có thật).
 */
export function adminUnitLabel(placeName?: string | null, level?: AdminUnitLevel): string {
  const raw = String(placeName ?? '').replace(/\s+/g, ' ').trim()
  if (!raw) return ''

  const matched = raw.match(PREFIX_PATTERN)
  const bare = matched?.[2]?.trim() || raw
  const inferred = matched ? PREFIX_LEVEL[(matched[1] || '').toLowerCase()] : undefined
  const resolved = String(level ?? '').trim() || inferred

  if (resolved === 'phuong') return `P. ${bare}`
  if (resolved === 'xa') return `Xã ${bare}`
  if (resolved === 'tinh') return bare
  return raw
}

/**
 * Mắt xích hành chính của một entity nội dung.
 *
 * Fallback (bắt buộc): thiếu `placeId`, hoặc `placeId` trỏ tới id không tồn tại
 * (backend không gắn được `place_name`) → trả `null` = BỎ HẲN mắt xích, thay vì
 * bịa một địa bàn. Có `place_name` mà thiếu `placeId` → giữ nhãn, bỏ liên kết.
 *
 * Chính entity `type=place` → null: nó ĐÃ LÀ đơn vị hành chính, mắt xích cuối là
 * tên nó, phía trên chỉ còn cấp tỉnh. Guard này bắt buộc vì `placeId` của nhiều
 * entity place trong dữ liệu đang trỏ sang đơn vị khác (đo 2026-08-07 trên
 * web/data.json: 39/125 place có `placeId` ≠ id — 37 trỏ sang place khác, 32 trong
 * số đó trỏ nhầm `p-long-chau`; 2 bỏ trống)
 * — không có guard thì trang "Xã An Bình" sẽ đội mắt xích "P. Long Châu".
 */
export function adminUnitCrumb(entity?: AdminUnitCarrier | null): AdminUnitCrumb | null {
  if (String(entity?.type ?? '').trim() === 'place') return null
  const label = adminUnitLabel(entity?.place_name, entity?.place_level)
  if (!label) return null
  const placeId = String(entity?.placeId ?? '').trim()
  const selfId = String(entity?.id ?? '').trim()
  if (placeId && selfId && placeId === selfId) return null
  return { label, to: placeId ? `/xa-phuong/${encodePathId(placeId)}` : '' }
}

/**
 * Mắt xích "địa bàn" thay-thế-được: vùng cũ `/khu-vuc/<area>` hoặc một xã/phường
 * cụ thể `/xa-phuong/<id>`. Catalog `/xa-phuong` (không có id) là mắt xích CHUYÊN MỤC
 * của entity type=place — không đụng tới.
 */
function isReplaceableLocationTier(item: unknown): boolean {
  const url = (item as { item?: unknown })?.item
  if (typeof url !== 'string') return false
  return url.includes('/khu-vuc/') || url.includes('/xa-phuong/')
}

function rewriteBreadcrumbList(node: Record<string, unknown>, crumb: AdminUnitCrumb | null) {
  const items = Array.isArray(node.itemListElement) ? [...node.itemListElement] : []
  if (!items.length) return node

  const kept = items.filter(item => !isReplaceableLocationTier(item))
  if (crumb) {
    const crumbItem: Record<string, unknown> = { '@type': 'ListItem', name: crumb.label }
    if (crumb.to) crumbItem.item = `${SITE_URL}${crumb.to}`
    // Chèn ngay trước mắt xích cuối (chính entity) để giữ đúng thứ tự
    // Trang chủ → Chuyên mục → Xã/Phường → Entity.
    const at = Math.max(kept.length - 1, 0)
    kept.splice(at, 0, crumbItem)
  }

  return {
    ...node,
    itemListElement: kept.map((item, index) => ({
      ...(item as Record<string, unknown>),
      position: index + 1,
    })),
  }
}

function rewriteNode(node: unknown, crumb: AdminUnitCrumb | null): unknown {
  if (Array.isArray(node)) return node.map(child => rewriteNode(child, crumb))
  if (!node || typeof node !== 'object') return node

  const source = node as Record<string, unknown>
  let next: Record<string, unknown> = source

  if (source['@type'] === 'BreadcrumbList') {
    next = rewriteBreadcrumbList(next, crumb) as Record<string, unknown>
  }
  if (Array.isArray(next['@graph'])) {
    next = { ...next, '@graph': next['@graph'].map(child => rewriteNode(child, crumb)) }
  }
  if (next.breadcrumb && typeof next.breadcrumb === 'object') {
    next = { ...next, breadcrumb: rewriteNode(next.breadcrumb, crumb) }
  }
  return next
}

/**
 * Đồng bộ JSON-LD BreadcrumbList với breadcrumb hiển thị.
 *
 * `/seo/jsonld/{id}` (agent/seo.py:519 `_build_breadcrumb`) vẫn phát mắt xích
 * `area` cũ (`/khu-vuc/...`) và payload backend được ưu tiên hơn fallback của
 * trang, nên nếu không chuẩn hoá ở đây thì HTML nói 'P. An Hội' còn
 * structured-data nói 'Bến Tre' → lệch. Hàm này thay mắt xích `/khu-vuc/` bằng
 * mắt xích xã/phường (hoặc bỏ hẳn khi không xác định được) rồi đánh số lại
 * `position`. Idempotent: chạy trên payload đã đúng vẫn ra kết quả như cũ.
 */
export function withAdminUnitBreadcrumb<T>(payload: T, crumb: AdminUnitCrumb | null): T {
  return rewriteNode(payload, crumb) as T
}
