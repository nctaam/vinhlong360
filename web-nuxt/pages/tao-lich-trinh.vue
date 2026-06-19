<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: 'Tạo lịch trình' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">📋</span>
        <div>
          <h1>Tạo lịch trình</h1>
          <p>Lập kế hoạch chuyến đi của bạn — chọn điểm đến, sắp xếp thứ tự và lưu lại.</p>
        </div>
      </div>
    </section>

    <div class="planner-layout">
      <!-- Left: Entity picker -->
      <div class="planner-picker">
        <!-- Source tabs: All vs Favorites -->
        <div class="chip-row chip-row-spaced">
          <button type="button" :class="['chip', { active: sourceTab === 'all' }]" @click="sourceTab = 'all'">Tất cả</button>
          <button type="button" :class="['chip', { active: sourceTab === 'saved' }]" @click="sourceTab = 'saved'">
            ❤️ Đã lưu ({{ favCount }})
          </button>
        </div>
        <div class="search-row search-row-spaced">
          <input v-model="searchQ" type="search" aria-label="Tìm điểm đến" placeholder="Tìm điểm đến, đặc sản, lưu trú…" />
        </div>
        <div v-if="sourceTab === 'all'" class="chip-row chip-row-spaced">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button" v-for="t in typeChips" :key="t.value" :class="['chip', { active: typeFilter === t.value }]" @click="typeFilter = t.value">
            {{ t.label }}
          </button>
        </div>
        <div class="picker-list">
          <div
            v-for="e in pickerResults"
            :key="e.id"
            class="picker-item"
            role="button"
            tabindex="0"
            @click="addStop(e)"
            @keydown.enter="addStop(e)"
            @keydown.space.prevent="addStop(e)"
          >
            <span class="picker-emoji">{{ getTypeMeta(e.type).emoji }}</span>
            <div class="picker-info">
              <strong :title="e.name">{{ e.name }}</strong>
              <small>{{ e.place_name || '' }} · {{ getTypeMeta(e.type).label }}</small>
            </div>
            <button type="button" class="btn btn-sm btn-ghost" title="Thêm vào lịch trình">+</button>
          </div>
          <p v-if="fetchError" class="empty picker-empty">⚠️ Không thể tải danh sách. <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('planner-entities')">Thử lại</button></p>
          <p v-else-if="!pickerResults.length" class="empty picker-empty">Không tìm thấy kết quả.</p>
        </div>
      </div>

      <!-- Right: Itinerary builder -->
      <div class="planner-builder">
        <div class="builder-header">
          <input v-model="planTitle" class="input builder-title" placeholder="Tên lịch trình (VD: 2 ngày khám phá Vĩnh Long)" aria-label="Tên lịch trình" />
          <div class="builder-actions">
            <button type="button" class="btn btn-sm btn-ghost" @click="clearPlan" :disabled="!stops.length">Xóa tất cả</button>
            <button type="button" class="btn btn-sm btn-primary" @click="savePlan" :disabled="!stops.length">Lưu lịch trình</button>
          </div>
        </div>

        <!-- Transport mode selector -->
        <div v-if="stops.length >= 2" class="transport-mode">
          <span class="tm-label">Phương tiện:</span>
          <button type="button" v-for="m in transportModes" :key="m.value" :class="['chip', { active: transportMode === m.value }]" @click="transportMode = m.value">
            {{ m.icon }} {{ m.label }}
          </button>
          <div v-if="routeResult" class="route-total">
            {{ formatDistance(routeResult.totalDistance) }} · {{ formatDuration(routeResult.totalDuration) }}
          </div>
          <div v-if="routeLoading" class="route-total route-loading">Đang tính...</div>
        </div>

        <div v-if="!stops.length" class="builder-empty">
          <EmptyState message="Chưa có điểm nào. Chọn điểm đến từ danh sách bên trái để bắt đầu." />
        </div>

        <div v-else class="stop-list">
          <template v-for="(stop, idx) in stops" :key="stop.id + '-' + idx">
            <div class="stop-item">
              <div class="stop-num">{{ idx + 1 }}</div>
              <div class="stop-connector" v-if="idx < stops.length - 1"></div>
              <div class="stop-card">
                <div class="stop-card-head">
                  <span class="stop-emoji">{{ getTypeMeta(stop.type).emoji }}</span>
                  <div class="stop-card-info">
                    <strong>{{ stop.name }}</strong>
                    <small>{{ stop.place_name || '' }} · {{ getTypeMeta(stop.type).label }}</small>
                  </div>
                  <div class="stop-card-actions">
                    <button type="button" v-if="idx > 0" class="btn-icon-sm" title="Lên" aria-label="Di chuyển lên" @click="moveStop(idx, -1)">↑</button>
                    <button type="button" v-if="idx < stops.length - 1" class="btn-icon-sm" title="Xuống" aria-label="Di chuyển xuống" @click="moveStop(idx, 1)">↓</button>
                    <button type="button" class="btn-icon-sm danger" title="Xóa" aria-label="Xóa điểm dừng" @click="removeStop(idx)">✕</button>
                  </div>
                </div>
                <div class="stop-card-fields">
                  <input
                    v-model="stop.time"
                    class="input stop-time-input"
                    type="text"
                    aria-label="Thời gian dừng"
                    placeholder="VD: 8:00 - 10:00"
                  />
                  <input
                    v-model="stop.notes"
                    class="input stop-note-input"
                    type="text"
                    aria-label="Ghi chú điểm dừng"
                    placeholder="Ghi chú (tùy chọn)"
                  />
                </div>
              </div>
            </div>
            <!-- Route leg info between stops -->
            <div v-if="idx < stops.length - 1 && routeResult?.legs[idx]" class="route-leg">
              <div class="route-leg-line"></div>
              <div class="route-leg-info">
                {{ formatDistance(routeResult.legs[idx].distance) }} · {{ formatDuration(routeResult.legs[idx].duration) }}
              </div>
            </div>
          </template>
        </div>

        <!-- Route map -->
        <ClientOnly>
          <div v-if="stops.length >= 2" class="route-map-section">
            <h3>Bản đồ lộ trình</h3>
            <div ref="routeMapEl" class="route-map"></div>
          </div>
        </ClientOnly>

        <!-- Saved itineraries -->
        <div v-if="savedPlans.length" class="saved-plans">
          <h3>Lịch trình đã lưu</h3>
          <div v-for="(plan, pi) in savedPlans" :key="pi" class="saved-plan-item">
            <button type="button" class="saved-plan-info saved-plan-btn" @click="loadPlan(pi)">
              <strong>{{ plan.title || 'Lịch trình chưa đặt tên' }}</strong>
              <small>{{ plan.stops.length }} điểm · Lưu {{ formatDate(plan.savedAt) }}</small>
            </button>
            <div class="saved-plan-actions">
              <button type="button" class="btn btn-sm btn-ghost" @click="sharePlan(pi)">Chia sẻ</button>
              <button type="button" class="btn btn-sm btn-ghost danger" @click="deletePlan(pi)">Xóa</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
