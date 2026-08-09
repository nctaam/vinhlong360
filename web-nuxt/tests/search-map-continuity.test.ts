import { mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MapListSurface from '../components/public/MapListSurface.vue'
import { useSearchViewState } from '../composables/useSearchViewState'

const mapHarness = vi.hoisted(() => {
  let container: HTMLElement | null = null
  const listeners = new Map<string, Array<() => void>>()
  const removeMap = vi.fn()
  const jumpTo = vi.fn()

  class FakeMarker {
    private element: HTMLElement

    constructor(options: { element: HTMLElement }) {
      this.element = options.element
    }

    setLngLat() { return this }
    addTo() {
      container?.append(this.element)
      return this
    }
    remove() { this.element.remove() }
  }

  const map = {
    on: vi.fn((event: string, callback: () => void) => {
      const callbacks = listeners.get(event) || []
      callbacks.push(callback)
      listeners.set(event, callbacks)
      if (event === 'load') queueMicrotask(callback)
      return map
    }),
    off: vi.fn(),
    getCenter: () => ({ lng: 106.01, lat: 10.24 }),
    getZoom: () => 11,
    jumpTo,
    remove: removeMap,
  }

  return {
    FakeMarker,
    jumpTo,
    listeners,
    map,
    removeMap,
    setContainer(value: HTMLElement) { container = value },
  }
})

vi.mock('../composables/useNDAMap', () => ({
  useNDAMap: () => ({
    createMap: vi.fn(async (container: HTMLElement) => {
      mapHarness.setContainer(container)
      return { map: mapHarness.map, maplibregl: { Marker: mapHarness.FakeMarker } }
    }),
  }),
}))

const results = [
  {
    id: 'entity-42',
    name: 'Gốm đỏ Mang Thít',
    type: 'craft_village',
    coordinates: { lat: 10.24, lng: 106.01 },
    attributes: { address: 'Mang Thít, Vĩnh Long' },
    quality: { source_tier: 'official' },
  },
  {
    id: 'entity-99',
    name: 'Chợ nổi Trà Ôn',
    type: 'attraction',
    coordinates: { lat: 9.97, lng: 105.93 },
    attributes: { address: 'Trà Ôn, Vĩnh Long' },
    quality: { source_tier: 'community' },
  },
]

beforeEach(() => {
  sessionStorage.clear()
  window.history.replaceState({}, '', '/tim-kiem')
  mapHarness.removeMap.mockClear()
  mapHarness.jumpTo.mockClear()
  mapHarness.listeners.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('shared search view continuity', () => {
  it('restores query, filters, selected result and scroll key after back navigation', () => {
    const filters = encodeURIComponent(JSON.stringify({ type: ['craft_village'] }))
    const view = useSearchViewState(`/tim-kiem?q=g%E1%BB%91m&area=vinh-long&intent=place&filters=${filters}`)

    view.selectResult('entity-42')
    view.openPanel('map')
    view.setScrollKey('result-entity-42')

    const restored = useSearchViewState(`/tim-kiem?q=g%E1%BB%91m&area=vinh-long&intent=place&filters=${filters}`)
    restored.restoreBackStack()

    expect(restored.state.value.query).toBe('gốm')
    expect(restored.state.value.intent).toBe('place')
    expect(restored.state.value.area?.id).toBe('vinh-long')
    expect(restored.state.value.filters).toEqual({ type: ['craft_village'] })
    expect(restored.state.value.selectedId).toBe('entity-42')
    expect(restored.state.value.panel).toBe('map')
    expect(restored.state.value.scrollKey).toBe('result-entity-42')
  })

  it('keeps selection private and replaces only a sanitized viewport after debounce', async () => {
    vi.useFakeTimers()
    const view = useSearchViewState('/ban-do?q=gốm&intent=place')
    view.selectResult('entity-42')
    view.setViewport({ center: [105.912345, 10.234567], zoom: 12.4 })

    expect(view.url.value).not.toContain('viewport=')
    await vi.advanceTimersByTimeAsync(250)

    expect(view.url.value).toContain('viewport=')
    expect(view.url.value).not.toContain('entity-42')
    expect(view.url.value).not.toContain('105.912345')
    expect(view.url.value).not.toContain('10.234567')
    expect(view.viewportPending.value).toBe(true)
  })
})

describe('MapListSurface coordination and recovery', () => {
  it('uses the same stable id for list rows and markers and selects without moving the camera', async () => {
    const wrapper = await mountSuspended(MapListSurface, {
      props: {
        results,
        selectedId: undefined,
        viewport: { center: [106, 10.2], zoom: 10 },
        mapState: 'ready',
      },
      global: {
        stubs: {
          IconLine: true,
          SourceMark: true,
          FreshnessLine: true,
        },
      },
    })
    await nextTick()
    await nextTick()

    const row = wrapper.get('[data-result-id="entity-42"][data-result-role="list"]')
    const marker = wrapper.get('[data-result-id="entity-42"][data-result-role="marker"]')
    await row.trigger('focus')
    await marker.trigger('click')

    expect(wrapper.emitted('select')).toEqual([['entity-42'], ['entity-42']])
    expect(mapHarness.jumpTo).not.toHaveBeenCalled()
  })

  it('requires explicit activation before committing the panned search area', async () => {
    const wrapper = await mountSuspended(MapListSurface, {
      props: {
        results,
        selectedId: 'entity-42',
        viewport: { center: [106, 10.2], zoom: 10 },
        mapState: 'ready',
      },
      global: { stubs: { IconLine: true, SourceMark: true, FreshnessLine: true } },
    })
    await nextTick()
    await nextTick()

    for (const callback of mapHarness.listeners.get('moveend') || []) callback()
    await nextTick()

    expect(wrapper.emitted('viewport-change')).toEqual([[{ center: [106.01, 10.24], zoom: 11 }]])
    expect(wrapper.emitted('search-area')).toBeUndefined()
    await wrapper.get('[data-search-area]').trigger('click')
    expect(wrapper.emitted('search-area')).toEqual([[{ center: [106.01, 10.24], zoom: 11 }]])
  })

  it('preserves selected list results and addresses when the map renderer fails', async () => {
    const wrapper = await mountSuspended(MapListSurface, {
      props: {
        results,
        selectedId: 'entity-42',
        viewport: undefined,
        mapState: 'error',
      },
      global: { stubs: { IconLine: true, SourceMark: true, FreshnessLine: true } },
    })

    expect(wrapper.get('[data-map-fallback]').text()).toContain('Danh sách vẫn dùng được')
    expect(wrapper.get('[data-result-id="entity-42"]').classes()).toContain('is-selected')
    expect(wrapper.text()).toContain('Mang Thít, Vĩnh Long')
    expect(wrapper.text()).toContain('Chợ nổi Trà Ôn')
  })
})
