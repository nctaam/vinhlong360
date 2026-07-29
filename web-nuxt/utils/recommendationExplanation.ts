import type { RecommendationExplanation } from '~/types/api'

export interface SafeRecommendationExplanation {
  reasons: string[]
  regionLabel: string
  interestLabels: string[]
}

const DEFAULT_REASON = 'Được cộng đồng quan tâm'

function foldText(value: string) {
  return value
    .trim()
    .toLocaleLowerCase('vi-VN')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/\s+/g, ' ')
}

const SAFE_REASON_MAP: Record<string, string> = {
  'hop voi nhom noi dung ban quan tam': 'Hợp với nhóm nội dung bạn quan tâm',
  'hop voi noi dung ban quan tam': 'Hợp với nội dung bạn quan tâm',
  'phu hop voi so thich ban da chon': 'Phù hợp với sở thích bạn đã chọn',
  'cung khu vuc ban hay xem': 'Cùng khu vực bạn quan tâm',
  'cung khu vuc ban quan tam': 'Cùng khu vực bạn quan tâm',
  'cung khu vuc ban chon': 'Cùng khu vực bạn quan tâm',
  'cung chu de voi noi dang xem': 'Cùng chủ đề với nơi đang xem',
  'gan mach kham pha hien tai': 'Gần mạch khám phá hiện tại',
  'lien quan truc tiep toi tim kiem': 'Liên quan tới tìm kiếm hiện tại',
  'lien quan toi tim kiem hien tai': 'Liên quan tới tìm kiếm hiện tại',
  'duoc cong dong quan tam': DEFAULT_REASON,
  'lien quan trong ban do tri thuc': 'Liên quan trong bản đồ tri thức',
  'gan nhau trong cung xa phuong': 'Gần nhau trong cùng xã phường',
  'cung khu vuc kham pha': 'Cùng khu vực khám phá',
  'co chu de trai nghiem gan nhau': 'Có chủ đề trải nghiệm gần nhau',
  'cung nhom noi dung': 'Cùng nhóm nội dung',
  'phu hop de kham pha tiep': 'Phù hợp để khám phá tiếp',
}

const INTEREST_LABELS: Record<string, string> = {
  food: 'Ẩm thực',
  'am thuc': 'Ẩm thực',
  local_products: 'Đặc sản & OCOP',
  'dac san & ocop': 'Đặc sản & OCOP',
  'dac san va ocop': 'Đặc sản & OCOP',
  garden: 'Miệt vườn',
  'miet vuon': 'Miệt vườn',
  culture: 'Văn hóa',
  'van hoa': 'Văn hóa',
  craft: 'Làng nghề',
  'lang nghe': 'Làng nghề',
  stay: 'Lưu trú',
  'luu tru': 'Lưu trú',
}

function safeReason(value: unknown, hasExplicitInterests: boolean) {
  if (typeof value !== 'string') return ''
  const folded = foldText(value)
  if (folded.startsWith('khop so thich ')) {
    return hasExplicitInterests ? 'Phù hợp với sở thích bạn đã chọn' : 'Hợp với nội dung bạn quan tâm'
  }
  return SAFE_REASON_MAP[folded] || ''
}

function safeRegionLabel(value: unknown) {
  if (typeof value !== 'string') return ''
  const normalized = value.trim()
  if (!normalized || normalized.length > 100) return ''
  const folded = foldText(normalized)
  if (/\b(gps|ip|toa do|latitude|longitude|lat|lng|truy van|tim kiem)\b/.test(folded)) return ''
  if (/(?:\d{1,3}\.){3}\d{1,3}/.test(normalized)) return ''
  if (/(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9]{0,4}/.test(normalized)) return ''
  if (/[+-]?(?:\d+\.\d+|\.\d+)\s*[,;/]\s*[+-]?(?:\d+\.\d+|\.\d+)/.test(normalized)) return ''
  if (/\d{1,3}\s*[°º]/.test(normalized)) return ''
  if (/(?:^|\s)[+-]?(?:\d+\.\d+|\.\d+)(?:\s|$)/.test(normalized)) return ''
  return normalized
}

function safeInterestLabels(value: unknown) {
  if (!Array.isArray(value)) return []
  const labels = value.flatMap((item) => {
    if (typeof item !== 'string') return []
    const label = INTEREST_LABELS[foldText(item)]
    return label ? [label] : []
  })
  return [...new Set(labels)].slice(0, 3)
}

export function projectRecommendationExplanation(
  explanation?: Partial<RecommendationExplanation> | null,
): SafeRecommendationExplanation {
  const interestLabels = safeInterestLabels(explanation?.explicit_interests)
  const candidates = [
    explanation?.primary_reason,
    ...(Array.isArray(explanation?.reasons) ? explanation.reasons : []),
  ]
  const reasons = [...new Set(
    candidates.map(value => safeReason(value, interestLabels.length > 0)).filter(Boolean),
  )].slice(0, 3)
  return {
    reasons: reasons.length ? reasons : [DEFAULT_REASON],
    regionLabel: safeRegionLabel(explanation?.region_label),
    interestLabels,
  }
}