useReveal()
import { TYPE_META, CARD_TYPES } from '~/composables/useConstants'
import { fetchRoute, formatDistance, formatDuration, type TransportMode, type RouteResult } from '~/composables/useRouting'

interface PlanStop {
  id: string
  name: string
  type: string
  place_name?: string
  coords?: [number, number]
  time: string
  notes: string
}

interface SavedPlan {
  title: string
  stops: PlanStop[]
  savedAt: string
}

const { favorites: favList, count: favCount } = useFavorites()

const TYPES = CARD_TYPES as readonly string[]
const typeChips = TYPES.map(t => ({
  value: t,
  label: `${TYPE_META[t].emoji} ${TYPE_META[t].label}`,
}))

const transportModes = [
  { value: 'driving' as TransportMode, icon: '🚗', label: 'Ô tô' },
  { value: 'cycling' as TransportMode, icon: '🚲', label: 'Xe đạp' },
  { value: 'foot' as TransportMode, icon: '🚶', label: 'Đi bộ' },
]

const sourceTab = ref('all')
const searchQ = ref('')
const typeFilter = ref('all')
const planTitle = ref('')
const stops = ref<PlanStop[]>([])
const savedPlans = ref<SavedPlan[]>([])
const transportMode = ref<TransportMode>('driving')
const routeResult = ref<RouteResult | null>(null)
const routeLoading = ref(false)
const routeMapEl = ref<HTMLElement | null>(null)

