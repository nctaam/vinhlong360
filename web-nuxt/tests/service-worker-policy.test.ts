// @vitest-environment node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import vm from 'node:vm'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

type CacheRecord = {
  match: Mock<(request: FakeRequest) => Promise<FakeResponse | undefined>>
  put: Mock<(request: FakeRequest, response: FakeResponse) => Promise<void>>
  addAll: Mock<(urls: string[]) => Promise<void>>
}

type WorkerFetchEvent = {
  request: FakeRequest
  respondWith: Mock<(value: Promise<unknown>) => void>
}

type WorkerLifecycleEvent = {
  waitUntil: (value: Promise<unknown>) => void
}

type WorkerEvent = WorkerFetchEvent | WorkerLifecycleEvent

type CachePurgeDeclaration = {
  readonly revision: string
  readonly strategy: string
  readonly retained_cache_names: readonly string[]
  readonly forbidden_cache_classes: readonly string[]
  readonly activation_verified: boolean
}

type WorkerGlobal = {
  location: { origin: string }
  clients: { claim: Mock<() => void> }
  skipWaiting: Mock<() => void>
  addEventListener: (type: string, listener: (event: WorkerEvent) => void) => void
  CACHE_PURGE_DECLARATION?: CachePurgeDeclaration
}

class FakeHeaders {
  private readonly values = new Map<string, string>()

  constructor(values: Record<string, string> = {}) {
    for (const [name, value] of Object.entries(values)) this.values.set(name.toLowerCase(), value)
  }

  get(name: string): string | null {
    return this.values.get(name.toLowerCase()) ?? null
  }
}

class FakeRequest {
  readonly url: string
  readonly method: string
  readonly mode: string
  readonly cache: string
  readonly destination: string
  readonly headers: FakeHeaders

  constructor(url: string, init: Partial<Pick<FakeRequest, 'method' | 'mode' | 'cache' | 'destination'>> & { headers?: Record<string, string> } = {}) {
    this.url = url
    this.method = init.method ?? 'GET'
    this.mode = init.mode ?? 'cors'
    this.cache = init.cache ?? 'default'
    this.destination = init.destination ?? ''
    this.headers = new FakeHeaders(init.headers)
  }
}

class FakeResponse {
  readonly ok: boolean
  readonly headers: FakeHeaders

  constructor({ ok = true, headers = {} }: { ok?: boolean; headers?: Record<string, string> } = {}) {
    this.ok = ok
    this.headers = new FakeHeaders(headers)
  }

  clone(): FakeResponse {
    return this
  }
}

const serviceWorkerPath = resolve(process.cwd(), 'public/sw.js')

