import type { RecommendationExplanation } from '~/types/api'

export interface SafeRecommendationExplanation {
  reasons: string[]
  regionLabel: string
  interestLabels: string[]
}

const DEFAULT_REASON = 'Được cộng đồng quan tâm'
const EXPLICIT_INTEREST_REASON = 'Phù hợp với sở thích bạn đã chọn'

const RE_COMBINING_MARKS = /[\u0300-\u036f]/g
const RE_LETTER_D = /đ/g
const RE_WHITESPACE = /\s+/g

const RE_UNSAFE_REGION_KEYWORDS = /\b(?:gps|ip|toa do|latitude|longitude|lat|lng|truy van|tim kiem)\b/
const RE_IPV4 = /(?:\d{1,3}\.){3}\d{1,3}/
const RE_IPV6 = /(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9]{0,4}/
const RE_COORD_PAIR = /[+-]?(?:\d+\.\d+|\.\d+)\s*[,;/]\s*[+-]?(?:\d+\.\d+|\.\d+)/
const RE_DEGREE = /\d{1,3}\s*[°º]/
const RE_FLOAT_TOKEN = /(?:^|\s)[+-]?(?:\d+\.\d+|\.\d+)(?:\s|$)/

function foldText(value: string) {
  return value
    .trim()
    .toLocaleLowerCase('vi-VN')
    .normalize('NFD')
    .replace(RE_COMBINING_MARKS, '')
    .replace(RE_LETTER_D, 'd')
    .replace(RE_WHITESPACE, ' ')
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
    return hasExplicitInterests ? EXPLICIT_INTEREST_REASON : 'Hợp với nội dung bạn quan tâm'
  }
  return SAFE_REASON_MAP[folded] || ''
}

function safeRegionLabel(value: unknown) {
  if (typeof value !== 'string') return ''
  const normalized = value.trim()
  if (!normalized || normalized.length > 100) return ''
  if (
    RE_IPV4.test(normalized)
    || RE_IPV6.test(normalized)
    || RE_COORD_PAIR.test(normalized)
    || RE_DEGREE.test(normalized)
    || RE_FLOAT_TOKEN.test(normalized)
  ) {
    return ''
  }
  const folded = foldText(normalized)
  if (RE_UNSAFE_REGION_KEYWORDS.test(folded)) return ''
  return normalized
}

function safeInterestLabels(value: unknown): string[] {
  if (!Array.isArray(value) || value.length === 0) return []
  const result: string[] = []
  for (let i = 0; i < value.length; i++) {
    const item = value[i]
    if (typeof item !== 'string') continue
    const label = INTEREST_LABELS[item] || INTEREST_LABELS[foldText(item)]
    if (label && !result.includes(label)) {
      result.push(label)
      if (result.length === 3) break
    }
  }
  return result
}

export function projectRecommendationExplanation(
  explanation?: Partial<RecommendationExplanation> | null,
): SafeRecommendationExplanation {
  if (!explanation) {
    return {
      reasons: [DEFAULT_REASON],
      regionLabel: '',
      interestLabels: [],
    }
  }
  const interestLabels = safeInterestLabels(explanation.explicit_interests)
  const hasExplicitInterests = interestLabels.length > 0
  const reasons: string[] = []

  const primary = safeReason(explanation.primary_reason, hasExplicitInterests)
  if (primary) reasons.push(primary)

  if (Array.isArray(explanation.reasons)) {
    for (let i = 0; i < explanation.reasons.length; i++) {
      const mapped = safeReason(explanation.reasons[i], hasExplicitInterests)
      if (mapped && !reasons.includes(mapped)) {
        reasons.push(mapped)
      }
    }
  }

  if (hasExplicitInterests) {
    const explicitIndex = reasons.indexOf(EXPLICIT_INTEREST_REASON)
    if (explicitIndex > 0) {
      for (let i = explicitIndex; i > 0; i--) {
        reasons[i] = reasons[i - 1]!
      }
      reasons[0] = EXPLICIT_INTEREST_REASON
    }
  }

  if (reasons.length > 3) {
    reasons.length = 3
  } else if (reasons.length === 0) {
    reasons.push(DEFAULT_REASON)
  }

  return {
    reasons,
    regionLabel: safeRegionLabel(explanation.region_label),
    interestLabels,
  }
}
