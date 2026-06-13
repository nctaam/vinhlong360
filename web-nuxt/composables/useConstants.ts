export interface TypeMeta {
  emoji: string
  label: string
  cat: string
}

export const TYPE_META: Record<string, TypeMeta> = {
  experience: { emoji: '🌾', label: 'Trải nghiệm', cat: 'experience' },
  product: { emoji: '🍊', label: 'Đặc sản & OCOP', cat: 'product' },
  dish: { emoji: '🍲', label: 'Ẩm thực', cat: 'dish' },
  craft_village: { emoji: '🏺', label: 'Làng nghề', cat: 'craft' },
  attraction: { emoji: '🛕', label: 'Tham quan', cat: 'attraction' },
  accommodation: { emoji: '🏡', label: 'Lưu trú', cat: 'accommodation' },
  organization: { emoji: '🏢', label: 'Cơ sở / HTX', cat: 'org' },
  place: { emoji: '📍', label: 'Xã/Phường', cat: 'place' },
  nature: { emoji: '🌿', label: 'Thiên nhiên', cat: 'nature' },
  history: { emoji: '🏛️', label: 'Lịch sử', cat: 'history' },
  event: { emoji: '🎉', label: 'Sự kiện', cat: 'event' },
  economy: { emoji: '📊', label: 'Kinh tế', cat: 'economy' },
  person: { emoji: '👤', label: 'Nhân vật', cat: 'person' },
}

export const AREA_META: Record<string, { name: string; emoji: string; blurb: string }> = {
  'vinh-long': { name: 'Vĩnh Long', emoji: '🍊', blurb: 'Miệt vườn cam sành, khoai lang, bưởi Năm Roi và làng gốm Mang Thít.' },
  'ben-tre': { name: 'Bến Tre', emoji: '🥥', blurb: 'Xứ dừa: kẹo dừa, mật hoa dừa, bưởi da xanh và những rẫy dừa bạt ngàn.' },
  'tra-vinh': { name: 'Trà Vinh', emoji: '🛕', blurb: 'Văn hóa Khmer: ao Bà Om, chùa cổ, dừa sáp Cầu Kè và bún nước lèo.' },
}

export const CARD_TYPES = ['experience', 'product', 'dish', 'craft_village', 'attraction', 'accommodation', 'nature', 'history', 'event'] as const
export const TOURISM_TYPES = ['experience', 'attraction', 'accommodation', 'craft_village', 'dish', 'nature', 'history'] as const
export const PRODUCT_TYPES = ['product'] as const

export const REL_FWD: Record<string, string> = {
  hosts: 'Tổ chức', offered_by: 'Đặt qua', made_by: 'Sản xuất bởi',
  produced_in: 'Sản xuất tại', supplies_to: 'Cung ứng cho', near: 'Gần',
}
export const REL_BWD: Record<string, string> = {
  hosts: 'Diễn ra tại', offered_by: 'Cung cấp', made_by: 'Sản phẩm',
  produced_in: 'Đặc sản', supplies_to: 'Nguồn cung', near: 'Gần',
}

export const FLOOD_MONTHS = [8, 9, 10, 11]

export function useConstants() {
  return { TYPE_META, AREA_META, CARD_TYPES, TOURISM_TYPES, PRODUCT_TYPES, REL_FWD, REL_BWD, FLOOD_MONTHS }
}
