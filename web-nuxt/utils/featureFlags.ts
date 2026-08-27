// A4 — feature flag registry.
// Single source of the toggleable modules. The CMS stores overrides under the
// single key `features.flags` (a JSON object of {flagKey: boolean}). useFeature()
// resolves: explicit override → registry default → false. Flags only HIDE
// existing sections (never enable commerce — §1.4). Every flag here must gate a
// real section so the admin toggle grid stays honest.

export interface FeatureFlag {
  key: string
  label: string
  description?: string
  default: boolean
  group?: string
}

export const FEATURE_FLAGS: FeatureFlag[] = [
  { key: 'chat_widget', label: 'Bong bóng chat AI', description: 'Nút chat AI nổi ở góc màn hình', default: true, group: 'AI' },
  { key: 'ai_recommendations', label: 'Gợi ý liên quan (AI)', description: 'Khối "Có thể bạn quan tâm" trên trang chủ, chi tiết, tìm kiếm', default: true, group: 'AI' },
  { key: 'ai_tips', label: 'Mẹo trải nghiệm (AI)', description: 'Mẹo du lịch AI ở trang chi tiết địa điểm', default: true, group: 'AI' },
  { key: 'ai_best_time', label: 'Thời điểm lý tưởng (AI)', description: 'Gợi ý thời điểm ghé thăm ở trang chi tiết', default: true, group: 'AI' },
  { key: 'reviews', label: 'Đánh giá địa điểm', description: 'Khối đánh giá của người dùng ở trang chi tiết', default: true, group: 'Cộng đồng' },
  { key: 'nearby', label: 'Địa điểm lân cận', description: 'Khối gợi ý địa điểm gần đó ở trang chi tiết', default: true, group: 'Khám phá' },
  { key: 'onboarding', label: 'Hướng dẫn lần đầu', description: 'Bảng chào mừng hiện cho khách lần đầu truy cập', default: true, group: 'Khám phá' },
  // default:false CÓ CHỦ ĐÍCH — mục mới phải được bật TAY từ AdminCP. Cờ chưa
  // nằm trong ESTABLISHED nên resolveFeatureFlag bỏ qua `default` và trả false
  // cho tới khi có override; đó là đường lùi 10 giây không cần deploy, quan
  // trọng vì máy chủ KHÔNG giữ bản N-1 (installer xoá hẳn bản cũ).
  { key: 'home_product_lead', label: 'Tin chính đặc sản', description: 'Mục điểm dừng đặc sản trên trang chủ (một sản phẩm dựng lớn theo tháng)', default: false, group: 'Khám phá' },
  { key: 'preference_ui_v1', label: 'Thiết lập khu vực & sở thích', description: 'Lớp thiết lập cá nhân hóa NP-1 trong onboarding và cài đặt', default: false, group: 'Cá nhân hóa' },
  { key: 'recommendation_explanations_v1', label: 'Giải thích đề xuất', description: 'Nút Vì sao gợi ý này và ngăn điều khiển đề xuất', default: false, group: 'Cá nhân hóa' },
  { key: 'trust_drawer_v1', label: 'Ngăn nguồn & độ tin cậy', description: 'Disclosure nguồn dữ liệu ở trang chi tiết địa điểm', default: false, group: 'Tin cậy' },
  { key: 'public_personalization_v1', label: 'Cá nhân hóa công khai', description: 'Điều chỉnh thứ tự và CTA theo tín hiệu đã đồng ý', default: false, group: 'Rollout công khai' },
  { key: 'public_recommendation_v1', label: 'Đề xuất theo ngữ cảnh', description: 'Đề xuất thích ứng; tắt cờ vẫn giữ danh sách xác định', default: false, group: 'Rollout công khai' },
  { key: 'public_search_expansion_v1', label: 'Mở rộng tìm kiếm', description: 'Mở rộng truy vấn khi có đủ tín hiệu an toàn', default: false, group: 'Rollout công khai' },
  { key: 'public_optimizer_v1', label: 'Tối ưu lịch trình', description: 'Tối ưu nâng cao; tắt cờ giữ trình lập lịch cơ bản', default: false, group: 'Rollout công khai' },
  { key: 'public_proactive_notices_v1', label: 'Thông báo chủ động', description: 'Thông báo theo ngữ cảnh không chặn tác vụ chính', default: false, group: 'Rollout công khai' },
]

export const PUBLIC_CAPABILITY_FLAGS = Object.freeze({
  personalization: 'public_personalization_v1',
  recommendation: 'public_recommendation_v1',
  searchExpansion: 'public_search_expansion_v1',
  optimizer: 'public_optimizer_v1',
  proactiveNotices: 'public_proactive_notices_v1',
} as const)

export type PublicCapability = keyof typeof PUBLIC_CAPABILITY_FLAGS
export type PublicCapabilityMode = 'enhanced' | 'deterministic'

const ESTABLISHED_FEATURE_FLAGS = Object.freeze(new Set([
  'chat_widget',
  'ai_recommendations',
  'ai_tips',
  'ai_best_time',
  'reviews',
  'nearby',
  'onboarding',
]))

const LEGACY_PUBLIC_CAPABILITY: Partial<Record<string, PublicCapability>> = Object.freeze({
  preference_ui_v1: 'personalization',
  recommendation_explanations_v1: 'personalization',
})

export function isEstablishedFeatureFlag(key: string): boolean {
  return ESTABLISHED_FEATURE_FLAGS.has(key)
}

export function featureFlagDefault(key: string): boolean {
  return FEATURE_FLAGS.find(f => f.key === key)?.default ?? false
}

export function resolveFeatureFlag(key: string, flags: Record<string, unknown> | null | undefined): boolean {
  const definition = FEATURE_FLAGS.find(flag => flag.key === key)
  if (!definition) return false

  const safeFlags = flags && typeof flags === 'object' && !Array.isArray(flags) ? flags : null
  const override = safeFlags?.[key]
  const enabled = typeof override === 'boolean'
    ? override
    : isEstablishedFeatureFlag(key) ? definition.default : false
  const capability = LEGACY_PUBLIC_CAPABILITY[key]
  if (!capability || !enabled) return enabled
  return safeFlags?.[PUBLIC_CAPABILITY_FLAGS[capability]] === true
}

export function resolvePublicCapabilityMode(capability: PublicCapability, flags: Record<string, unknown> | null | undefined): PublicCapabilityMode {
  return resolveFeatureFlag(PUBLIC_CAPABILITY_FLAGS[capability], flags) ? 'enhanced' : 'deterministic'
}
