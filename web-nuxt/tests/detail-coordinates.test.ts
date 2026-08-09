import { describe, expect, it } from 'vitest'

import { normalizeCoords } from '../composables/useCoords'

describe('detail coordinate normalization', () => {
  it.each([
    [null, null],
    ['', ''],
    ['   ', '105.9'],
    [false, false],
    [undefined, 105.9],
  ])('rejects absent or blank coordinate members %#', (lat, lng) => {
    expect(normalizeCoords([lat, lng])).toBeNull()
  })

  it('requires exactly two finite in-range members', () => {
    expect(normalizeCoords([10.2, 105.9, 106])).toBeNull()
    expect(normalizeCoords([91, 105.9])).toBeNull()
    expect(normalizeCoords([10.2, 181])).toBeNull()
    expect(normalizeCoords([Number.NaN, 105.9])).toBeNull()
  })

  it('keeps explicitly numeric zero coordinates valid', () => {
    expect(normalizeCoords([0, 105.9])).toEqual([0, 105.9])
    expect(normalizeCoords([10.2, 0])).toEqual([10.2, 0])
  })

  it('still accepts non-blank numeric strings and swaps reversed coordinates', () => {
    expect(normalizeCoords(['10.2', '105.9'])).toEqual([10.2, 105.9])
    expect(normalizeCoords([105.9, 10.2])).toEqual([10.2, 105.9])
  })
})
