<template>
  <section
    class="map-list-surface"
    data-map-list-surface
    :data-panel="panel"
    :data-map-state="effectiveMapState"
  >
    <header class="map-list-surface__toolbar">
      <p aria-live="polite">{{ results.length }} kết quả · danh sách là nguồn đối chiếu chính</p>
      <div class="map-list-surface__toggle" role="group" aria-label="Chế độ kết quả">
        <button type="button" :aria-pressed="panel === 'list'" @click="emit('panel-change', 'list')">
          <IconLine name="list" aria-hidden="true" /> Danh sách
        </button>
        <button type="button" :aria-pressed="panel === 'map'" @click="emit('panel-change', 'map')">
          <IconLine name="map" aria-hidden="true" /> Bản đồ
        </button>
      </div>
    </header>

    <div class="map-list-surface__body">
      <!-- ul/li chứ không phải div[role=list] + article[role=listitem]: <article>
           có vai trò ngầm là article và ARIA-in-HTML KHÔNG cho nó nhận listitem,
           nên 120 hàng × 2 chế độ = 240 trong tổng 274 node aria-allowed-role của
           cả đợt quét đều từ đây. Nặng hơn cái axe báo: vai trò listitem là
           name-from-author nên 120 hàng đó KHÔNG có tên khả truy cập, mà vẫn
           tabindex="0" — người dùng NVDA nghe 120 lần "list item" trống rỗng.

           Bỏ tabindex khỏi hàng: /ban-do có 240 điểm dừng Tab liên tiếp (đo được:
           điểm dừng thứ 20 đến 259, chỉ còn ~31 phần tử sau đó), không phím mũi
           tên, không link bỏ qua. Hàng tự nó không phải điều khiển — cái bấm được
           là link bên trong. Bỏ đi còn 120.

           @focusin chứ không @focus: focusin NỔI BỌT, nên việc đồng bộ bản đồ vẫn
           chạy khi bất cứ thứ gì bên trong hàng nhận tiêu điểm — kể cả nội dung do
           bên dùng thay qua <slot name="result"> (tim-kiem.vue:72 dùng EntityCard).
           Gắn thẳng vào link mặc định thì các slot đó mất đồng bộ. -->
      <ul ref="listElement" class="map-list-surface__list" aria-label="Kết quả tìm kiếm theo địa chỉ" @scroll="onListScroll">
        <li
          v-for="result in results"
          :key="result.id"
          :ref="element => rememberRow(result.id, element)"
          class="map-result-row"
          :class="{ 'is-selected': result.id === selectedId }"
          :data-result-id="result.id"
          :data-material-accent="resolveRegionalAccent(result.type)"
          data-result-role="list"
          @focusin="selectFromList(result.id)"
        >
          <slot name="result" :result="result">
            <div class="map-result-row__copy">
              <NuxtLink :to="entityPath(result.id)" class="map-result-row__title" @click="selectFromList(result.id)">{{ result.name }}</NuxtLink>
              <p class="map-result-row__address">{{ resultAddress(result) }}</p>
              <div class="map-result-row__evidence">
                <SourceMark
                  :tier="resultSourceTier(result)"
                  compact
                  :source-title="resultSourceTitle(result)"
                  :source-url="resultSourceUrl(result)"
                  :verified-at="resultVerifiedAt(result)"
                />
                <FreshnessLine
                  v-if="resultUpdatedLabel(result)"
                  :status="resultFreshness(result)"
                  :updated-label="resultUpdatedLabel(result)"
                />
              </div>
            </div>
          </slot>
          <span v-if="result.id === selectedId" class="map-result-row__selected" aria-label="Đang chọn">Đang chọn</span>
        </li>
      </ul>

      <div class="map-list-surface__map-pane" aria-label="Bản đồ kết quả">
        <button type="button" class="map-list-surface__mobile-close" aria-label="Đóng bản đồ và trở lại danh sách" @click="emit('panel-change', 'list')">
          <IconLine name="x" aria-hidden="true" /> Danh sách
        </button>
        <div
          v-show="showRenderer"
          ref="mapElement"
          class="map-list-surface__map"
          role="application"
          aria-label="Bản đồ vị trí kết quả"
          aria-describedby="map-list-instructions"
          tabindex="0"
        />
        <p id="map-list-instructions" class="sr-only">Kéo hoặc thu phóng bản đồ rồi chọn Tìm trong khu vực này để đổi phạm vi. Chọn danh sách bằng bàn phím không làm bản đồ tự di chuyển.</p>
        <MapFallback
          v-if="fallbackState"
          :state="fallbackState"
          :result-count="results.length"
          :selected-address="selectedAddress"
          @retry="retryMap"
        />
        <button
          v-if="pendingViewport && effectiveMapState !== 'error'"
          type="button"
          class="btn btn-primary map-list-surface__search-area"
          data-search-area
          @click="commitSearchArea"
        >
          Tìm trong khu vực này
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue'
import MapFallback from '~/components/public/MapFallback.vue'
import type { Entity } from '~/types'
import type { MapViewport } from '~/types/publicExperience'
import type { FreshnessStatus, SourceTier } from '~/utils/regionalColor'
import { entityPath } from '~/utils/routePaths'
import { resolveFreshnessStatus, resolveRegionalAccent, resolveSourceTier } from '~/utils/regionalColor'
import { normalizeCoords } from '~/composables/useCoords'
import { useNDAMap, type NDAMapState } from '~/composables/useNDAMap'

