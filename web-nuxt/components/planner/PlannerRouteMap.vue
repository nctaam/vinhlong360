<template>
  <div class="planner-map-column" data-planner-map-column>
    <button
      v-if="stops.length >= 2"
      type="button"
      class="btn btn-outline planner-map-sheet-toggle"
      :aria-expanded="mapSheetOpen"
      aria-controls="planner-map-sheet"
      @click="mapSheetOpen = !mapSheetOpen"
    >
      {{ mapSheetOpen ? 'Đóng bản đồ' : 'Mở bản đồ' }}
    </button>
    <ClientOnly>
      <div v-if="stops.length >= 2" id="planner-map-sheet" class="route-map-section" :class="{ 'is-open': mapSheetOpen }">
        <h2 class="sediment-head">Bản đồ lộ trình</h2>
        <div v-show="mapState !== 'error'" ref="routeMapEl" class="route-map" :data-map-state="mapState"></div>
        <div v-if="mapState === 'error'" class="planner-map-fallback" data-map-fallback role="status">
          <strong>Bản đồ chưa khả dụng</strong>
          <p>Timeline vẫn giữ nguyên thứ tự và chỉnh sửa thủ công được.</p>
          <button type="button" class="btn btn-sm btn-outline" @click="retryMap">Thử lại bản đồ</button>
        </div>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import type { RouteResult } from '~/composables/useRouting'
import type { PlanStop } from '~/utils/plannerSnapshots'
import { escapeHtml } from '~/utils/safe'

const props = defineProps<{
  stops: PlanStop[]
  routeResult: RouteResult | null
  isActive?: () => boolean
}>()

const { createMap: createNDAMap } = useNDAMap()
let mapInstance: any = null
let maplibre: any = null
let markers: any[] = []
const mapState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const mapSheetOpen = ref(false)
const routeMapEl = ref<HTMLElement | null>(null)

let pendingUpdate = false
let lastRouteResult: RouteResult | null = null
let updatingMap = false

function isLifecycleActive() {
  return props.isActive ? props.isActive() : true
}

type IndexedStopWithCoords = PlanStop & { idx: number; coords: [number, number] }

function hasCoords(stop: PlanStop & { idx: number }): stop is IndexedStopWithCoords {
  return Array.isArray(stop.coords) &&
    Number.isFinite(stop.coords[0]) &&
    Number.isFinite(stop.coords[1])
}

function fitMapToCoords(coords: [number, number][]) {
  const first = coords[0]
  if (!first || !mapInstance || !maplibre) return
  const bounds = coords
    .slice(1)
    .reduce((b: any, c) => b.extend(c), new maplibre.LngLatBounds(first, first))
  mapInstance.fitBounds(bounds, { padding: 40 })
}

async function updateMap(result: RouteResult | null = props.routeResult) {
  if (!import.meta.client || !isLifecycleActive()) return
  lastRouteResult = result
  if (updatingMap) { pendingUpdate = true; return }

  if (!routeMapEl.value) {
    pendingUpdate = true
    return
  }

  updatingMap = true
  mapState.value = 'loading'
  try {
    if (!mapInstance) {
      const res = await createNDAMap(routeMapEl.value, { isActive: isLifecycleActive })
      if (!isLifecycleActive()) {
        if (res?.map && typeof (res.map as any).remove === 'function') (res.map as any).remove()
        return
      }
      if (!res) {
        mapState.value = 'error'
        return
      }
      mapInstance = res.map
      maplibre = res.maplibregl
      mapInstance.on('styleimagemissing', (e: any) => {
        if (!mapInstance.hasImage(e.id)) mapInstance.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) })
      })
      await new Promise<void>(r => mapInstance.on('load', r))
      if (!isLifecycleActive()) return
    }

    markers.forEach(m => m.remove())
    markers = []

    if (mapInstance.getSource('route')) {
      mapInstance.removeLayer('route-line')
      mapInstance.removeSource('route')
    }

    const stopsWithCoords = props.stops
      .map((s, i) => ({ ...s, idx: i }))
      .filter(hasCoords)
    if (!stopsWithCoords.length) {
      mapState.value = 'error'
      return
    }

    stopsWithCoords.forEach((s) => {
      const num = s.idx + 1
      const el = document.createElement('div')
      el.className = 'route-marker'
      el.innerHTML = `<div class="rm-num">${num}</div>`
      const marker = new maplibre.Marker({ element: el })
        .setLngLat([s.coords[1], s.coords[0]])
        .setPopup(new maplibre.Popup({ offset: 25 }).setHTML(`<strong>${num}. ${escapeHtml(s.name)}</strong>`))
        .addTo(mapInstance)
      markers.push(marker)
    })

    if (result?.geometry?.length) {
      const coords = result.geometry
        .map((p: [number, number]) => [p[1], p[0]] as [number, number])
        .filter(([lng, lat]) => Number.isFinite(lng) && Number.isFinite(lat))
      mapInstance.addSource('route', {
        type: 'geojson',
        data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: coords } },
      })
      mapInstance.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'route',
        paint: { 'line-color': 'rgb(var(--blue-rgb))', 'line-width': 4, 'line-opacity': 0.8 },
      })
      fitMapToCoords(coords)
    } else {
      const coords = stopsWithCoords.map(s => [s.coords[1], s.coords[0]] as [number, number])
      fitMapToCoords(coords)
    }

    mapState.value = 'ready'
  } catch {
    mapState.value = 'error'
  } finally {
    updatingMap = false
    if (pendingUpdate && mapState.value !== 'error') {
      pendingUpdate = false
      void updateMap(lastRouteResult)
    }
  }
}

async function retryMap() {
  mapState.value = 'loading'
  await nextTick()
  await updateMap(lastRouteResult)
}

watch(routeMapEl, (el) => {
  if (el && pendingUpdate) {
    pendingUpdate = false
    updateMap(lastRouteResult)
  }
})

watch(mapSheetOpen, async (open) => {
  if (!open) return
  await nextTick()
  if (mapInstance && typeof mapInstance.resize === 'function') mapInstance.resize()
  await updateMap(lastRouteResult)
})

onBeforeUnmount(() => {
  if (mapInstance && typeof (mapInstance as any).remove === 'function') (mapInstance as any).remove()
  mapInstance = null
  markers = []
})

defineExpose({
  updateMap,
  retryMap,
})
</script>

<style scoped>
.route-map { height: 300px; border-radius: var(--radius-sheet); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); }
.dark .route-map { border-color: var(--line); }
</style>
