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

    <!-- Guided flow indicator -->
    <ol class="planner-steps" aria-label="Các bước tạo lịch trình">
      <li :class="['planner-step', { active: !stops.length, done: stops.length > 0 }]">
        <span class="step-dot">1</span><span class="step-label">Chọn điểm</span>
      </li>
      <li class="planner-step-sep" aria-hidden="true"></li>
      <li :class="['planner-step', { active: stops.length > 0 && stops.length < 2, done: stops.length >= 2 }]">
        <span class="step-dot">2</span><span class="step-label">Sắp xếp</span>
      </li>
      <li class="planner-step-sep" aria-hidden="true"></li>
      <li :class="['planner-step', { active: stops.length >= 2 }]">
        <span class="step-dot">3</span><span class="step-label">Xem & lưu</span>
      </li>
    </ol>

    <div class="planner-layout">
      <!-- Left: Entity picker -->
      <div class="planner-picker">
        <!-- Source tabs: All vs Favorites -->
        <div class="chip-row chip-row-spaced">
          <button type="button" :class="['chip', { active: sourceTab === 'all' }]" :aria-pressed="sourceTab === 'all'" @click="sourceTab = 'all'">Tất cả</button>
          <button type="button" :class="['chip', { active: sourceTab === 'saved' }]" :aria-pressed="sourceTab === 'saved'" @click="sourceTab = 'saved'">
            ❤️ Đã lưu ({{ favCount }})
          </button>
        </div>
        <div class="search-row search-row-spaced">
          <input v-model="searchQ" type="search" enterkeyhint="search" aria-label="Tìm điểm đến" placeholder="Tìm điểm đến, đặc sản, lưu trú…" />
        </div>
        <div v-if="sourceTab === 'all'" class="chip-row chip-row-spaced">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" :aria-pressed="typeFilter === 'all'" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button" v-for="t in typeChips" :key="t.value" :class="['chip', { active: typeFilter === t.value }]" :aria-pressed="typeFilter === t.value" @click="typeFilter = t.value">
            {{ t.label }}
          </button>
        </div>
        <div class="picker-list">
          <div
            v-for="e in pickerResults"
            :key="e.id"
            :class="['picker-item', { adding: addingId === e.id }]"
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
          <div v-else-if="sourceTab === 'saved' && !favCount" class="premium-empty-state">
            <EmptyState icon="❤️" title="Chưa có điểm đã lưu" message="Nhấn hình trái tim ở các điểm đến để lưu lại, rồi quay lại đây thêm vào lịch trình." />
          </div>
          <div v-else-if="!pickerResults.length" class="premium-empty-state">
            <EmptyState icon="🔎" title="Không tìm thấy" message="Thử từ khóa khác hoặc bỏ bộ lọc loại nhé." />
          </div>
        </div>
      </div>

      <!-- Right: Itinerary builder -->
      <div class="planner-builder">
        <div class="builder-header">
          <div class="builder-title-wrap">
            <input v-model="planTitle" class="input builder-title" placeholder="Tên lịch trình (VD: 2 ngày khám phá Vĩnh Long)" aria-label="Tên lịch trình" maxlength="100" />
            <span v-if="planTitle.length > 80" class="title-counter" :class="{ warn: planTitle.length >= 95 }">{{ planTitle.length }}/100</span>
          </div>
          <div class="builder-actions">
            <button type="button" class="btn btn-sm btn-ghost" @click="clearPlan" :disabled="!stops.length">Xóa tất cả</button>
            <button type="button" :class="['btn', 'btn-sm', 'btn-primary', { 'save-pulse': savePulse }]" @click="savePlan" :disabled="!stops.length || saving">{{ saving ? 'Đang lưu…' : 'Lưu lịch trình' }}</button>
          </div>
        </div>

        <!-- Transport mode selector -->
        <div v-if="stops.length >= 2" class="transport-mode">
          <span class="tm-label">Phương tiện:</span>
          <button type="button" v-for="m in transportModes" :key="m.value" :class="['chip', { active: transportMode === m.value }]" :aria-pressed="transportMode === m.value" @click="transportMode = m.value">
            {{ m.icon }} {{ m.label }}
          </button>
          <div v-if="routeResult" class="route-total">
            {{ formatDistance(routeResult.totalDistance) }} · {{ formatDuration(routeResult.totalDuration) }}
          </div>
          <div v-if="routeLoading" class="route-total route-loading">Đang tính...</div>
          <div v-else-if="routeError" class="route-total route-err" role="status">⚠️ Chưa tính được lộ trình (thử lại sau)</div>
        </div>

        <p v-if="stops.length >= 20" class="max-stops-warn" role="status">Tối đa 20 điểm mỗi lịch trình.</p>
        <span class="sr-only" aria-live="polite" aria-atomic="true">{{ stopAnnounce }}</span>
        <div v-if="!stops.length" class="builder-empty">
          <EmptyState message="Chưa có điểm nào. Chọn điểm đến từ danh sách bên trái để bắt đầu." />
        </div>

        <div v-else class="stop-list">
          <template v-for="(stop, idx) in stops" :key="stop.id + '-' + idx">
            <div class="stop-item" :style="{ animationDelay: `${idx * 50}ms` }">
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
                    <button type="button" v-if="idx > 0" class="btn-icon-sm move" title="Lên" aria-label="Di chuyển lên" @click="moveStop(idx, -1)">↑</button>
                    <button type="button" v-if="idx < stops.length - 1" class="btn-icon-sm move" title="Xuống" aria-label="Di chuyển xuống" @click="moveStop(idx, 1)">↓</button>
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
              <button v-if="plan.id" type="button" :class="['btn btn-sm', plan.is_public ? 'btn-primary' : 'btn-ghost']" @click="publishPlan(pi)">
                {{ plan.is_public ? '🌐 Công khai' : '🔒 Riêng tư' }}
              </button>
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
import type { Itinerary, Entity} from '~/types'
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
  id?: string          // có khi đồng-bộ tài-khoản (server); thiếu = plan local (khách)
  title: string
  stops: PlanStop[]
  savedAt: string
}

