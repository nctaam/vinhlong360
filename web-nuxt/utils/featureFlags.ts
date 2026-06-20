// A4 — feature flag registry.
// Single source of the toggleable modules. The CMS stores overrides under the
// single key `features.flags` (a JSON object of {flagKey: boolean}). useFeature()
// resolves: explicit override → registry default → true. Flags only HIDE
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
]

export function featureFlagDefault(key: string): boolean {
  return FEATURE_FLAGS.find(f => f.key === key)?.default ?? true
}
