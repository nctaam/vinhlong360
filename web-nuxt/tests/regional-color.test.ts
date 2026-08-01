import { describe, expect, it } from 'vitest'
import { resolveFreshnessStatus, resolveRegionalAccent, resolveSourceTier } from '../utils/regionalColor'

describe('regional color resolver', () => {
  it.each([
    ['craft_village', 'clay'],
    ['pottery', 'clay'],
    ['product', 'clay'],
    ['nature', 'leaf'],
    ['agriculture', 'leaf'],
    ['experience', 'river'],
    ['accommodation', 'river'],
    ['dish', 'amber'],
    ['event', 'amber'],
    ['directory', 'neutral'],
    ['free community text', 'neutral'],
    [undefined, 'neutral'],
  ] as const)('maps %s to %s without location or image input', (input, expected) => {
    expect(resolveRegionalAccent(input)).toBe(expected)
  })

  it('normalizes only approved source-tier aliases', () => {
    expect(resolveSourceTier('official')).toBe('official')
    expect(resolveSourceTier('government')).toBe('official')
    expect(resolveSourceTier('partner')).toBe('verified')
    expect(resolveSourceTier('ugc')).toBe('community')
    expect(resolveSourceTier('gold')).toBe('unknown')
    expect(resolveSourceTier('https://gov.vn')).toBe('unknown')
  })

  it('normalizes freshness without inventing recency', () => {
    expect(resolveFreshnessStatus('fresh')).toBe('fresh')
    expect(resolveFreshnessStatus('aging')).toBe('aging')
    expect(resolveFreshnessStatus('stale')).toBe('stale')
    expect(resolveFreshnessStatus('yesterday')).toBe('unknown')
  })
})
