import { afterEach, describe, expect, it, vi } from 'vitest'
import { yieldToMain } from '../utils/yieldToMain'

describe('yieldToMain', () => {
  const originalDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'scheduler')

  afterEach(() => {
    if (originalDescriptor) {
      Object.defineProperty(globalThis, 'scheduler', originalDescriptor)
    } else {
      Reflect.deleteProperty(globalThis, 'scheduler')
    }
  })

  it('uses globalThis.scheduler.yield when available', async () => {
    const yieldSpy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(globalThis, 'scheduler', {
      value: { yield: yieldSpy },
      configurable: true,
    })

    await yieldToMain()
    expect(yieldSpy).toHaveBeenCalledTimes(1)
  })

  it('falls back to setTimeout(0) when scheduler.yield is unavailable', async () => {
    Object.defineProperty(globalThis, 'scheduler', {
      value: undefined,
      configurable: true,
    })

    await expect(yieldToMain()).resolves.toBeUndefined()
  })
})
