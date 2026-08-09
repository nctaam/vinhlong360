// @vitest-environment node

import { describe, expect, it } from 'vitest'
import { resolvePriority, useAdaptivePriority } from '../composables/useAdaptivePriority'
import { recommendationSuggestionId, resolveContextualRecommendationPriority } from '../composables/useContextualRecommendations'
import { projectAdaptivePreferenceSignals } from '../composables/usePersonalizationPreferences'

describe('adaptive priority', () => {
  it('changes CTA only for high-confidence intent with valid action data', () => {
    expect(resolvePriority({ confidence: 'low', defaultCta: 'view', candidateCta: 'directions' }).primaryCta).toBe('view')
    expect(resolvePriority({ confidence: 'high', defaultCta: 'view', candidateCta: 'directions' }).primaryCta).toBe('directions')
    expect(resolvePriority({ confidence: 'high', defaultCta: 'view', candidateCta: 'directions', candidateValid: false }).primaryCta).toBe('view')
  })

  it('lets medium confidence reorder metadata without changing task blocks or CTA', () => {
    const { resolve } = useAdaptivePriority()
    const result = resolve({
      context: { network: 'online' },
      intent: { confidence: 'medium', defaultCta: 'view' },
      candidates: [
        { id: 'task-a', kind: 'task', defaultOrder: 0, adaptiveRank: 9 },
        { id: 'meta-a', kind: 'metadata', defaultOrder: 1, adaptiveRank: 8, reason: 'selected-area' },
        { id: 'meta-b', kind: 'metadata', defaultOrder: 2, adaptiveRank: 1 },
        { id: 'task-b', kind: 'task', defaultOrder: 3, adaptiveRank: 0 },
      ],
    })

    expect(result.primaryCta).toBe('view')
    expect(result.orderedBlocks.map(item => item.id)).toEqual(['task-a', 'meta-b', 'meta-a', 'task-b'])
    expect(result.reasons).toContain('Gần khu vực đã chọn')
    expect(result.reversible).toBe(true)
    expect(result.resetAction).toEqual({ id: 'show-default', label: 'Hiển thị mặc định' })
  })

  it('fails closed offline and caps the viewport to one primary and two suggestions', () => {
    const { resolve } = useAdaptivePriority()
    const result = resolve({
      context: { network: 'offline' },
      intent: { confidence: 'high', defaultCta: 'view', candidateCta: 'directions' },
      candidates: [
        { id: 'one', kind: 'action', role: 'primary', valid: true },
        { id: 'two', kind: 'action', role: 'primary', valid: true },
        { id: 'three', kind: 'suggestion' },
        { id: 'four', kind: 'suggestion' },
        { id: 'five', kind: 'suggestion' },
      ],
    })

    expect(result.primaryCta).toBe('view')
    expect(result.orderedBlocks.filter(item => item.role === 'primary')).toHaveLength(1)
    expect(result.suggestions.map(item => item.id)).toEqual(['three', 'four'])
    expect(result.reversible).toBe(false)
  })

  it('requires a matching valid action contract before changing a high-confidence CTA', () => {
    const { resolve } = useAdaptivePriority()
    const missing = resolve({
      context: { network: 'online' },
      intent: { confidence: 'high', defaultCta: 'view', candidateCta: 'directions' },
      candidates: [{ id: 'details', kind: 'action', cta: 'view', valid: true }],
    })
    const valid = resolve({
      context: { network: 'online' },
      intent: { confidence: 'high', defaultCta: 'view', candidateCta: 'directions', reason: 'unfinished-task' },
      candidates: [{ id: 'directions', kind: 'action', cta: 'directions', valid: true }],
    })

    expect(missing.primaryCta).toBe('view')
    expect(valid.primaryCta).toBe('directions')
    expect(valid.reasons).toContain('Liên quan tác vụ bạn đang tiếp tục')
  })

  it('preserves the default CTA when high confidence has no action candidates', () => {
    const result = useAdaptivePriority().resolve({
      context: { network: 'online' },
      intent: {
        confidence: 'high',
        defaultCta: 'view',
        candidateCta: 'directions',
        reason: 'unfinished-task',
      },
      candidates: [],
    })

    expect(result.primaryCta).toBe('view')
    expect(result.reversible).toBe(false)
    expect(result.reasons).toEqual([])
  })

  it('collapses an unexplained non-default order back to exact defaults', () => {
    const result = useAdaptivePriority().resolve({
      context: { network: 'online' },
      intent: { confidence: 'medium', defaultCta: 'view' },
      candidates: [
        { id: 'default-first', kind: 'metadata', defaultOrder: 0, adaptiveRank: 2 },
        { id: 'adaptive-first', kind: 'metadata', defaultOrder: 1, adaptiveRank: 1 },
      ],
    })

    expect(result.primaryCta).toBe('view')
    expect(result.orderedBlocks.map(item => item.id)).toEqual(['default-first', 'adaptive-first'])
    expect(result.reversible).toBe(false)
    expect(result.reasons).toEqual([])
    expect(result.resetAction).toBeNull()
  })

  it('projects only broad, opted-in preference signals', () => {
    expect(projectAdaptivePreferenceSignals({
      personalization_enabled: true,
      location_enabled: true,
      region_id: 'vinh-long',
      explicit_interests: ['Ẩm thực'],
    })).toEqual(['selected-area', 'explicit-interest'])
    expect(projectAdaptivePreferenceSignals({
      personalization_enabled: false,
      location_enabled: true,
      region_id: 'vinh-long',
      explicit_interests: ['Ẩm thực'],
    })).toEqual([])
  })

  it('adapts recommendation metadata through the shared resolver without mutating items', () => {
    const items = [{ id: 'default-first' }, { id: 'area-first' }]
    const result = resolveContextualRecommendationPriority({
      items,
      context: { network: 'online' },
      intent: { confidence: 'medium', defaultCta: 'view' },
      adaptiveOrder: { 'area-first': 0, 'default-first': 1 },
      reason: 'selected-area',
    })

    expect(result.orderedBlocks.map(item => item.id)).toEqual(['area-first', 'default-first'])
    expect(items.map(item => item.id)).toEqual(['default-first', 'area-first'])
  })

  it('creates attention keys only from opaque public item identifiers', () => {
    expect(recommendationSuggestionId('entity-1')).toBe('recommendation:entity-1')
    expect(recommendationSuggestionId('query=secret&gps=10.25,105.97')).toBe('')
  })
})