type MapListResult = Entity & {
  lat?: number | string
  lng?: number | string
  category_color?: string
  emoji?: string
}

type PublicMapState = 'loading' | 'ready' | 'partial' | 'stale' | 'error' | 'offline'
const DEFAULT_VIEWPORT: MapViewport = { center: [106, 10.25], zoom: 10 }

const props = withDefaults(defineProps<{
  results: MapListResult[]
  selectedId?: string
  viewport?: MapViewport
  mapState: PublicMapState
  panel?: 'list' | 'map'
  scrollKey?: string
  viewportPending?: boolean
}>(), {
  selectedId: undefined,
  viewport: undefined,
  panel: 'list',
  scrollKey: undefined,
  viewportPending: false,
})

const emit = defineEmits<{
  select: [id: string]
  'viewport-change': [viewport: MapViewport]
  'search-area': [viewport: MapViewport]
  'panel-change': [panel: 'list' | 'map']
  'scroll-key-change': [scrollKey: string]
}>()

const mapElement = ref<HTMLElement | null>(null)
const listElement = ref<HTMLElement | null>(null)
const internalMapState = ref<NDAMapState>('loading')
const pendingViewport = ref<MapViewport | null>(props.viewportPending && props.viewport
  ? { center: [...props.viewport.center], zoom: props.viewport.zoom }
  : null)
const rowElements = new Map<string, HTMLElement>()
const markers = new Map<string, { marker: { remove: () => void }; element: HTMLButtonElement }>()
const { createMap } = useNDAMap()
let map: any = null
let maplibregl: any = null
let active = true
let starting = false
let suppressNextMoveEnd = false
let lastMapViewport: MapViewport | undefined

const mappableResults = computed(() => props.results.flatMap(result => {
  const coordinates = resultCoordinates(result)
  return coordinates ? [{ result, coordinates }] : []
}))

const effectiveMapState = computed<PublicMapState>(() => {
  if (props.mapState === 'error' || props.mapState === 'offline' || props.mapState === 'partial' || props.mapState === 'stale') return props.mapState
  if (!mappableResults.value.length) return 'ready'
  if (internalMapState.value === 'error') return 'error'
  if (internalMapState.value === 'loading') return 'loading'
  if (internalMapState.value === 'fallback') return 'partial'
  return 'ready'
})

