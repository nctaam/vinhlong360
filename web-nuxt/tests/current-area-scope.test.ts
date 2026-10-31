import { describe, expect, it } from 'vitest'
import {
  areaMatchesScope,
  entityMatchesAreaScope,
  isCurrentProvinceArea,
  normalizeCurrentArea,
} from '../utils/safe'

describe('current Vĩnh Long area scope', () => {
  it('canonicalizes current and legacy province identifiers', () => {
    expect(normalizeCurrentArea('vinh-long')).toBe('vinh-long')
    expect(normalizeCurrentArea('ben_tre')).toBe('vinh-long')
    expect(normalizeCurrentArea('province-tv')).toBe('vinh-long')
    expect(isCurrentProvinceArea('tra-vinh')).toBe(true)
    expect(isCurrentProvinceArea('mang-thit')).toBe(false)
  })

  it('matches legacy provenance buckets inside the current province filter', () => {
    expect(areaMatchesScope('ben-tre', 'vinh-long')).toBe(true)
    expect(areaMatchesScope('tra-vinh', 'vinh-long')).toBe(true)
    expect(areaMatchesScope('mang-thit', 'vinh-long')).toBe(false)
    expect(entityMatchesAreaScope({ place_area: 'tra-vinh' }, 'vinh-long')).toBe(true)
    expect(entityMatchesAreaScope({ area: 'vinh-long', place_area: 'mang-thit' }, 'vinh-long')).toBe(true)
  })

  it('keeps historical direct filters exact', () => {
    expect(areaMatchesScope('ben-tre', 'ben-tre')).toBe(true)
    expect(areaMatchesScope('tra-vinh', 'ben-tre')).toBe(false)
    expect(entityMatchesAreaScope({ area: 'tra-vinh' }, 'ben-tre')).toBe(false)
  })
})
