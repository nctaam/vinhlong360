// GĐ-A entity split per-kind — FE config cho các trang quản lý theo nhóm.
// Nguồn sự thật type→kind là agent/entity_schemas.py (KIND_OF_TYPE); file này
// khai báo phần FE cần: cột đặc thù, chip lọc, thứ tự hiển thị. Spec:
// docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md

export interface KindColumn {
  key: string
  label: string
  widget: 'text' | 'number' | 'select' | 'bool'
  options?: string[]
  width?: string
}

export interface KindChip {
  key: string
  label: string
  test: (e: Record<string, any>) => boolean
}

export interface KindDef {
  kind: string        // giá trị kind backend (KIND_OF_TYPE)
  slug: string        // nhãn URL thân thiện (dự phòng)
  label: string
  emoji: string
  types: string[]     // types thành viên — khớp KIND_OF_TYPE backend
  columns: KindColumn[]
  chips: KindChip[]
}

const attr = (e: Record<string, any>, k: string) => (e?.attributes || {})[k]
const noAttr = (k: string) => (e: Record<string, any>) => {
  const v = attr(e, k)
  return v === undefined || v === null || v === '' || (Array.isArray(v) && !v.length)
}
const noSeason = (e: Record<string, any>) => !(e?.season?.months?.length || e?.season?.best)

const HERITAGE_LEVELS = ['Di tích quốc gia đặc biệt', 'Di tích quốc gia', 'Di tích cấp tỉnh', 'Chưa xếp hạng']
const ACCOM_TYPES = ['Khách sạn', 'Homestay', 'Nhà nghỉ', 'Resort', 'Nhà vườn', 'Khác']
// SP6 2026-07-07: +4 mục facility ngoài-cơ-quan — khớp agent/entity_schemas.py OFFICE_KINDS
const OFFICE_KINDS = ['ubnd', 'cong_an', 'y_te', 'truong_hoc', 'buu_dien', 'tu_phap', 'giao_thong', 'ngan_hang', 'vien_thong', 'cua_hang', 'khac']

