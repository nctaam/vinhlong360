// B7 — default content for the first-visit onboarding sheet (OnboardingSheet.vue).
// Editable via the CMS key `onboarding`; component merges override-over-default.

export interface OnboardingFeature { icon: string; title: string; desc: string }
export interface OnboardingContent {
  emoji: string
  title: string
  intro: string
  features: OnboardingFeature[]
  cta_primary_label: string
  cta_primary_to: string
  cta_secondary_label: string
}

const LEGACY_ONBOARDING_ICON_MAP: Record<string, string> = {
  '🌴': 'leaf',
  '🗺️': 'map',
  '🗺': 'map',
  '📅': 'calendar',
  '💬': 'message',
  '✨': 'sparkle',
  '🍊': 'leaf',
  '🧭': 'compass',
  '📍': 'pin',
}

const VALID_ONBOARDING_ICONS = new Set([
  'leaf', 'map', 'calendar', 'message', 'sparkle', 'compass', 'pin',
  'star', 'book', 'award', 'building', 'camera', 'check', 'clock',
  'globe', 'heart', 'home', 'info', 'layers', 'route', 'search',
  'shield', 'sun', 'tag', 'user', 'users', 'utensils',
])

export function resolveOnboardingIcon(raw: string | undefined, fallback = 'sparkle'): string {
  const trimmed = (raw || '').trim()
  if (!trimmed) return fallback
  if (VALID_ONBOARDING_ICONS.has(trimmed)) return trimmed
  return LEGACY_ONBOARDING_ICON_MAP[trimmed] || fallback
}

export const DEFAULT_ONBOARDING: OnboardingContent = {
  emoji: 'leaf',
  title: 'Chào mừng đến vinhlong360',
  intro: 'Khám phá tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025) — theo cách của người bản địa.',
  features: [
    { icon: 'map', title: '1.400+ địa điểm & đặc sản', desc: 'Trải nghiệm miệt vườn, làng nghề, món ngon — cập nhật liên tục từ cộng đồng.' },
    { icon: 'calendar', title: 'Lịch trình gợi ý theo mùa', desc: 'Lộ trình chi tiết với bản đồ, đặc sản mùa nào, lễ hội sắp diễn ra.' },
    { icon: 'message', title: 'Hỏi đáp AI bản địa', desc: 'Chat trực tiếp để lên kế hoạch — nhanh hơn tìm kiếm thủ công.' },
  ],
  cta_primary_label: 'Khám phá ngay',
  cta_primary_to: '/du-lich',
  cta_secondary_label: 'Để sau',
}

export function mergeOnboarding(override: unknown): OnboardingContent {
  const o = (override && typeof override === 'object' && !Array.isArray(override))
    ? override as Partial<OnboardingContent>
    : {}
  const d = DEFAULT_ONBOARDING
  return {
    emoji: o.emoji || d.emoji,
    title: o.title || d.title,
    intro: o.intro || d.intro,
    features: Array.isArray(o.features) && o.features.length ? o.features : d.features,
    cta_primary_label: o.cta_primary_label || d.cta_primary_label,
    cta_primary_to: o.cta_primary_to || d.cta_primary_to,
    cta_secondary_label: o.cta_secondary_label || d.cta_secondary_label,
  }
}
