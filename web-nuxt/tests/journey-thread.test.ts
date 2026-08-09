// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'
import { useJourneyThread } from '../composables/useJourneyThread'
import { filterCurrentRecentItems } from '../composables/useRecentlyViewed'

function memoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value) },
    removeItem: (key: string) => { values.delete(key) },
    raw: values,
  }
}

describe('useJourneyThread', () => {
  it('does not treat expired recent records as current intent', () => {
    const items = [
      { id: 'fresh', name: 'Fresh', type: 'place', viewedAt: 9_500 },
      { id: 'stale', name: 'Stale', type: 'place', viewedAt: 8_000 },
    ] as never

    expect(filterCurrentRecentItems(items, 10_000, 1_000).map(item => item.id)).toEqual(['fresh'])
  })

  it('keeps the existing search return path through detail and planner intent', () => {
    const storage = memoryStorage()
    const restoreBackStack = vi.fn()
    const thread = useJourneyThread({
      storage,
      ownerScope: 'user-a',
      now: () => 1_000,
      searchViewState: { restoreBackStack },
    })

    thread.snapshot({
      returnPath: '/tim-kiem?query=cho-noi&intent=place&area=vinh-long',
      intent: 'explore',
    })
    thread.pushIntent('plan', { currentPath: '/tao-lich-trinh?source=detail-1' })

    expect(thread.returnPath.value).toBe('/tim-kiem?query=cho-noi&intent=place&area=vinh-long')
    expect(thread.restore()).toEqual(expect.objectContaining({
      intent: 'plan',
      currentPath: '/tao-lich-trinh?source=detail-1',
      returnPath: '/tim-kiem?query=cho-noi&intent=place&area=vinh-long',
    }))
    expect(restoreBackStack).toHaveBeenCalledOnce()
  })

  it('expires bounded context and isolates it from another signed-in owner', () => {
    const storage = memoryStorage()
    let now = 2_000
    const ownerA = useJourneyThread({ storage, ownerScope: 'user-a', now: () => now, ttlMs: 500 })
    ownerA.snapshot({ returnPath: '/tim-kiem?query=buoi', intent: 'explore' })

    const ownerB = useJourneyThread({ storage, ownerScope: 'user-b', now: () => now, ttlMs: 500 })
    expect(ownerB.restore()).toBeNull()

    ownerA.snapshot({ returnPath: '/tim-kiem?query=buoi', intent: 'explore' })
    now = 2_501
    expect(ownerA.restore()).toBeNull()
    expect(ownerA.returnPath.value).toBe('')
  })

  it('clears continuity when the live auth owner changes', () => {
    const storage = memoryStorage()
    let owner = 'user-a'
    const thread = useJourneyThread({ storage, ownerScope: () => owner, now: () => 2_800 })
    thread.snapshot({ returnPath: '/tim-kiem?query=buoi', intent: 'explore' })

    owner = 'user-b'
    expect(thread.restore()).toBeNull()
    expect(thread.returnPath.value).toBe('')
  })

  it('re-snapshots only the safe public search path for a new owner before detail and planner advance', () => {
    const storage = memoryStorage()
    let owner = 'guest'
    const thread = useJourneyThread({ storage, ownerScope: () => owner, now: () => 3_500 })
    const searchPath = '/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long'

    thread.snapshot({ intent: 'explore', returnPath: searchPath, currentPath: searchPath })
    owner = 'account-a'
    expect(thread.restore()).toBeNull()

    thread.snapshot({ intent: 'explore', returnPath: searchPath, currentPath: searchPath })
    const detail = thread.restore()
    expect(detail?.returnPath).toBe(searchPath)
    thread.pushIntent('explore', { currentPath: '/dia-diem/gom-do-mang-thit', returnPath: detail?.returnPath })

    const detailJourney = thread.restore()
    thread.pushIntent('plan', { currentPath: '/tao-lich-trinh?source=gom-do-mang-thit', returnPath: detailJourney?.returnPath })
    const plannerJourney = thread.restore()
    expect(plannerJourney).toEqual(expect.objectContaining({
      intent: 'plan',
      currentPath: '/tao-lich-trinh?source=gom-do-mang-thit',
      returnPath: searchPath,
    }))
    expect(plannerJourney?.returnPath).toBe(searchPath)
    expect([...storage.raw.values()].join('')).not.toContain('account-a')

    thread.clear()
    expect(thread.restore()).toBeNull()
    expect(thread.snapshot({ intent: 'explore', returnPath: '//evil.example/steal' })).toBeNull()
    expect([...storage.raw.values()].join('')).toBe('')
  })

  it('persists only bounded public continuity fields', () => {
    const storage = memoryStorage()
    const thread = useJourneyThread({ storage, ownerScope: 'guest', now: () => 3_000 })

    thread.snapshot({
      returnPath: '/tim-kiem?query=vuon-trai-cay',
      intent: 'explore',
      currentPath: '/dia-diem/entity-1',
      recentItemIds: Array.from({ length: 20 }, (_, index) => `recent-${index}`),
      savedItemIds: ['saved-1'],
      rawGps: '10.25,105.97',
      ip: '203.0.113.10',
    } as never)

    const persisted = [...storage.raw.values()].join('')
    expect(persisted).not.toContain('10.25,105.97')
    expect(persisted).not.toContain('203.0.113.10')
    expect(thread.restore()?.recentItemIds).toHaveLength(12)
  })
})