const fallbackState = computed<'loading' | 'error' | 'offline' | 'empty' | 'partial' | 'stale' | null>(() => {
  if (!mappableResults.value.length) return 'empty'
  if (effectiveMapState.value === 'ready') return null
  return effectiveMapState.value
})
const showRenderer = computed(() => !['error', 'offline'].includes(effectiveMapState.value) && mappableResults.value.length > 0)
const selectedAddress = computed(() => resultAddress(props.results.find(result => result.id === props.selectedId)))

function resultCoordinates(result: MapListResult): [number, number] | null {
  if (result.coordinates) return normalizeCoords(result.coordinates)
  return normalizeCoords({ lat: result.lat, lng: result.lng })
}

function resultAddress(result?: MapListResult) {
  if (!result) return ''
  return String(result.attributes?.address || result.place_name || result.place_area || result.area || 'Chưa có địa chỉ chi tiết')
}

function resultSourceTier(result: MapListResult): SourceTier {
  return resolveSourceTier(result.source_freshness?.source_tier || result.quality?.source_tier)
}

function resultSourceTitle(result: MapListResult) {
  return String(result.source_freshness?.source_title || result.quality?.source_title || result.source?.[0]?.name || '')
}

function resultSourceUrl(result: MapListResult) {
  return String(result.source_freshness?.source_url || result.quality?.source_url || result.source?.[0]?.url || '')
}

function resultVerifiedAt(result: MapListResult) {
  return String(result.source_freshness?.verified_at || result.quality?.verified_at || '')
}

function resultFreshness(result: MapListResult): FreshnessStatus {
  return resolveFreshnessStatus(result.source_freshness?.freshness_status)
}

function resultUpdatedLabel(result: MapListResult) {
  return String(result.source_freshness?.updated_at || result.updatedAt || '')
}

function rememberRow(id: string, element: Element | ComponentPublicInstance | null) {
  const htmlElement = element instanceof HTMLElement ? element : element && '$el' in element ? element.$el as HTMLElement : null
  if (htmlElement) rowElements.set(id, htmlElement)
  else rowElements.delete(id)
}

function restoreListScroll(scrollKey?: string) {
  const match = /^list:(\d+)$/.exec(scrollKey || '')
  if (listElement.value && match) listElement.value.scrollTop = Number(match[1])
}

function onListScroll() {
  if (!listElement.value) return
  emit('scroll-key-change', `list:${Math.max(0, Math.round(listElement.value.scrollTop))}`)
}

function selectFromList(id: string) {
  emit('select', id)
}

