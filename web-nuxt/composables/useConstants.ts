export interface TypeMeta {
  emoji: string
  /** IconLine name — line-icon equivalent of `emoji` for template contexts. */
  icon: string
  label: string
  cat: string
}

export const TYPE_META: Record<string, TypeMeta> = {
  experience: { emoji: '🌾', icon: 'sprout', label: 'Trải nghiệm', cat: 'experience' },
  product: { emoji: '🍊', icon: 'fruit', label: 'Đặc sản & OCOP', cat: 'product' },
  dish: { emoji: '🍲', icon: 'bowl', label: 'Ẩm thực', cat: 'dish' },
  restaurant: { emoji: '🍽️', icon: 'bowl', label: 'Quán ăn', cat: 'dish' },
  cafe: { emoji: '☕', icon: 'coffee', label: 'Quán cà phê', cat: 'dish' },
  craft_village: { emoji: '🏺', icon: 'vase', label: 'Làng nghề', cat: 'craft' },
  attraction: { emoji: '🛕', icon: 'landmark', label: 'Tham quan', cat: 'attraction' },
  accommodation: { emoji: '🏡', icon: 'home', label: 'Lưu trú', cat: 'accommodation' },
  organization: { emoji: '🏢', icon: 'building', label: 'Cơ sở / HTX', cat: 'org' },
  place: { emoji: '📍', icon: 'pin', label: 'Xã/Phường', cat: 'place' },
  nature: { emoji: '🌿', icon: 'leaf', label: 'Thiên nhiên', cat: 'nature' },
  history: { emoji: '🏛️', icon: 'landmark', label: 'Lịch sử', cat: 'history' },
  event: { emoji: '🎉', icon: 'calendar', label: 'Sự kiện', cat: 'event' },
  economy: { emoji: '📊', icon: 'building', label: 'Kinh tế', cat: 'economy' },
  person: { emoji: '👤', icon: 'user', label: 'Nhân vật', cat: 'person' },
  drink: { emoji: '🥤', icon: 'cup', label: 'Đồ uống', cat: 'dish' },
  itinerary: { emoji: '🗺️', icon: 'map', label: 'Lịch trình', cat: 'itinerary' },
  facility: { emoji: '🏛️', icon: 'building', label: 'Cơ quan hành chính', cat: 'facility' },
}

export function getTypeMeta(type: string): TypeMeta {
  return TYPE_META[type] || { emoji: '📍', icon: 'pin', label: type, cat: 'place' }
}

// GĐ13.4: nhãn loại cơ quan công vụ (facility.attributes.office_kind) cho danh bạ hành chính.
export const OFFICE_KIND: Record<string, { emoji: string; icon: string; label: string }> = {
  ubnd: { emoji: '🏛️', icon: 'landmark', label: 'UBND xã/phường' },
  cong_an: { emoji: '👮', icon: 'user', label: 'Công an' },
  y_te: { emoji: '🏥', icon: 'building', label: 'Trạm y tế' },
  truong_hoc: { emoji: '🏫', icon: 'building', label: 'Trường học' },
  buu_dien: { emoji: '📮', icon: 'building', label: 'Bưu điện' },
  tu_phap: { emoji: '⚖️', icon: 'building', label: 'Tư pháp – Hộ tịch' },
  khac: { emoji: '🏢', icon: 'building', label: 'Cơ quan khác' },
}

export const AREA_META: Record<string, { name: string; emoji: string; icon: string; blurb: string }> = {
  'vinh-long': { name: 'Vĩnh Long', emoji: '🍊', icon: 'fruit', blurb: 'Miệt vườn cam sành, khoai lang, bưởi Năm Roi và làng gốm Mang Thít.' },
  'ben-tre': { name: 'Bến Tre', emoji: '🥥', icon: 'leaf', blurb: 'Xứ dừa: kẹo dừa, mật hoa dừa, bưởi da xanh và những rẫy dừa bạt ngàn.' },
  'tra-vinh': { name: 'Trà Vinh', emoji: '🛕', icon: 'landmark', blurb: 'Văn hóa Khmer: ao Bà Om, chùa cổ, dừa sáp Cầu Kè và bún nước lèo.' },
  'lien-vung': { name: 'Liên vùng', emoji: '🧭', icon: 'compass', blurb: 'Tuyến kết nối nhiều điểm đến giữa Vĩnh Long, Bến Tre và Trà Vinh.' },
}