const { createMap: createNDAMap } = useNDAMap()
let mapInstance: any = null
let maplibre: any = null
let markers: any[] = []

const { data, error: fetchError } = await useAsyncData('planner-entities', () =>
  $fetch<any>('/api/entities?limit=700')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: any) => TYPES.includes(e.type))
})

const pickerResults = computed(() => {
  let list: any[]

  if (sourceTab.value === 'saved') {
    list = favList.value.map(f => ({ id: f.id, name: f.name, type: f.type, place_name: f.place_name, summary: f.summary, coordinates: f.coordinates }))
  } else {
    list = allEntities.value
    if (typeFilter.value !== 'all') {
      list = list.filter((e: any) => e.type === typeFilter.value)
    }
  }

  if (searchQ.value.trim()) {
    const query = searchQ.value.toLowerCase()
    list = list.filter((e: any) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query) ||
      (e.place_name || '').toLowerCase().includes(query)
    )
  }

  return list.slice(0, 50)
})

function getTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

function extractCoords(entity: any): [number, number] | undefined {
  let c = entity.coordinates
  if (!c) return undefined
  if (typeof c === 'string') {
    try { c = JSON.parse(c) } catch { return undefined }
  }
  if (Array.isArray(c) && c.length >= 2) return [c[0], c[1]]
  if (c.lat && c.lng) return [c.lat, c.lng]
  return undefined
}

function addStop(entity: any) {
  stops.value.push({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    place_name: entity.place_name,
    coords: extractCoords(entity),
    time: '',
    notes: '',
  })
}

function removeStop(idx: number) {
  stops.value.splice(idx, 1)
}

function moveStop(idx: number, dir: number) {
  const target = idx + dir
  if (target < 0 || target >= stops.value.length) return
  const temp = stops.value[idx]
  stops.value[idx] = stops.value[target]
  stops.value[target] = temp
}

function clearPlan() {
  stops.value = []
  planTitle.value = ''
  routeResult.value = null
}

function savePlan() {
  if (!stops.value.length) return
  const plan: SavedPlan = {
    title: planTitle.value.trim() || 'Lịch trình chưa đặt tên',
    stops: JSON.parse(JSON.stringify(stops.value)),
    savedAt: new Date().toISOString(),
  }
  savedPlans.value.unshift(plan)
  localStorage.setItem('vl360_plans', JSON.stringify(savedPlans.value))
  showToast(`Đã lưu "${plan.title}"`, 'success')
}

function loadPlan(idx: number) {
  const plan = savedPlans.value[idx]
  planTitle.value = plan.title
  stops.value = JSON.parse(JSON.stringify(plan.stops))
}

function deletePlan(idx: number) {
  savedPlans.value.splice(idx, 1)
  localStorage.setItem('vl360_plans', JSON.stringify(savedPlans.value))
}

const { show: showToast } = useToast()