export const ADMIN_KINDS: KindDef[] = [
  {
    kind: 'place', slug: 'dia-diem', label: 'Địa điểm', emoji: '🛕',
    types: ['attraction', 'nature', 'history'],
    columns: [
      { key: 'sub_category', label: 'Phân loại', widget: 'text' },
      { key: 'admission', label: 'Vé vào', widget: 'text' },
      { key: 'heritage_level', label: 'Xếp hạng DT', widget: 'select', options: HERITAGE_LEVELS },
    ],
    chips: [
      { key: 'di-tich-qg', label: '🏛️ Di tích quốc gia', test: e => String(attr(e, 'heritage_level') || '').includes('quốc gia') },
      { key: 'thieu-dia-chi', label: 'Thiếu địa chỉ', test: noAttr('address') },
      { key: 'thieu-mua', label: 'Thiếu mùa', test: noSeason },
    ],
  },
  {
    kind: 'experience', slug: 'trai-nghiem', label: 'Trải nghiệm', emoji: '🌾',
    types: ['experience'],
    columns: [
      { key: 'duration', label: 'Thời lượng', widget: 'text' },
      { key: 'operator', label: 'Đơn vị tổ chức', widget: 'text' },
      { key: 'price_range', label: 'Giá', widget: 'text' },
    ],
    chips: [
      { key: 'thieu-gia', label: 'Thiếu giá', test: noAttr('price_range') },
      { key: 'thieu-dia-chi', label: 'Thiếu địa chỉ', test: noAttr('address') },
    ],
  },
  {
    kind: 'product', slug: 'san-pham', label: 'Sản phẩm & OCOP', emoji: '🍊',
    types: ['product', 'craft_village'],
    columns: [
      { key: 'ocop_star', label: 'Sao OCOP', widget: 'select', options: ['1', '2', '3', '4', '5'] },
      { key: 'producer', label: 'Nhà sản xuất', widget: 'text' },
      { key: 'price_range', label: 'Giá', widget: 'text' },
    ],
    chips: [
      { key: 'ocop-4-5', label: '⭐ OCOP 4–5 sao', test: e => Number(attr(e, 'ocop_star') || 0) >= 4 },
      { key: 'thieu-producer', label: 'Thiếu nhà SX', test: noAttr('producer') },
      { key: 'thieu-gia', label: 'Thiếu giá', test: noAttr('price_range') },
    ],
  },
  {
    kind: 'food', slug: 'am-thuc', label: 'Ẩm thực & Ăn uống', emoji: '🍲',
    types: ['dish', 'drink', 'restaurant', 'cafe'],
    columns: [
      { key: 'price_range', label: 'Giá', widget: 'text' },
      { key: 'rating', label: 'Điểm', widget: 'number' },
      { key: 'specialty', label: 'Đặc trưng', widget: 'text' },
    ],
    chips: [
      { key: 'co-rating', label: '⭐ Có đánh giá', test: e => Number(attr(e, 'rating') || 0) > 0 },
      { key: 'thieu-gia', label: 'Thiếu giá', test: noAttr('price_range') },
      { key: 'thieu-dia-chi', label: 'Thiếu địa chỉ', test: noAttr('address') },
    ],
  },
  {
    kind: 'lodging', slug: 'luu-tru', label: 'Lưu trú', emoji: '🏡',
    types: ['accommodation'],
    columns: [
      { key: 'accommodation_type', label: 'Loại hình', widget: 'select', options: ACCOM_TYPES },
      { key: 'rooms', label: 'Số phòng', widget: 'number' },
      { key: 'price_range', label: 'Giá', widget: 'text' },
    ],
    chips: [
      { key: 'thieu-rooms', label: 'Thiếu số phòng', test: noAttr('rooms') },
      { key: 'thieu-sdt', label: 'Thiếu SĐT', test: noAttr('phone') },
    ],
  },
  {
    kind: 'event', slug: 'su-kien', label: 'Sự kiện & Lễ hội', emoji: '🎉',
    types: ['event'],
    columns: [
      { key: 'date_start', label: 'Bắt đầu', widget: 'text' },
      { key: 'venue', label: 'Địa điểm', widget: 'text' },
      { key: 'organizer', label: 'BTC', widget: 'text' },
    ],
    chips: [
      { key: 'le-hoi-am-lich', label: '🌙 Lễ hội âm lịch', test: e => !!attr(e, 'lunar_date') },
      { key: 'thieu-ngay', label: 'Thiếu ngày', test: e => !attr(e, 'date_start') && !attr(e, 'lunar_date') },
    ],
  },
  {
    kind: 'facility', slug: 'co-quan', label: 'Cơ quan & Tiện ích', emoji: '🏛️',
    types: ['facility'],
    columns: [
      { key: 'office_kind', label: 'Loại cơ quan', widget: 'select', options: OFFICE_KINDS },
      { key: 'phone', label: 'Điện thoại', widget: 'text' },
      { key: 'hours', label: 'Giờ làm việc', widget: 'text' },
    ],
    chips: [
      { key: 'thieu-sdt', label: 'Thiếu SĐT', test: noAttr('phone') },
      { key: 'thieu-gio', label: 'Thiếu giờ', test: noAttr('hours') },
    ],
  },
  {
    kind: 'person', slug: 'nhan-vat', label: 'Nhân vật', emoji: '👤',
    types: ['person'],
    columns: [
      { key: 'role', label: 'Vai trò', widget: 'text' },
      { key: 'birth_year', label: 'Năm sinh', widget: 'number' },
      { key: 'hometown', label: 'Quê quán', widget: 'text' },
    ],
    chips: [
      { key: 'thieu-role', label: 'Thiếu vai trò', test: noAttr('role') },
    ],
  },
  {
    kind: 'admin_place', slug: 'xa-phuong', label: 'Xã/Phường', emoji: '📍',
    types: ['place'],
    columns: [
      { key: 'former_district', label: 'Huyện cũ', widget: 'text' },
      { key: 'population', label: 'Dân số', widget: 'number' },
      { key: 'effective_date', label: 'Hiệu lực', widget: 'text' },
    ],
    chips: [
      { key: 'thieu-danso', label: 'Thiếu dân số', test: noAttr('population') },
    ],
  },
]

export function kindBySlug(slug: string): KindDef | undefined {
  return ADMIN_KINDS.find(k => k.slug === slug)
}

export function kindByKey(kind: string): KindDef | undefined {
  return ADMIN_KINDS.find(k => k.kind === kind)
}
