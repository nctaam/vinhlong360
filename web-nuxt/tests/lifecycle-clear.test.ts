import { describe, expect, it, beforeEach } from 'vitest'
import { consumeLifecycleClearInstruction } from '~/composables/useLifecycleClear'

describe('lifecycle clear instruction', () => {
  beforeEach(() => { localStorage.clear(); sessionStorage.clear() })
  it('removes shipped keys once per version and subject', () => {
    localStorage.setItem('vl360_favorites', 'x'); sessionStorage.setItem('chat_sid', 'x')
    const instruction = { version: 'v1', action: 'clear', subject_hash: 's1', keys: ['vl360_favorites', 'chat_sid'] }
    expect(consumeLifecycleClearInstruction(instruction)).toBe(true)
    expect(localStorage.getItem('vl360_favorites')).toBeNull()
    expect(sessionStorage.getItem('chat_sid')).toBeNull()
    expect(consumeLifecycleClearInstruction(instruction)).toBe(false)
    expect(consumeLifecycleClearInstruction({ ...instruction, version: 'v2' })).toBe(true)
  })
})
