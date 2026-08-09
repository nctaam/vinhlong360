import { clearNuxtData } from '#app'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { effectScope, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MapListSurface from '../components/public/MapListSurface.vue'
import MapPage from '../pages/ban-do.vue'
import { useSearchViewState } from '../composables/useSearchViewState'

const apiFetchMock = vi.hoisted(() => vi.fn())
mockNuxtImport('apiFetch', () => apiFetchMock)

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
const wrappers: Array<{ unmount: () => void }> = []

beforeEach(() => {
  sessionStorage.clear()
  window.history.replaceState({}, '', '/tim-kiem')
  mapHarness.removeMap.mockClear()
  mapHarness.jumpTo.mockClear()
  mapHarness.listeners.clear()
  apiFetchMock.mockReset()
})

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.useRealTimers()
  await clearNuxtData()
})

describe('shared search view continuity', () => {
  it('restores destination-entry selection, panel and scroll after real back navigation', async () => {
    const filters = encodeURIComponent(JSON.stringify({ type: ['craft_village'] }))
    window.history.replaceState({}, '', `/tim-kiem?q=g%E1%BB%91m&area=vinh-long&intent=place&filters=${filters}`)
    const scope = effectScope()
    const view = scope.run(() => useSearchViewState())!

    view.selectResult('entity-42')
    view.openPanel('map')
    view.setScrollKey('list:144')
    view.setQuery('dừa sáp')
    view.selectResult('entity-99')
    view.openPanel('list')
    view.setScrollKey('list:24')

    window.history.back()
    await vi.waitFor(() => expect(view.state.value.query).toBe('gốm'))

    expect(view.state.value.intent).toBe('place')
    expect(view.state.value.area?.id).toBe('vinh-long')
    expect(view.state.value.filters).toEqual({ type: ['craft_village'] })
    expect(view.state.value.selectedId).toBe('entity-42')
    expect(view.state.value.panel).toBe('map')
    expect(view.state.value.scrollKey).toBe('list:144')
    scope.stop()
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
    expect(view.committedViewport.value).toBeUndefined()
  })

  it('flags unsupported filter keys and value types as visibly sanitized', () => {
    const filters = encodeURIComponent(JSON.stringify({ unknown: 'x', type: { nested: true } }))
    const view = useSearchViewState(`/tim-kiem?q=g%E1%BB%91m&filters=${filters}`)

    expect(view.state.value.filters).toEqual({})
    expect(view.hasMalformedUrl.value).toBe(true)
    expect(view.malformedNotice.value).toContain('không hợp lệ')
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
    wrappers.push(wrapper)
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
    wrappers.push(wrapper)
    await nextTick()
    await nextTick()

    for (const callback of mapHarness.listeners.get('moveend') || []) callback()
    await nextTick()

    expect(wrapper.emitted('viewport-change')).toEqual([[{ center: [106.01, 10.24], zoom: 11 }]])
    expect(wrapper.emitted('search-area')).toBeUndefined()
    await wrapper.get('[data-search-area]').trigger('click')
    expect(wrapper.emitted('search-area')).toEqual([[{ center: [106.01, 10.24], zoom: 11 }]])
  })

  it('captures and restores the list scroll key through the production surface', async () => {
    const wrapper = await mountSuspended(MapListSurface, {
      props: {
        results,
        selectedId: undefined,
        viewport: undefined,
        mapState: 'error',
        scrollKey: 'list:96',
      },
      global: { stubs: { IconLine: true, SourceMark: true, FreshnessLine: true } },
    })
    wrappers.push(wrapper)
    await nextTick()

    const list = wrapper.get<HTMLElement>('.map-list-surface__list')
    expect(list.element.scrollTop).toBe(96)
    list.element.scrollTop = 180
    await list.trigger('scroll')
    await nextTick()

    expect(wrapper.emitted('scroll-key-change')).toEqual([['list:180']])
  })

  it('updates an existing map once for an external viewport without emitting a move loop', async () => {
    const wrapper = await mountSuspended(MapListSurface, {
      props: {
        results,
        selectedId: undefined,
        viewport: { center: [106, 10.2], zoom: 10 },
        mapState: 'ready',
      },
      global: { stubs: { IconLine: true, SourceMark: true, FreshnessLine: true } },
    })
    wrappers.push(wrapper)
    await nextTick()
    await nextTick()
    mapHarness.jumpTo.mockClear()

    await wrapper.setProps({ viewport: { center: [105.62, 9.91], zoom: 12 } })
    await nextTick()

    expect(mapHarness.jumpTo).toHaveBeenCalledTimes(1)
    expect(mapHarness.jumpTo).toHaveBeenCalledWith({ center: [105.62, 9.91], zoom: 12 })
    for (const callback of mapHarness.listeners.get('moveend') || []) callback()
    expect(wrapper.emitted('viewport-change')).toBeUndefined()
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
    wrappers.push(wrapper)

    expect(wrapper.get('[data-map-fallback]').text()).toContain('Danh sách vẫn dùng được')
    expect(wrapper.get('[data-result-id="entity-42"]').classes()).toContain('is-selected')
    expect(wrapper.text()).toContain('Mang Thít, Vĩnh Long')
    expect(wrapper.text()).toContain('Chợ nổi Trà Ôn')
  })
})

describe('/ban-do committed spatial scope', () => {
  it('keeps pending pan non-mutating and changes result ids only after explicit commit', async () => {
    apiFetchMock.mockResolvedValue([
      { id: 'near', name: 'Gốm đỏ', type: 'craft_village', lat: 10.24, lng: 106.01, place_name: 'Mang Thít' },
      { id: 'far', name: 'Dừa sáp', type: 'product', lat: 9.91, lng: 105.62, place_name: 'Cầu Kè' },
    ])
    const wrapper = await mountSuspended(MapPage, {
      route: '/ban-do',
      global: {
        stubs: {
          Breadcrumb: true,
          FilterChips: true,
          PageState: true,
          IconLine: true,
          MapListSurface: {
            props: ['results'],
            emits: ['viewport-change', 'search-area'],
            template: `<div data-map-page-surface>
              <span v-for="result in results" :key="result.id" :data-map-result-id="result.id" />
              <button data-map-pan @click="$emit('viewport-change', { center: [105.62, 9.91], zoom: 11 })" />
              <button data-map-commit @click="$emit('search-area', { center: [105.62, 9.91], zoom: 11 })" />
            </div>`,
          },
        },
      },
    })
    wrappers.push(wrapper)
    await vi.waitFor(() => expect(wrapper.findAll('[data-map-result-id]')).toHaveLength(2))

    await wrapper.get('[data-map-pan]').trigger('click')
    expect(wrapper.findAll('[data-map-result-id]').map(node => node.attributes('data-map-result-id')).sort()).toEqual(['far', 'near'])

    await wrapper.get('[data-map-commit]').trigger('click')
    await nextTick()
    expect(wrapper.findAll('[data-map-result-id]').map(node => node.attributes('data-map-result-id'))).toEqual(['far'])
  })
})