const { favorites: favList, count: favCount } = useFavorites()
const { confirmDialog } = useConfirm()
const { isLoggedIn, authHeaders } = useAuth()
const routeError = ref(false)   // OSRM không tính được route (≥2 điểm có toạ độ)

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
const addingId = ref<string | null>(null)
let addingTimer: ReturnType<typeof setTimeout> | null = null
const savePulse = ref(false)
const saving = ref(false)
const stopAnnounce = ref('')
const MAX_STOPS = 20
let savePulseTimer: ReturnType<typeof setTimeout> | null = null

const { createMap: createNDAMap } = useNDAMap()
let mapInstance: unknown = null
let maplibre: unknown = null
let markers: unknown[] = []

const { data, error: fetchError } = await useAsyncData('planner-entities', () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?limit=700')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => TYPES.includes(e.type))
})

const pickerResults = computed(() => {
  let list: Entity[]

  if (sourceTab.value === 'saved') {
    list = favList.value.map(f => ({ id: f.id, name: f.name, type: f.type, place_name: f.place_name, summary: f.summary, coordinates: f.coordinates }))
  } else {
    list = allEntities.value
    if (typeFilter.value !== 'all') {
      list = list.filter((e: Entity) => e.type === typeFilter.value)
    }
  }

  if (searchQ.value.trim()) {
    const query = searchQ.value.toLowerCase()
    list = list.filter((e: Entity) =>
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

// F4: dùng chuẩn chung normalizeCoords (validate + hoán đổi lat/lng đảo)
function extractCoords(entity: Entity): [number, number] | null {
  return normalizeCoords(entity.coordinates)
}

async function addStop(entity: Entity) {
  if (stops.value.length >= MAX_STOPS) {
    stopAnnounce.value = ''
    nextTick(() => { stopAnnounce.value = `Tối đa ${MAX_STOPS} điểm.` })
    return
  }
  const stop = reactive({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    place_name: entity.place_name,
    coords: extractCoords(entity) as [number, number] | null,
    time: '',
    notes: '',
  })
  stops.value.push(stop)
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `Đã thêm ${entity.name}. ${stops.value.length} điểm.` })
  addingId.value = entity.id
  if (addingTimer) clearTimeout(addingTimer)
  addingTimer = setTimeout(() => { addingId.value = null }, 300)
  // P0-19: saved items (favorites) carry no coordinates → fetch detail so the
  // stop can be routed/mapped. Falls back silently (stop still listed) on error.
  if (!stop.coords && entity.id) {
    try {
      const res = await $fetch<Record<string, any>>(`/api/entities/${encodeURIComponent(entity.id)}`)
      const c = normalizeCoords(res?.coordinates)
      if (c) stop.coords = c
    } catch { /* coords stay null */ }
  }
}

function removeStop(idx: number) {
  const name = stops.value[idx]?.name || ''
  stops.value.splice(idx, 1)
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `Đã xóa ${name}. ${stops.value.length} điểm.` })
}