function sharePlan(idx: number) {
  const plan = savedPlans.value[idx]
  const legs = routeResult.value?.legs || []
  const text = `${plan.title}\n\n` + plan.stops.map((s, i) => {
    let line = `${i + 1}. ${s.name}${s.time ? ` (${s.time})` : ''}${s.notes ? ` — ${s.notes}` : ''}`
    if (i < plan.stops.length - 1 && legs[i]) {
      line += `\n   → ${formatDistance(legs[i].distance)}, ${formatDuration(legs[i].duration)}`
    }
    return line
  }).join('\n')

  if (navigator.share) {
    navigator.share({ title: plan.title, text }).catch(() => {})
  } else {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép lịch trình vào clipboard', 'success')
    }).catch(() => {
      showToast('Không thể sao chép', 'error')
    })
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('vi-VN')
}

let routeTimer: ReturnType<typeof setTimeout> | null = null

async function computeRoute() {
  const coords = stops.value.map(s => s.coords).filter(Boolean) as [number, number][]
  if (coords.length < 2) {
    routeResult.value = null
    updateMap(null)
    return
  }
  routeLoading.value = true
  const result = await fetchRoute(coords, transportMode.value)
  routeResult.value = result
  routeLoading.value = false
  updateMap(result)
}

function scheduleRouteCalc() {
  if (routeTimer) clearTimeout(routeTimer)
  routeTimer = setTimeout(computeRoute, 400)
}

let pendingUpdate = false
let lastRouteResult: RouteResult | null = null

async function updateMap(result: RouteResult | null) {
  if (!import.meta.client) return
  lastRouteResult = result

  if (!routeMapEl.value) {
    pendingUpdate = true
    return
  }

  if (!mapInstance) {
    const res = await createNDAMap(routeMapEl.value)
    mapInstance = res.map
    maplibre = res.maplibregl
    await new Promise<void>(r => mapInstance.on('load', r))
  }

  markers.forEach(m => m.remove())
  markers = []

  if (mapInstance.getSource('route')) {
    mapInstance.removeLayer('route-line')
    mapInstance.removeSource('route')
  }

  const stopsWithCoords = stops.value
    .map((s, i) => ({ ...s, idx: i }))
    .filter(s => s.coords)
  if (!stopsWithCoords.length) return

  stopsWithCoords.forEach((s) => {
    const num = s.idx + 1
    const el = document.createElement('div')
    el.className = 'route-marker'
    el.innerHTML = `<div class="rm-num">${num}</div>`
    const marker = new maplibre.Marker({ element: el })
      .setLngLat([s.coords![1], s.coords![0]])
      .setPopup(new maplibre.Popup({ offset: 25 }).setHTML(`<strong>${num}. ${s.name}</strong>`))
      .addTo(mapInstance)
    markers.push(marker)
  })

  if (result?.geometry?.length) {
    const coords = result.geometry.map((p: [number, number]) => [p[1], p[0]])
    mapInstance.addSource('route', {
      type: 'geojson',
      data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: coords } },
    })
    mapInstance.addLayer({
      id: 'route-line',
      type: 'line',
      source: 'route',
      paint: { 'line-color': '#2563eb', 'line-width': 4, 'line-opacity': 0.8 },
    })
    const bounds = coords.reduce(
      (b: any, c: number[]) => b.extend(c),
      new maplibre.LngLatBounds(coords[0], coords[0])
    )
    mapInstance.fitBounds(bounds, { padding: 40 })
  } else {
    const coords = stopsWithCoords.map(s => [s.coords![1], s.coords![0]])
    const bounds = coords.reduce(
      (b: any, c: number[]) => b.extend(c),
      new maplibre.LngLatBounds(coords[0], coords[0])
    )
    mapInstance.fitBounds(bounds, { padding: 40 })
  }
}

watch(routeMapEl, (el) => {
  if (el && pendingUpdate) {
    pendingUpdate = false
    updateMap(lastRouteResult)
  }
})

watch([stops, transportMode], scheduleRouteCalc, { deep: true })

onMounted(() => {
  try {
    const raw = localStorage.getItem('vl360_plans')
    if (raw) savedPlans.value = JSON.parse(raw)
  } catch { /* ignore */ }
})

onBeforeUnmount(() => {
  if (routeTimer) clearTimeout(routeTimer)
})

