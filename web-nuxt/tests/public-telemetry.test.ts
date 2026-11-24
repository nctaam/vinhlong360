import { describe, expect, it, vi } from 'vitest'

import {
  createBatchedPublicTelemetryTransport,
  createDefaultPublicTelemetryTransport,
  resolvePublicTelemetryEndpoint,
  sanitizePublicTelemetry,
  usePublicTelemetry,
} from '../composables/usePublicTelemetry'

const defaultOutcome = {
  kind: 'outcome' as const,
  eventName: 'search-result-opened' as const,
  outcomeClass: 'detail-opened' as const,
  routeFamily: 'search' as const,
  viewport: 'mobile' as const,
  network: 'online' as const,
  theme: 'nocturne' as const,
}

describe('public telemetry privacy boundary', () => {
  it('redacts raw coordinates and arbitrary payload keys', () => {
    const event = sanitizePublicTelemetry({
      eventName: 'search-result-opened',
      outcomeClass: 'detail-opened',
      routeFamily: 'search',
      viewport: 'mobile',
      network: 'degraded',
      theme: 'nocturne',
      area: 'vinh-long',
      lat: 10.2,
      lng: 105.9,
      entityName: 'Private payload',
    })

    expect(event).toEqual({
      eventName: 'search-result-opened',
      outcomeClass: 'detail-opened',
      routeFamily: 'search',
      viewport: 'mobile',
      network: 'degraded',
      theme: 'nocturne',
      areaId: 'vinh-long',
    })
    expect(event).not.toHaveProperty('lat')
    expect(event).not.toHaveProperty('lng')
    expect(event).not.toHaveProperty('entityName')
  })

  it('rejects phone numbers and private query text instead of serializing them', () => {
    expect(sanitizePublicTelemetry({
      eventName: 'search-submitted',
      outcomeClass: 'result-shown',
      routeFamily: 'search',
      viewport: 'desktop',
      network: 'online',
      theme: 'parchment',
      areaId: 'vinh-long',
      phone: '0909 123 456',
      query: 'goi 0909 123 456 cho toi',
    })).toEqual({
      eventName: 'search-submitted',
      outcomeClass: 'result-shown',
      routeFamily: 'search',
      viewport: 'desktop',
      network: 'online',
      theme: 'parchment',
      areaId: 'vinh-long',
    })

    expect(sanitizePublicTelemetry({
      eventName: 'call-0909123456',
      outcomeClass: 'result-shown',
    })).not.toHaveProperty('eventName')
  })

  it('rejects arbitrary slug-shaped private values from closed telemetry dimensions', () => {
    expect(sanitizePublicTelemetry({
      eventName: 'visitor-lan-nguyen',
      outcomeClass: 'email-lan-example-com',
      harmClass: 'home-address-cai-be',
      areaId: 'nguyen-van-a',
      routeFamily: 'detail',
      viewport: 'mobile',
      network: 'online',
      theme: 'nocturne',
    })).toEqual({
      routeFamily: 'detail',
      viewport: 'mobile',
      network: 'online',
      theme: 'nocturne',
    })
  })

  it('resolves only same-origin telemetry endpoints', () => {
    const origin = 'https://vinhlong360.vn'

    expect(resolvePublicTelemetryEndpoint('/feedback/public-telemetry', origin)).toBe(
      'https://vinhlong360.vn/feedback/public-telemetry',
    )
    expect(resolvePublicTelemetryEndpoint('https://vinhlong360.vn/feedback/public-telemetry', origin)).toBe(
      'https://vinhlong360.vn/feedback/public-telemetry',
    )
    expect(resolvePublicTelemetryEndpoint('//collector.example/private', origin)).toBeUndefined()
    expect(resolvePublicTelemetryEndpoint('https://collector.example/private', origin)).toBeUndefined()
  })

  it('emits outcome, harm and performance events through one sanitized transport', () => {
    const transport = vi.fn()
    const telemetry = usePublicTelemetry({ transport })

    telemetry.trackPublicOutcome({
      eventName: 'planner-completed',
      outcomeClass: 'task-completed',
      routeFamily: 'planner',
      viewport: 'desktop',
      network: 'online',
      theme: 'nocturne',
      areaId: 'vinh-long',
      query: 'must-not-leak',
    } as never)
    telemetry.trackPublicHarm({
      eventName: 'detail-recovery-shown',
      harmClass: 'false-not-found-risk',
      routeFamily: 'detail',
      viewport: 'mobile',
      network: 'offline',
      theme: 'parchment',
    })
    telemetry.trackPerformanceBudget({
      eventName: 'first-useful-result',
      routeFamily: 'search',
      viewport: 'tablet',
      network: 'degraded',
      theme: 'nocturne',
      metric: 'ttfur',
      value: 820,
      budget: 1200,
    })

    expect(transport).toHaveBeenNthCalledWith(1, expect.objectContaining({
      kind: 'outcome',
      eventName: 'planner-completed',
      outcomeClass: 'task-completed',
    }))
    expect(transport.mock.calls[0]?.[0]).not.toHaveProperty('query')
    expect(transport).toHaveBeenNthCalledWith(2, expect.objectContaining({
      kind: 'harm',
      harmClass: 'false-not-found-risk',
    }))
    expect(transport).toHaveBeenNthCalledWith(3, expect.objectContaining({
      kind: 'performance',
      metric: 'ttfur',
      value: 820,
      budget: 1200,
      withinBudget: true,
    }))
  })

  it('never blocks the public task when transport is unavailable', () => {
    const telemetry = usePublicTelemetry({ transport: () => { throw new Error('offline') } })

    expect(() => telemetry.trackPublicOutcome({
      eventName: 'search-recovered',
      outcomeClass: 'task-recovered',
      routeFamily: 'search',
      viewport: 'mobile',
      network: 'offline',
      theme: 'nocturne',
    })).not.toThrow()
  })

  it('keeps the default transport disabled until the public config explicitly enables it', () => {
    const sendBeacon = vi.fn(() => true)
    const fetch = vi.fn((_url: string, _init?: RequestInit) => Promise.resolve({ ok: true }))
    const transport = createDefaultPublicTelemetryTransport({
      config: { public: { publicTelemetryEnabled: false, publicTelemetryEndpoint: '/feedback/public-telemetry' } },
      origin: 'https://vinhlong360.vn',
      sendBeacon,
      fetch,
      Blob,
    })

    transport(defaultOutcome)

    expect(sendBeacon).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('uses sendBeacon when enabled and falls back to keepalive fetch when it declines', () => {
    const sendBeacon = vi.fn(() => false)
    const fetch = vi.fn((_url: string, _init?: RequestInit) => Promise.resolve({ ok: true }))
    const transport = createDefaultPublicTelemetryTransport({
      config: { public: { publicTelemetryEnabled: true, publicTelemetryEndpoint: '/feedback/public-telemetry' } },
      origin: 'https://vinhlong360.vn',
      sendBeacon,
      fetch,
      Blob,
    })

    transport(defaultOutcome)

    expect(sendBeacon).toHaveBeenCalledWith('https://vinhlong360.vn/feedback/public-telemetry', expect.any(Blob))
    expect(fetch).toHaveBeenCalledWith('https://vinhlong360.vn/feedback/public-telemetry', {
      method: 'POST',
      body: expect.any(String),
      headers: { 'content-type': 'application/json' },
      keepalive: true,
    })
  })

  it('batches telemetry via fetchLater(), aborts prior signal, and resets after activation', () => {
    const signals: AbortSignal[] = []
    let resultState = { activated: false }
    const fetchLater = vi.fn((_url: string, init: RequestInit & { activateAfter?: number }) => {
      if (init.signal) signals.push(init.signal)
      return resultState
    })
    const transport = createBatchedPublicTelemetryTransport({
      config: { public: { publicTelemetryEnabled: true, publicTelemetryEndpoint: '/feedback/public-telemetry' } },
      origin: 'https://vinhlong360.vn',
      fetchLater,
      batchWindowMs: 5000,
    })

    transport(defaultOutcome)
    transport({ ...defaultOutcome, eventName: 'search-submitted', outcomeClass: 'result-shown' })

    expect(fetchLater).toHaveBeenCalledTimes(2)
    expect(signals[0]?.aborted).toBe(true)
    expect(signals[1]?.aborted).toBe(false)
    const secondCallInit = fetchLater.mock.calls[1]![1]
    expect(secondCallInit.activateAfter).toBe(5000)
    expect(JSON.parse(String(secondCallInit.body))).toHaveLength(2)

    resultState.activated = true
    transport({ ...defaultOutcome, eventName: 'planner-completed', outcomeClass: 'task-completed' })
    expect(fetchLater).toHaveBeenCalledTimes(3)
    const thirdBody = JSON.parse(String(fetchLater.mock.calls[2]![1].body))
    expect(thirdBody).toHaveLength(1)
    expect(thirdBody[0].eventName).toBe('planner-completed')
  })

  it('falls back safely inside try/catch when fetchLater() throws quota error and enforces queue bounds', () => {
    const sendBeacon = vi.fn(() => true)
    const fetchLater = vi.fn(() => {
      throw new DOMException('QuotaExceededError', 'QuotaExceededError')
    })
    const transport = createBatchedPublicTelemetryTransport({
      config: { public: { publicTelemetryEnabled: true, publicTelemetryEndpoint: '/feedback/public-telemetry' } },
      origin: 'https://vinhlong360.vn',
      fetchLater,
      sendBeacon,
      Blob,
    })

    expect(() => transport(defaultOutcome)).not.toThrow()
    expect(sendBeacon).toHaveBeenCalledTimes(1)
  })

  it('debounces and flushes on visibilitychange hidden when fetchLater is unsupported', () => {
    const listeners = new Map<string, () => void>()
    const fakeDoc = {
      visibilityState: 'visible' as DocumentVisibilityState,
      addEventListener: (name: string, fn: EventListenerOrEventListenerObject) => {
        listeners.set(name, fn as () => void)
      },
      removeEventListener: (name: string) => {
        listeners.delete(name)
      },
    }
    const fetch = vi.fn((_url: string, _init: RequestInit) => Promise.resolve({ ok: true }))
    const sendBeacon = vi.fn(() => false)
    const transport = createBatchedPublicTelemetryTransport({
      config: { public: { publicTelemetryEnabled: true, publicTelemetryEndpoint: '/feedback/public-telemetry' } },
      origin: 'https://vinhlong360.vn',
      sendBeacon,
      fetch,
      document: fakeDoc,
      batchWindowMs: 10_000,
    })

    transport(defaultOutcome)
    transport({ ...defaultOutcome, eventName: 'search-recovered', outcomeClass: 'task-recovered' })
    expect(fetch).not.toHaveBeenCalled()

    fakeDoc.visibilityState = 'hidden'
    listeners.get('visibilitychange')?.()

    expect(fetch).toHaveBeenCalledTimes(1)
    const [, init] = fetch.mock.calls[0]!
    expect(init.keepalive).toBe(true)
    expect(JSON.parse(String(init.body))).toHaveLength(2)
  })
})
