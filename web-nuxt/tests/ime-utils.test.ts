import { describe, expect, it } from 'vitest'
import { isImeComposing } from '../utils/ime'

describe('isImeComposing', () => {
  it('returns true when KeyboardEvent.isComposing is true', () => {
    expect(isImeComposing({ isComposing: true, keyCode: 13 })).toBe(true)
  })

  it('returns true when legacy VK_PROCESSKEY (229) is reported (Safari WebKit 165004)', () => {
    expect(isImeComposing({ isComposing: false, keyCode: 229 })).toBe(true)
  })

  it('returns false on normal confirmed Enter submission', () => {
    expect(isImeComposing({ isComposing: false, keyCode: 13 })).toBe(false)
  })
})
