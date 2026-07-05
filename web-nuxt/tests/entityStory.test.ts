import { describe, it, expect } from 'vitest'
import { entityStoryTeaser, entityDateline } from '../composables/useEntityStory'

describe('entityStoryTeaser', () => {
  it('prefers attributes.hook over everything', () => {
    expect(entityStoryTeaser({ type: 'dish', attributes: { hook: 'Nước lèo nấu từ mắm bò hóc.' }, description: 'x'.repeat(60), summary: 's' }))
      .toBe('Nước lèo nấu từ mắm bò hóc.')
  })
  it('falls back highlight → famous_for → first sentence → summary', () => {
    expect(entityStoryTeaser({ type: 'attraction', attributes: { highlight: 'H' } })).toBe('H')
    expect(entityStoryTeaser({ type: 'attraction', attributes: { famous_for: 'F' } })).toBe('F')
    expect(entityStoryTeaser({ type: 'dish', attributes: { signature_dish: 'Bún nước lèo' } })).toBe('Bún nước lèo')
    expect(entityStoryTeaser({ type: 'attraction', description: 'Câu đầu tiên ở đây. Câu hai.' })).toBe('Câu đầu tiên ở đây.')
    expect(entityStoryTeaser({ type: 'attraction', summary: 'Chỉ có summary.' })).toBe('Chỉ có summary.')
    expect(entityStoryTeaser({ type: 'attraction' })).toBe('')
  })
  it('prefixes provenance (place) for product/craft_village, before any price', () => {
    expect(entityStoryTeaser({ type: 'product', attributes: { highlight: 'Ngọt thanh' }, place_name: 'Vườn bưởi Bình Minh' }))
      .toBe('Vườn bưởi Bình Minh — Ngọt thanh')
    // no double-prefix when hook already names the place
    expect(entityStoryTeaser({ type: 'product', attributes: { hook: 'Vườn bưởi Bình Minh trồng theo lối xưa.' }, place_name: 'Vườn bưởi Bình Minh' }))
      .toBe('Vườn bưởi Bình Minh trồng theo lối xưa.')
  })
})

describe('entityDateline', () => {
  it('joins type label and area name', () => {
    expect(entityDateline({ area: 'ben-tre' }, 'Đặc sản')).toBe('Đặc sản · Bến Tre')
  })
  it('reads place_area and omits area when unknown', () => {
    expect(entityDateline({ place_area: 'tra-vinh' }, 'Điểm đến')).toBe('Điểm đến · Trà Vinh')
    expect(entityDateline({}, 'Điểm đến')).toBe('Điểm đến')
  })
})