useSeoMeta({
  title: 'Tạo lịch trình — vinhlong360',
  description: 'Lập kế hoạch chuyến đi Vĩnh Long: chọn điểm đến, sắp xếp thứ tự và lưu lịch trình cá nhân.',
  robots: 'noindex,follow',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tao-lich-trinh') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: 'Công cụ tạo lịch trình vinhlong360',
      applicationCategory: 'TravelApplication',
      operatingSystem: 'Web',
      url: canonicalUrl('/tao-lich-trinh'),
    }),
  }],
})
</script>

<style scoped>
.picker-list { max-height: 50vh; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
.picker-list::-webkit-scrollbar { width: 6px; }
.picker-list::-webkit-scrollbar-track { background: transparent; }
.picker-list::-webkit-scrollbar-thumb { background: var(--line); border-radius: var(--radius-sm); }
.picker-list::-webkit-scrollbar-thumb:hover { background: var(--muted); }
.picker-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3); border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.picker-item:hover { background: var(--bg-warm); transform: translateX(3px); }
.picker-item:active { transform: scale(.98); transition-duration: .08s; }
.picker-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-md); }
.picker-emoji { font-size: var(--text-lg); flex-shrink: 0; }
.picker-info { flex: 1; min-width: 0; }
.picker-info strong { display: block; font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.picker-info small { color: var(--muted); font-size: var(--text-xs); }
.picker-empty { text-align: center; padding: var(--space-5); color: var(--muted); font-size: var(--text-sm); }
.builder-header { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); }
.builder-actions { display: flex; gap: var(--space-2); }
.stop-item { display: flex; gap: var(--space-3); position: relative; animation: stopIn .3s var(--ease-out) both; }
@keyframes stopIn { from { opacity: 0; transform: translateY(6px); } }
.stop-num {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--primary); color: var(--text-on-dark, #fff);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: var(--weight-bold);
  flex-shrink: 0; z-index: 1;
}
.stop-connector { position: absolute; left: 13px; top: 28px; bottom: -12px; width: 2px; background: var(--primary); opacity: .25; }
.stop-card {
  flex: 1; background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg, 16px); padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-spring-gentle);
}
.stop-card:hover { border-color: var(--border); box-shadow: var(--shadow-sm); transform: translateY(-2px); }
.stop-card-head { display: flex; align-items: center; gap: var(--space-3); }
.stop-emoji { font-size: var(--text-lg); }
.stop-card-info { flex: 1; min-width: 0; }
.stop-card-info strong { display: block; font-size: var(--text-sm); }
.stop-card-info small { color: var(--muted); font-size: var(--text-xs); }
.stop-card-actions { display: flex; gap: var(--space-1); }
.stop-list { margin-bottom: var(--space-4); }
.route-map { height: 300px; border-radius: var(--radius-lg, 16px); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); }
.stop-card-actions button { min-height: 36px; min-width: 36px; display: inline-flex; align-items: center; justify-content: center; }
.dark .picker-item:hover { background: var(--glass-light); }
.dark .stop-card { background: var(--card); border-color: var(--line); }
.dark .stop-card:hover { border-color: var(--border); }
.dark .stop-connector { background: var(--primary-fg); }
.dark .picker-list::-webkit-scrollbar-thumb { background: var(--glass-medium); }
.dark .picker-list::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.2); }
.dark .saved-plan-item { background: var(--bg-alt); border-color: var(--line); }
.dark .saved-plan-item:hover { border-color: rgba(255,255,255,.1); }
.dark .route-map { border-color: var(--line); }
.dark .route-leg-info { background: rgba(255,255,255,.04); }
.dark .route-total { background: rgba(255,255,255,.04); }
.dark .builder-title { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .stop-time-input, .dark .stop-note-input { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .picker-item:hover { transform: none; }
  .picker-item:active { transform: none; }
  .stop-card:hover { transform: none; }
  .stop-item { animation: none; }
}
</style>