function esc(value: unknown) {
  return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function popupHTML(result: MapListResult) {
  return `<div data-entity-image-policy="no-image-invariant"><strong>${esc(result.name)}</strong><small>${esc(resultAddress(result))}</small><a class="map-popup-link" href="${entityPath(result.id)}">Xem chi tiết</a></div>`
}

function selectFromMarker(result: MapListResult, coordinates: [number, number]) {
  emit('select', result.id)
  rowElements.get(result.id)?.scrollIntoView?.({ block: 'nearest' })
  if (maplibregl?.Popup && map) {
    new maplibregl.Popup({ offset: 18 })
      .setLngLat([coordinates[1], coordinates[0]])
      .setHTML(popupHTML(result))
      .addTo(map)
  }
}

function clearMarkers() {
  for (const entry of markers.values()) entry.marker.remove()
  markers.clear()
}

function syncMarkerSelection() {
  for (const [id, entry] of markers) {
    const selected = id === props.selectedId
    entry.element.classList.toggle('is-selected', selected)
    entry.element.setAttribute('aria-pressed', String(selected))
  }
}

function syncMarkers() {
  if (!map || !maplibregl?.Marker) return
  clearMarkers()
  for (const { result, coordinates } of mappableResults.value) {
    const element = document.createElement('button')
    element.type = 'button'
    element.className = 'map-locator-marker'
    element.dataset.resultId = result.id
    element.dataset.resultRole = 'marker'
    element.dataset.materialAccent = resolveRegionalAccent(result.type)
    element.setAttribute('aria-label', `Chọn ${result.name}`)
    element.addEventListener('click', () => selectFromMarker(result, coordinates))
    const marker = new maplibregl.Marker({ element, anchor: 'center' })
      .setLngLat([coordinates[1], coordinates[0]])
      .addTo(map)
    markers.set(result.id, { marker, element })
  }
  syncMarkerSelection()
}

function currentViewport(): MapViewport | null {
  if (!map?.getCenter || !map?.getZoom) return null
  const center = map.getCenter()
  const zoom = Number(map.getZoom())
  if (!Number.isFinite(center?.lng) || !Number.isFinite(center?.lat) || !Number.isFinite(zoom)) return null
  return { center: [Number(center.lng), Number(center.lat)], zoom }
}

function sameViewport(left?: MapViewport, right?: MapViewport) {
  if (!left || !right) return left === right
  return left.zoom === right.zoom && left.center[0] === right.center[0] && left.center[1] === right.center[1]
}

function onViewportChange() {
  if (suppressNextMoveEnd) {
    suppressNextMoveEnd = false
    return
  }
  const viewport = currentViewport()
  if (!viewport) return
  lastMapViewport = viewport
  pendingViewport.value = viewport
  emit('viewport-change', viewport)
}

function syncExternalViewport(viewport?: MapViewport, isPending = props.viewportPending) {
  const target = viewport || DEFAULT_VIEWPORT
  pendingViewport.value = isPending && viewport ? { center: [...viewport.center], zoom: viewport.zoom } : null
  if (!map || sameViewport(lastMapViewport, target)) return
  lastMapViewport = { center: [...target.center], zoom: target.zoom }
  suppressNextMoveEnd = true
  map.jumpTo?.({ center: target.center, zoom: target.zoom })
}

function commitSearchArea() {
  if (!pendingViewport.value) return
  emit('search-area', pendingViewport.value)
  pendingViewport.value = null
}

async function startMap() {
  if (!active || starting || map || !mapElement.value || !mappableResults.value.length || ['error', 'offline'].includes(props.mapState)) return
  starting = true
  internalMapState.value = 'loading'
  try {
    const created = await createMap(mapElement.value, {
      center: props.viewport?.center,
      zoom: props.viewport?.zoom,
      isActive: () => active,
      onStateChange: state => { internalMapState.value = state },
    })
    if (!created || !active) return
    map = created.map
    maplibregl = created.maplibregl
    lastMapViewport = props.viewport ? { center: [...props.viewport.center], zoom: props.viewport.zoom } : DEFAULT_VIEWPORT
    map.on('load', syncMarkers)
    map.on('moveend', onViewportChange)
    syncMarkers()
  } catch {
    internalMapState.value = 'error'
  } finally {
    starting = false
  }
}

function retryMap() {
  clearMarkers()
  map?.remove?.()
  map = null
  maplibregl = null
  internalMapState.value = 'loading'
  nextTick(startMap)
}

watch(() => props.selectedId, syncMarkerSelection)
watch([() => props.viewport, () => props.viewportPending], ([viewport, isPending]) => syncExternalViewport(viewport, isPending), { deep: true })
watch(() => props.scrollKey, scrollKey => nextTick(() => restoreListScroll(scrollKey)))
watch(mappableResults, () => {
  if (map) syncMarkers()
  else nextTick(startMap)
})
watch(() => props.mapState, state => {
  if (state === 'ready' && !map) nextTick(startMap)
})

onMounted(() => {
  if (!navigator.onLine) internalMapState.value = 'error'
  restoreListScroll(props.scrollKey)
  startMap()
})

onBeforeUnmount(() => {
  active = false
  clearMarkers()
  map?.remove?.()
  map = null
  listElement.value = null
  rowElements.clear()
})
</script>
