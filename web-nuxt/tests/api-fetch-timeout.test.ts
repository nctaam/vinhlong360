import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiFetch } from '../utils/apiFetch'

interface DeadlineModule {
  DEFAULT_API_TIMEOUT_MS: number
  ATTESTATION_TIMEOUT_MS: number
  SITEMAP_TIMEOUT_MS: number
  withRequestDeadline<T>(
    timeoutMs: number,
    operation: (signal: AbortSignal) => Promise<T>,
  ): Promise<T>
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  fetchMock.mockResolvedValue({ ok: true })
  vi.stubGlobal('$fetch', fetchMock)
})

describe('apiFetch request deadlines', () => {
  it('supplies the 10 second default timeout', async () => {
    await apiFetch('/api/example')

    expect(fetchMock).toHaveBeenCalledWith('/api/example', expect.objectContaining({
      timeout: 10_000,
    }))
  })

  it('preserves an explicit caller timeout', async () => {
    await apiFetch('/api/example', { timeout: 750 })

    expect(fetchMock).toHaveBeenCalledWith('/api/example', expect.objectContaining({
      timeout: 750,
    }))
  })

  it('exports exact deadline constants and aborts a never-settling operation', async () => {
    const deadlines = await vi.importActual<DeadlineModule>('../utils/requestDeadline')
    expect(deadlines.DEFAULT_API_TIMEOUT_MS).toBe(10_000)
    expect(deadlines.ATTESTATION_TIMEOUT_MS).toBe(3_000)
    expect(deadlines.SITEMAP_TIMEOUT_MS).toBe(5_000)

    vi.useFakeTimers()
    try {
      let operationSignal: AbortSignal | undefined
      const pending = deadlines.withRequestDeadline(25, signal => {
        operationSignal = signal
        return new Promise((_resolve, reject) => {
          signal.addEventListener('abort', () => reject(new Error('aborted')))
        })
      })
      const rejected = expect(pending).rejects.toThrow(/25/)

      await vi.advanceTimersByTimeAsync(25)

      await rejected
      expect(operationSignal?.aborted).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })
})
