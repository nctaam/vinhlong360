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
  it('strips a leading duplicate of the entity name (auto-imported "{name} — {addr}" summaries)', () => {
    expect(entityStoryTeaser({ type: 'dish', name: 'Catimo Coffee', summary: 'Catimo Coffee — Góc Trần Đại Nghĩa, P. 4' }))
      .toBe('Góc Trần Đại Nghĩa, P. 4')
    // name that itself contains a hyphen must still strip cleanly at the real separator
    expect(entityStoryTeaser({ type: 'dish', name: 'Mèo Ú Kitchen - Món Nhật', summary: 'Mèo Ú Kitchen - Món Nhật — Hẻm 1 Hoàng Thái' }))
      .toBe('Hẻm 1 Hoàng Thái')
    // no false strip when the teaser only starts with a similar word
    expect(entityStoryTeaser({ type: 'dish', name: 'Phở', description: 'Phở bò tái nạm đậm đà.' }))
      .toBe('Phở bò tái nạm đậm đà.')
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