function moveStop(idx: number, dir: number) {
  const target = idx + dir
  if (target < 0 || target >= stops.value.length) return
  const temp = stops.value[idx]
  stops.value[idx] = stops.value[target]
  stops.value[target] = temp
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `${temp.name} chuyển sang vị trí ${target + 1}.` })
}

async function clearPlan() {
  if (stops.value.length && !await confirmDialog('Xóa toàn bộ điểm trong lịch trình đang tạo?', { danger: true, confirmText: 'Xóa' })) return
  stops.value = []
  planTitle.value = ''
  routeResult.value = null
}

async function savePlan() {
  if (!stops.value.length || saving.value) return
  saving.value = true
  try { await _doSave() } finally { saving.value = false }
}
async function _doSave() {
  const plan: SavedPlan = {
    title: planTitle.value.trim() || 'Lịch trình chưa đặt tên',
    stops: JSON.parse(JSON.stringify(stops.value)),
    savedAt: new Date().toISOString(),
  }
  if (isLoggedIn.value) {
    // Đồng-bộ tài-khoản (cross-device)
    try {
      const res = await $fetch<{ id: string }>('/api/my-plans', {
        method: 'POST', headers: authHeaders(),
        body: { title: plan.title, stops: plan.stops },
      })
      plan.id = res.id
    } catch (e: any) {
      showToast(e?.data?.detail || 'Không thể lưu lên tài khoản', 'error')
      return
    }
  } else {
    persistLocal([plan, ...savedPlans.value])
  }
  savedPlans.value.unshift(plan)
  // brief spring feedback on the button to reinforce the save toast
  savePulse.value = true
  if (savePulseTimer) clearTimeout(savePulseTimer)
  savePulseTimer = setTimeout(() => { savePulse.value = false }, 220)
  showToast(`Đã lưu "${plan.title}"${isLoggedIn.value ? ' (đồng bộ tài khoản)' : ''}`, 'success')
}

function persistLocal(plans: SavedPlan[]) {
  if (import.meta.client) {
    try { localStorage.setItem('vl360_plans', JSON.stringify(plans.filter(p => !p.id))) } catch {}
  }
}

async function loadPlan(idx: number) {
  if (stops.value.length && !await confirmDialog('Thay thế lịch trình đang tạo bằng bản đã lưu?', { confirmText: 'Thay thế' })) return
  const plan = savedPlans.value[idx]
  planTitle.value = plan.title
  stops.value = JSON.parse(JSON.stringify(plan.stops))
}

async function deletePlan(idx: number) {
  const plan = savedPlans.value[idx]
  if (!await confirmDialog(`Xóa lịch trình "${plan?.title || 'chưa đặt tên'}"?`, { danger: true, confirmText: 'Xóa' })) return
  if (plan?.id && isLoggedIn.value) {
    try {
      await $fetch(`/api/my-plans/${plan.id}`, { method: 'DELETE', headers: authHeaders() })
    } catch (e: any) {
      showToast(e?.data?.detail || 'Không thể xoá trên tài khoản', 'error')
      return
    }
  }
  savedPlans.value.splice(idx, 1)
  persistLocal(savedPlans.value)
  showToast('Đã xóa lịch trình', 'success')
}

const { show: showToast } = useToast()

