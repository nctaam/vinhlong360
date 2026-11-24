import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import {
  damerauLevenshtein,
  foldVietnamese,
  scoreVietnameseQuery,
} from '../utils/vietnameseSearch'
import SearchDrawer from '../components/SearchDrawer.vue'

describe('vietnameseSearch utilities & drawer integration', () => {
  it('folds Vietnamese diacritics including đ/Đ and collapses whitespace', () => {
    expect(foldVietnamese('  Đờn   ca tài tử Vĩnh Long  ')).toBe('don ca tai tu vinh long')
    expect(foldVietnamese('Cù lao An Bình — Đất phù sa')).toBe('cu lao an binh — dat phu sa')
  })

  it('computes Damerau-Levenshtein transposition distance 1 with early abort', () => {
    expect(damerauLevenshtein('vinh long', 'vihn long')).toBe(1)
    expect(damerauLevenshtein('thit', 'tiht')).toBe(1)
    expect(damerauLevenshtein('an binh', 'completely different', 2)).toBeGreaterThan(2)
  })

  it('ranks exact/prefix title matches above snippet matches and recovers diacritic-free + typo queries', () => {
    const mangThit = [
      { text: 'Quần thể Lò gạch gốm đỏ Mang Thít & Kênh Thầy Cai', weight: 3 },
      { text: 'Di sản Làng nghề', weight: 2 },
    ]
    const cuLao = [
      { text: 'Cù lao An Bình — Vườn chôm chôm & Bưởi Năm Roi', weight: 3 },
      { text: 'Sinh thái Miệt vườn', weight: 2 },
    ]

    expect(scoreVietnameseQuery('mang thit', mangThit)).toBeGreaterThan(0)
    expect(scoreVietnameseQuery('mang tiht', mangThit)).toBeGreaterThan(0)
    expect(scoreVietnameseQuery('mang thit', cuLao)).toBe(0)
  })

  it('SearchDrawer matches diacritic-free and 1-typo queries via Vietnamese fuzzy scorer', async () => {
    const wrapper = mount(SearchDrawer, {
      props: { modelValue: true },
      global: {
        stubs: {
          Teleport: true,
          IconLine: true,
          NuxtLink: { template: '<a><slot /></a>' },
        },
      },
    })

    const input = wrapper.get('input')
    await input.setValue('mang thit')
    expect(wrapper.text()).toContain('Mang Thít')
    expect(wrapper.text()).not.toContain('Bến phà Đình Khao')

    await input.setValue('mang tiht')
    expect(wrapper.text()).toContain('Mang Thít')

    wrapper.unmount()
  })
})
