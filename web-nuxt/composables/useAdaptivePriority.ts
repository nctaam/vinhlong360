export type AdaptiveConfidence = 'low' | 'medium' | 'high'
export type AdaptiveReasonCode =
  | 'official-notice'
  | 'unfinished-task'
  | 'selected-area'
  | 'seasonal'
  | 'explicit-interest'
  | 'recent-item'
  | 'fresh-source'
  | 'default-ranking'

export type AdaptiveCandidateKind = 'task' | 'metadata' | 'action' | 'suggestion'
export type AdaptiveCandidateRole = 'primary' | 'secondary'

export interface AdaptiveCandidate {
  id: string
  kind: AdaptiveCandidateKind
  role?: AdaptiveCandidateRole
  cta?: string
  valid?: boolean
  defaultOrder?: number
  adaptiveRank?: number
  reason?: AdaptiveReasonCode
  [key: string]: unknown
}

export interface AdaptiveIntent {
  confidence?: AdaptiveConfidence
  defaultCta?: string
  candidateCta?: string
  candidateValid?: boolean
  reason?: AdaptiveReasonCode
}

export interface AdaptivePriorityInput<T extends AdaptiveCandidate = AdaptiveCandidate> {
  context?: { network?: 'online' | 'degraded' | 'offline' } | null
  intent?: AdaptiveIntent | null
  candidates?: T[]
}

export const ADAPTIVE_REASON_LABELS: Record<AdaptiveReasonCode, string> = {
  'official-notice': 'Ưu tiên vì cảnh báo chính thức đang hiệu lực',
  'unfinished-task': 'Liên quan tác vụ bạn đang tiếp tục',
  'selected-area': 'Gần khu vực đã chọn',
  seasonal: 'Phù hợp thời gian hoặc mùa hiện tại',
  'explicit-interest': 'Phù hợp sở thích bạn đã chọn',
  'recent-item': 'Liên quan nội dung vừa xem hoặc lưu',
  'fresh-source': 'Nguồn mới cập nhật và có thể kiểm tra',
  'default-ranking': 'Theo thứ tự mặc định',
}

export function adaptiveReasonLabel(value: unknown): string | null {
  return typeof value === 'string' && Object.prototype.hasOwnProperty.call(ADAPTIVE_REASON_LABELS, value)
    ? ADAPTIVE_REASON_LABELS[value as AdaptiveReasonCode]
    : null
}

export function resolvePriority(input: {
  confidence?: AdaptiveConfidence
  defaultCta?: string
  candidateCta?: string
  candidateValid?: boolean
}) {
  const defaultCta = String(input.defaultCta || '')
  const canChange = input.confidence === 'high'
    && input.candidateValid !== false
    && typeof input.candidateCta === 'string'
    && input.candidateCta.trim().length > 0
  return { primaryCta: canChange ? input.candidateCta!.trim() : defaultCta }
}

function stableOrder<T extends AdaptiveCandidate>(candidates: T[]) {
  return candidates
    .map((candidate, index) => ({ candidate, index }))
    .sort((left, right) => (left.candidate.defaultOrder ?? left.index) - (right.candidate.defaultOrder ?? right.index))
    .map(entry => entry.candidate)
}

function reorderMetadata<T extends AdaptiveCandidate>(candidates: T[]) {
  const ordered = stableOrder(candidates)
  const metadata = ordered
    .filter(candidate => candidate.kind === 'metadata')
    .sort((left, right) => (left.adaptiveRank ?? Number.MAX_SAFE_INTEGER) - (right.adaptiveRank ?? Number.MAX_SAFE_INTEGER))
  let metadataIndex = 0
  return ordered.map(candidate => candidate.kind === 'metadata' ? metadata[metadataIndex++]! : candidate)
}

function capActionRoles<T extends AdaptiveCandidate>(candidates: T[]) {
  let primaryAssigned = false
  return candidates.map((candidate) => {
    if (candidate.role !== 'primary') return { ...candidate }
    if (!primaryAssigned) {
      primaryAssigned = true
      return { ...candidate, role: 'primary' as const }
    }
    return { ...candidate, role: 'secondary' as const }
  })
}

function sameOrder(left: AdaptiveCandidate[], right: AdaptiveCandidate[]) {
  return left.length === right.length && left.every((candidate, index) => candidate.id === right[index]?.id)
}

function uniqueReasonLabels(codes: Array<AdaptiveReasonCode | undefined>) {
  return [...new Set(codes.map(adaptiveReasonLabel).filter((value): value is string => !!value))]
}

export function useAdaptivePriority() {
  function resolve<T extends AdaptiveCandidate>(input: AdaptivePriorityInput<T>) {
    const candidates = Array.isArray(input.candidates) ? input.candidates.filter(candidate => !!candidate?.id) : []
    const defaults = stableOrder(candidates)
    const networkSafe = !input.context?.network || input.context.network === 'online'
    const confidence: AdaptiveConfidence = networkSafe && ['low', 'medium', 'high'].includes(input.intent?.confidence || '')
      ? input.intent!.confidence!
      : 'low'

    const adaptMetadata = confidence === 'medium' || confidence === 'high'
    const ranked = adaptMetadata ? reorderMetadata(defaults) : defaults
    const orderedBlocks = capActionRoles(ranked.filter(candidate => candidate.kind !== 'suggestion'))
    const suggestions = ranked.filter(candidate => candidate.kind === 'suggestion').slice(0, 2).map(candidate => ({ ...candidate }))
    const requestedCandidate = String(input.intent?.candidateCta || '').trim()
    const matchingAction = requestedCandidate
      ? candidates.find(candidate => candidate.kind === 'action' && candidate.cta === requestedCandidate)
      : undefined
    const actionDataValid = input.intent?.candidateValid !== false
      && !!matchingAction
      && matchingAction.valid !== false
      && !!String(matchingAction.cta || '').trim()
    const ctaResult = resolvePriority({
      confidence,
      defaultCta: input.intent?.defaultCta,
      candidateCta: requestedCandidate,
      candidateValid: actionDataValid,
    })
    const defaultCta = String(input.intent?.defaultCta || '')
    const ctaChanged = ctaResult.primaryCta !== defaultCta
    const orderChanged = adaptMetadata && !sameOrder(defaults, ranked)
    const changed = ctaChanged || orderChanged
    const reasonCodes = changed
      ? [input.intent?.reason, ...ranked.filter(candidate => candidate.reason).map(candidate => candidate.reason)]
      : []
    const reasonLabels = uniqueReasonLabels(reasonCodes)

    if (changed && !reasonLabels.length) {
      return {
        primaryCta: defaultCta,
        orderedBlocks: capActionRoles(defaults.filter(candidate => candidate.kind !== 'suggestion')),
        suggestions: defaults.filter(candidate => candidate.kind === 'suggestion').slice(0, 2).map(candidate => ({ ...candidate })),
        reasons: [],
        reversible: false,
        resetAction: null,
      }
    }

    return {
      primaryCta: ctaResult.primaryCta,
      orderedBlocks,
      suggestions,
      reasons: reasonLabels,
      reversible: changed,
      resetAction: changed ? { id: 'show-default', label: 'Hiển thị mặc định' } as const : null,
    }
  }

  return { resolve }
}