async function publishPlan(idx: number) {
  const plan = savedPlans.value[idx]
  if (!plan?.id) return
  const next = !plan.is_public
  try {
    await $fetch(`/api/my-plans/${plan.id}/publish`, { method: 'POST', headers: authHeaders(), body: { is_public: next } })
    plan.is_public = next
    if (next && import.meta.client) {
      const link = `${location.origin}/lich-trinh-chia-se/${plan.id}`
      try { await navigator.clipboard?.writeText(link); showToast('Đã công khai — link đã sao chép', 'success') }
      catch { showToast('Đã công khai', 'success') }
    } else {
      showToast('Đã chuyển về riêng tư', 'success')
    }
  } catch (e: any) { showToast(e?.data?.detail || 'Không thể đổi trạng thái', 'error') }
}

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
  } else if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép lịch trình vào clipboard', 'success')
    }).catch(() => {
      showToast('Không thể sao chép', 'error')
    })
  } else {
    showToast('Trình duyệt không hỗ trợ sao chép', 'error')
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
  routeError.value = false
  const result = await fetchRoute(coords, transportMode.value)
  routeResult.value = result
  routeError.value = !result  // OSRM lỗi/null mà vẫn có ≥2 điểm → báo, không im lặng
  routeLoading.value = false
  updateMap(result)
}

function scheduleRouteCalc() {
  if (routeTimer) clearTimeout(routeTimer)
  routeTimer = setTimeout(computeRoute, 400)
}

let pendingUpdate = false
let lastRouteResult: RouteResult | null = null
let updatingMap = false

async function updateMap(result: RouteResult | null) {
  if (!import.meta.client) return
  lastRouteResult = result
  if (updatingMap) { pendingUpdate = true; return }

  if (!routeMapEl.value) {
    pendingUpdate = true
    return
  }

  updatingMap = true
  try {

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
      .setPopup(new maplibre.Popup({ offset: 25 }).setHTML(`<strong>${num}. ${escapeHtml(s.name)}</strong>`))
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
      (b: { extend: (c: number[]) => typeof b }, c: number[]) => b.extend(c),
      new maplibre.LngLatBounds(coords[0], coords[0])
    )
    mapInstance.fitBounds(bounds, { padding: 40 })
  } else {
    const coords = stopsWithCoords.map(s => [s.coords![1], s.coords![0]])
    const bounds = coords.reduce(
      (b: { extend: (c: number[]) => typeof b }, c: number[]) => b.extend(c),
      new maplibre.LngLatBounds(coords[0], coords[0])
    )
    mapInstance.fitBounds(bounds, { padding: 40 })
  }

  } finally { updatingMap = false }
}

watch(routeMapEl, (el) => {
  if (el && pendingUpdate) {
    pendingUpdate = false
    updateMap(lastRouteResult)
  }
})

// Chỉ tính lại route khi TOẠ-ĐỘ/THỨ-TỰ stop hoặc phương-tiện đổi — KHÔNG khi sửa giờ/ghi-chú.
watch(
  () => [stops.value.map(s => (s.coords ? s.coords.join(',') : 'x')).join('|'), transportMode.value],
  scheduleRouteCalc,
)

onMounted(async () => {
  let local: SavedPlan[] = []
  try {
    const raw = localStorage.getItem('vl360_plans')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) local = parsed
    }
  } catch { /* ignore */ }

  if (isLoggedIn.value) {
    try {
      // có plan khách lưu trước khi đăng nhập → đẩy lên rồi xoá local
      if (local.length) {
        const merged = await $fetch<{ plans: SavedPlan[] }>('/api/my-plans/merge', {
          method: 'POST', headers: authHeaders(), body: { plans: local },
        })
        savedPlans.value = merged.plans || []
        localStorage.removeItem('vl360_plans')
      } else {
        const res = await $fetch<{ plans: SavedPlan[] }>('/api/my-plans', { headers: authHeaders() })
        savedPlans.value = res.plans || []
      }
    } catch {
      savedPlans.value = local  // lỗi mạng → hiển thị tạm local
    }
  } else {
    savedPlans.value = local
  }
})