describe('service worker policy', () => {
  let listeners: Map<string, (event: WorkerEvent) => void>
  let cacheMap: Map<string, CacheRecord>
  let cachesApi: {
    open: Mock<(name: string) => Promise<CacheRecord>>
    keys: Mock<() => Promise<string[]>>
    delete: Mock<(name: string) => Promise<boolean>>
  }
  let fetchSpy: Mock<() => Promise<FakeResponse>>
  let claimSpy: Mock<() => void>
  let skipWaitingSpy: Mock<() => void>
  let workerGlobal: WorkerGlobal

  beforeEach(() => {
    listeners = new Map()
    cacheMap = new Map()
    cachesApi = {
      open: vi.fn(async (name: string) => {
        let cache = cacheMap.get(name)
        if (!cache) {
          const entries = new Map<string, FakeResponse>()
          cache = {
            match: vi.fn(async (request: FakeRequest) => entries.get(request.url)),
            put: vi.fn(async (request: FakeRequest, response: FakeResponse) => {
              entries.set(request.url, response)
            }),
            addAll: vi.fn(async (urls: string[]) => {
              for (const url of urls) entries.set(`https://vinhlong360.vn${url}`, new FakeResponse())
            }),
          }
          cacheMap.set(name, cache)
        }
        return cache
      }),
      keys: vi.fn(async () => [...cacheMap.keys()]),
      delete: vi.fn(async (name: string) => cacheMap.delete(name)),
    }
    fetchSpy = vi.fn(async () => new FakeResponse())
    claimSpy = vi.fn()
    skipWaitingSpy = vi.fn()

    workerGlobal = {
      location: { origin: 'https://vinhlong360.vn' },
      clients: { claim: claimSpy },
      skipWaiting: skipWaitingSpy,
      addEventListener: (type: string, listener: (event: WorkerEvent) => void) => listeners.set(type, listener),
    }
    const context = {
      self: workerGlobal,
      caches: cachesApi,
      fetch: fetchSpy,
      URL,
      Promise,
      console,
    }
    vm.runInNewContext(readFileSync(serviceWorkerPath, 'utf8'), context)
  })

  it('exports the exact frozen launch cache-purge declaration', () => {
    expect(workerGlobal.CACHE_PURGE_DECLARATION).toEqual({
      revision: 'launch-cache-purge-v1',
      strategy: 'delete-all-except',
      retained_cache_names: ['vl360-launch-v1-assets'],
      forbidden_cache_classes: [
        'navigation',
        'html',
        'root-seo',
        'internal',
        'api',
        'selective-open',
        'failed-open',
      ],
      activation_verified: true,
    })
    expect(Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION)).toBe(true)
    expect(Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION?.retained_cache_names)).toBe(true)
    expect(Object.isFrozen(workerGlobal.CACHE_PURGE_DECLARATION?.forbidden_cache_classes)).toBe(true)
  })

  function dispatchFetch(request: FakeRequest): { respondWith: Mock<(value: Promise<unknown>) => void>; response?: Promise<unknown> } {
    let response: Promise<unknown> | undefined
    const respondWith = vi.fn((value: Promise<unknown>) => { response = Promise.resolve(value) })
    listeners.get('fetch')?.({ request, respondWith })
    return { respondWith, response }
  }

  async function activateWithCaches(names: string[]): Promise<string[]> {
    for (const name of names) await cachesApi.open(name)
    const waits: Promise<unknown>[] = []
    listeners.get('activate')?.({ waitUntil: (value: Promise<unknown>) => waits.push(Promise.resolve(value)) })
    await Promise.all(waits)
    return cachesApi.keys()
  }

  it.each([
    new FakeRequest('https://vinhlong360.vn/', { mode: 'navigate' }),
    new FakeRequest('https://vinhlong360.vn/robots.txt'),
    new FakeRequest('https://vinhlong360.vn/sitemap.xml'),
    new FakeRequest('https://vinhlong360.vn/sitemap-media.xml'),
    new FakeRequest('https://vinhlong360.vn/sitemap-index.xml'),
    new FakeRequest('https://vinhlong360.vn/sitemap'),
    new FakeRequest('https://vinhlong360.vn/_internal'),
    new FakeRequest('https://vinhlong360.vn/_internal/launch-readiness'),
    new FakeRequest('https://vinhlong360.vn/api'),
    new FakeRequest('https://vinhlong360.vn/api/entities/a'),
    new FakeRequest('https://vinhlong360.vn/events'),
    new FakeRequest('https://vinhlong360.vn/recommend'),
    new FakeRequest('https://vinhlong360.vn/seo'),
    new FakeRequest('https://vinhlong360.vn/seo/jsonld/a'),
    new FakeRequest('https://vinhlong360.vn/_nuxt/app.js', { cache: 'no-store' }),
    new FakeRequest('https://cdn.example.test/_nuxt/app.js'),
    new FakeRequest('https://vinhlong360.vn/', { headers: { Accept: 'APPLICATION/JSON, TEXT/HTML' } }),
    new FakeRequest('https://vinhlong360.vn/_nuxt/app.js', { method: 'POST' }),
  ])('bypasses policy-bearing or unsafe request %s', (request) => {
    const { respondWith } = dispatchFetch(request)
    expect(respondWith).not.toHaveBeenCalled()
    expect([...cacheMap.values()].flatMap((cache) => [cache.match, cache.put].map((spy) => spy.mock.calls.length))).toEqual([])
  })

  it.each([
    '/_nuxt/app.abc123.js',
    '/fonts/fraunces-latin.woff2',
    '/icons/icon-192.png',
    '/img/hero.webp',
    '/manifest.json',
    '/favicon.svg',
  ])('intercepts reviewed asset %s', async (path) => {
    const result = dispatchFetch(new FakeRequest(`https://vinhlong360.vn${path}`))
    expect(result.respondWith).toHaveBeenCalledTimes(1)
    await result.response
    const cache = cacheMap.get('vl360-launch-v1-assets')
    expect(cache).toBeDefined()
    expect(cache?.put).toHaveBeenCalledTimes(1)
  })

  it.each(['/data/entities.json', '/events/list', '/recommendations', '/plain.css', '/some-page'])('does not intercept unreviewed path %s', (path) => {
    const { respondWith } = dispatchFetch(new FakeRequest(`https://vinhlong360.vn${path}`))
    expect(respondWith).not.toHaveBeenCalled()
  })

  it('does not cache unsuccessful or no-store asset responses', async () => {
    fetchSpy.mockResolvedValueOnce(new FakeResponse({ ok: false }))
    const failed = dispatchFetch(new FakeRequest('https://vinhlong360.vn/_nuxt/fail.js'))
    await failed.response

    fetchSpy.mockResolvedValueOnce(new FakeResponse({ headers: { 'CACHE-CONTROL': 'public, max-age=60, No-StOrE' } }))
    const noStore = dispatchFetch(new FakeRequest('https://vinhlong360.vn/_nuxt/no-store.js'))
    await noStore.response

    const cache = cacheMap.get('vl360-launch-v1-assets')
    expect(cache?.put).not.toHaveBeenCalled()
  })

  it('purges every cache except the launch asset cache on activation', async () => {
    await expect(activateWithCaches([
      'vl360-v3-html',
      'vl360-v3-assets',
      'vl360-launch-assets-v1',
      'vl360-launch-v0-assets',
      'navigation',
      'html',
      'root-seo',
      'internal',
      'api',
      'selective-open',
      'failed-open',
      'vl360-launch-v1-assets',
    ])).resolves.toEqual(['vl360-launch-v1-assets'])
    expect(claimSpy).toHaveBeenCalledTimes(1)
  })
})