// Interest landing pages (/kham-pha/<slug>). Overridable via metadata.interests.
export interface InterestDef {
  emoji: string
  icon: string
  label: string
  description: string
  types: string[]
  relatedRoutes?: string[]
}
export const INTEREST_META: Record<string, InterestDef> = {
  'am-thuc': { emoji: '🍲', icon: 'bowl', label: 'Ẩm thực', description: 'Món ngon bản địa — từ bún nước lèo, bánh xèo đến đặc sản trái cây theo mùa.', types: ['dish', 'product'], relatedRoutes: ['vong-am-thuc-mien-tay'] },
  'thien-nhien': { emoji: '🌿', icon: 'leaf', label: 'Thiên nhiên', description: 'Miệt vườn sông nước, cù lao xanh mát, vườn trái cây và đồng lúa bát ngàn.', types: ['experience', 'attraction'], relatedRoutes: ['vong-trai-cay-vinh-long', 'vong-mua-nuoc-noi'] },
  'van-hoa': { emoji: '🛕', icon: 'landmark', label: 'Văn hóa', description: 'Di tích lịch sử, chùa Khmer cổ, lễ hội truyền thống và đời sống bản địa.', types: ['attraction', 'craft_village'], relatedRoutes: ['vong-chua-khmer-tra-vinh'] },
  'lang-nghe': { emoji: '🏺', icon: 'vase', label: 'Làng nghề', description: 'Gốm Mang Thít, kẹo dừa, chiếu lác, bánh tráng — nghề truyền thống hàng trăm năm.', types: ['craft_village', 'organization'], relatedRoutes: ['vong-lang-nghe-mang-thit'] },
  'mua-sam': { emoji: '🛍️', icon: 'gift', label: 'Mua sắm & OCOP', description: 'Sản phẩm OCOP, đặc sản làm quà, trái cây tươi và hàng thủ công mỹ nghệ.', types: ['product'] },
}

export const CARD_TYPES = ['experience', 'product', 'dish', 'craft_village', 'attraction', 'accommodation', 'nature', 'history', 'event'] as const
export const TOURISM_TYPES = ['experience', 'attraction', 'accommodation', 'craft_village', 'dish', 'nature', 'history'] as const
export const PRODUCT_TYPES = ['product'] as const

export const REL_FWD: Record<string, string> = {
  hosts: 'Tổ chức', offered_by: 'Đặt qua', made_by: 'Sản xuất bởi',
  produced_in: 'Sản xuất tại', supplies_to: 'Cung ứng cho', near: 'Gần',
  related_to: 'Liên quan', associated_with: 'Gắn với', located_in: 'Nằm tại', part_of: 'Thuộc',
}
export const REL_BWD: Record<string, string> = {
  hosts: 'Diễn ra tại', offered_by: 'Cung cấp', made_by: 'Sản phẩm',
  produced_in: 'Đặc sản', supplies_to: 'Nguồn cung', near: 'Gần',
  related_to: 'Liên quan', associated_with: 'Gắn với', located_in: 'Bao gồm', part_of: 'Gồm',
}

export const FLOOD_MONTHS = [8, 9, 10, 11]

// ── A1: site_settings overrides ──────────────────────────────────────────
// TYPE_META / AREA_META / OFFICE_KIND are imported directly as module
// singletons across ~37 call sites (templates iterate them, computeds read
// them). To let admins override emoji/label from the CMS without touching
// every call site, we merge `categories.*` / `metadata.*` overrides IN PLACE
// into these shared objects once at app init (see plugins/site-overrides.ts).
// Pristine snapshots let re-applying be idempotent (restore base, then merge)
// so a removed override reverts to the default on the next app load.
const _TYPE_BASE = JSON.parse(JSON.stringify(TYPE_META)) as typeof TYPE_META
const _AREA_BASE = JSON.parse(JSON.stringify(AREA_META)) as typeof AREA_META
const _OFFICE_BASE = JSON.parse(JSON.stringify(OFFICE_KIND)) as typeof OFFICE_KIND
const _INTEREST_BASE = JSON.parse(JSON.stringify(INTEREST_META)) as typeof INTEREST_META

function mergeInto(
  target: Record<string, any>,
  base: Record<string, any>,
  overrides: unknown,
) {
  // Restore known keys to their pristine default first (idempotent re-apply).
  for (const k of Object.keys(base)) {
    if (target[k]) Object.assign(target[k], base[k])
    else target[k] = { ...base[k] }
  }
  // Apply admin overrides on top (partial — only the fields provided).
  if (overrides && typeof overrides === 'object') {
    for (const [k, ov] of Object.entries(overrides as Record<string, any>)) {
      if (ov == null || typeof ov !== 'object') continue
      if (k === '__proto__' || k === 'constructor' || k === 'prototype') continue
      if (target[k]) Object.assign(target[k], ov)
      else target[k] = { ...ov }
    }
  }
}

/**
 * Merge CMS overrides into the shared metadata maps. Safe to call repeatedly;
 * each call resets to defaults then re-applies, so it never accumulates stale
 * keys for entries that still exist in the base maps.
 */
export function applySiteOverrides(opts: {
  typeOverrides?: unknown
  areaOverrides?: unknown
  officeKind?: unknown
  interests?: unknown
}) {
  mergeInto(TYPE_META, _TYPE_BASE, opts.typeOverrides)
  mergeInto(AREA_META, _AREA_BASE, opts.areaOverrides)
  mergeInto(OFFICE_KIND, _OFFICE_BASE, opts.officeKind)
  mergeInto(INTEREST_META, _INTEREST_BASE, opts.interests)
}

export function useConstants() {
  return { TYPE_META, AREA_META, OFFICE_KIND, INTEREST_META, CARD_TYPES, TOURISM_TYPES, PRODUCT_TYPES, REL_FWD, REL_BWD, FLOOD_MONTHS }
}