onBeforeUnmount(() => {
  if (routeTimer) clearTimeout(routeTimer)
  if (addingTimer) clearTimeout(addingTimer)
  if (savePulseTimer) clearTimeout(savePulseTimer)
  if (mapInstance && typeof (mapInstance as any).remove === 'function') (mapInstance as any).remove()
  mapInstance = null
  markers = []
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
.builder-title-wrap { position: relative; flex: 1; min-width: 0; }
.title-counter { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: var(--text-xs); color: var(--muted); pointer-events: none; }
.title-counter.warn { color: var(--error, #d32); font-weight: var(--weight-semibold); }
.max-stops-warn { font-size: var(--text-sm); color: var(--warning, #c90); margin: var(--space-2) 0; }
.stop-card-actions .btn-icon-sm { min-width: 36px; min-height: 36px; }
@media (pointer: coarse) { .stop-card-actions .btn-icon-sm { min-width: 44px; min-height: 44px; } }
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
.stop-card-actions button { min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; border-radius: var(--radius-sm); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle); }
.stop-card-actions button:hover { background: var(--bg-warm); }
.stop-card-actions button:active { transform: scale(.88); transition-duration: .08s; }
.dark .picker-item:hover { background: var(--glass-light); }
.dark .stop-card { background: var(--card); border-color: var(--line); }
.dark .stop-card-actions button:hover { background: rgba(255,255,255,.06); }
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

/* ── Guided flow step indicator ───────────────────────────── */
.planner-steps {
  list-style: none; margin: 0 0 var(--space-5); padding: 0;
  display: flex; align-items: center; gap: var(--space-2);
  flex-wrap: wrap;
}
.planner-step { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--muted); font-size: var(--text-sm); transition: color .3s var(--ease-out); }
.planner-step .step-dot {
  width: 26px; height: 26px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  background: var(--bg-alt); color: var(--muted);
  border: .5px solid var(--line);
  transition: background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out), box-shadow .3s var(--ease-out-expo), transform .35s var(--ease-spring-gentle);
}
.planner-step.active { color: var(--ink); font-weight: var(--weight-semibold); }
.planner-step.active .step-dot { background: var(--primary); color: var(--text-on-dark, #fff); border-color: var(--primary); box-shadow: 0 0 0 4px rgba(var(--primary-rgb), .12); transform: scale(1.05); }
.planner-step.done .step-dot { background: rgba(var(--secondary-rgb), .14); color: var(--secondary-fg); border-color: rgba(var(--secondary-rgb), .3); }
.planner-step.done .step-label { color: var(--ink); }
.planner-step-sep { flex: 1 1 18px; min-width: 18px; max-width: 48px; height: 2px; border-radius: 1px; background: var(--line); }
.dark .planner-step .step-dot { background: var(--bg-alt); border-color: var(--line); }

/* ── Premium picker empty state surface ───────────────────── */
.premium-empty-state {
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .06), transparent 60%),
    var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-4);
  position: relative; overflow: hidden;
}
.premium-empty-state::before {
  content: ""; position: absolute; inset: auto 0 0 0; height: 90px;
  opacity: .06; pointer-events: none;
  background-repeat: no-repeat; background-position: center bottom; background-size: 480px auto;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23586860%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E");
}
.premium-empty-state > * { position: relative; z-index: 1; }
.dark .premium-empty-state {
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .08), transparent 60%),
    var(--card);
}
.dark .premium-empty-state::before {
  opacity: .07;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E");
}

/* ── Picker item: brief highlight when added ──────────────── */
.picker-item.adding { background: rgba(var(--primary-rgb), .12); transform: scale(1.02); }

/* ── Move buttons: draggable affordance on hover ──────────── */
.stop-card-actions button.move:hover { background: var(--bg-warm); border-radius: var(--radius-full); }

/* ── Save button: spring feedback on save ─────────────────── */
.save-pulse { animation: save-pop .22s var(--ease-spring-gentle); }
@keyframes save-pop { 0% { transform: scale(1); } 40% { transform: scale(.96); } 100% { transform: scale(1); } }

/* ── Route loading: pulsing text while computing ──────────── */
.route-loading { animation: route-loading-pulse 1.2s var(--ease-out) infinite; }
@keyframes route-loading-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .picker-item:hover { transform: none; }
  .picker-item:active { transform: none; }
  .picker-item.adding { transform: none; }
  .stop-card:hover { transform: none; }
  .stop-item { animation: none; }
  .planner-step.active .step-dot { transform: none; }
  .save-pulse { animation: none; }
  .route-loading { animation: none; opacity: .7; }
}
</style>
