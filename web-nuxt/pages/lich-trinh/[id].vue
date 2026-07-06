<template>
  <section v-if="itinerary" class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: itineraryTitle }]">
      <template #before>
        <button type="button" class="bc-back" aria-label="Quay lại" @click="goBack">
          <span aria-hidden="true">←</span>
        </button>
      </template>
    </Breadcrumb>

    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🗓️</span>
        <div>
          <span class="itin-eyebrow"><IconLine :name="areaMeta.icon" /> {{ areaMeta.name }} · {{ itinerary.duration }}</span>
          <h1>{{ itineraryTitle }}</h1>
          <p>{{ itinerary.stops?.length || 0 }} điểm dừng — hình dạng một ngày trọn vẹn, từ sương sớm mặt sông tới lúc nắng ngả màu mật ong.</p>
        </div>
      </div>

      <!-- Signature: sun-arc rail — populated hero version of the day-arc
           strip (lich-trinh/index.vue). Real per-stop dots positioned by
           parsed stop.time along the dawn→dusk gradient: before reading a
           single stop, the shape of the day is visible (front-loaded
           morning, siesta gap at noon, golden-hour finish — §2/§10). -->
      <div v-if="sunArcDots.length" class="day-arc day-arc-hero" role="img" :aria-label="`Hình dạng ngày: ${sunArcDots.length} điểm dừng từ sáng tới tối`">
        <span class="day-arc-track" aria-hidden="true"></span>
        <span v-for="(d, i) in sunArcDots" :key="i" class="day-arc-dot" :style="{ left: d.pct + '%' }" :title="d.name">
          <span class="day-arc-dot-num" aria-hidden="true">{{ i + 1 }}</span>
        </span>
        <div class="day-arc-legend" aria-hidden="true">
          <span>🌅 Sáng sớm</span><span>☀️ Trưa</span><span>🌇 Hoàng hôn</span>
        </div>
      </div>
    </section>
    <p class="lead lead-flush">{{ itinerary.summary || itinerary.description || '' }}</p>

    <div class="itin-actions">
      <ClientOnly>
        <SaveButton :entity="itinerarySaveShape" :show-label="true" />
        <ShareButton :title="itineraryTitle" :text="itinerary.summary || itinerary.description" />
        <button type="button" class="btn btn-ghost btn-sm" aria-label="Báo cáo lịch trình" @click="openReport('entity', id)">🚩 Báo cáo</button>
      </ClientOnly>
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline btn-sm">+ Tự tạo lịch trình</NuxtLink>
    </div>

    <!-- Transport mode + total -->
    <ClientOnly>
      <div v-if="stopsWithCoords.length >= 2" class="transport-mode transport-mode-spaced">
        <span class="tm-label">Phương tiện:</span>
        <button type="button" v-for="m in transportModes" :key="m.value" :class="['chip', { active: transportMode === m.value }]" :aria-pressed="transportMode === m.value" @click="switchMode(m.value)">
          {{ m.icon }} {{ m.label }}
        </button>
      </div>
    </ClientOnly>

    <div class="sediment-head timeline-head">
      <h2>Lịch trình chi tiết</h2>
    </div>
    <ol class="timeline">
      <template v-for="(stop, idx) in (itinerary.stops || [])" :key="stopIdentity(stop) || idx">
        <!-- Chapter divider — "chapters of the day," inserted the first time
             a stop crosses into a new time-of-day band (§3: Buổi sáng / Buổi
             trưa / Buổi chiều). Quiet hairline + serif label, not a full
             section break; reuses the .sediment-head recipe's tick colors. -->
        <li v-if="isNewChapter(idx)" class="timeline-chapter" :key="'chapter-' + idx" aria-hidden="true">
          <span class="tc-label">{{ CHAPTER_LABEL[stopChapters[idx]!] }}</span>
        </li>
        <li class="step">
          <span class="step-time">{{ stop.time || '' }}</span>
          <div :class="['step-card', stop.type ? `cat-${catClass(stop.type)}` : '']">
            <span class="step-emoji" aria-hidden="true">{{ typeEmoji(stop.type) }}</span>
            <div class="step-content">
              <h3>
                <NuxtLink v-if="stopIdentity(stop)" :to="entityPath(stopIdentity(stop))" class="stop-link">{{ stop.name || stopIdentity(stop) }}</NuxtLink>
                <span v-else>{{ stop.name || 'Điểm dừng' }}</span>
              </h3>
              <span v-if="stop.type" class="step-type-label">{{ typeLabel(stop.type) }}</span>
              <p v-if="stop.summary" class="summary">{{ stop.summary }}</p>
              <p v-if="stop.note" class="step-note-callout"><span class="tnc-glyph" aria-hidden="true">☞</span>{{ stop.note }}</p>
            </div>
          </div>
        </li>
        <!-- Route leg info between stops — extended into a narrative bridge:
             not just a distance stat, but a whisper of what's coming next
             (§5/§7: "1.2km · 15 phút → tới Chợ nổi Cái Bè"). -->
        <li v-if="idx < (itinerary.stops || []).length - 1 && routeLegs[idx]" class="route-leg" :key="'leg-' + idx">
          <div class="route-leg-line"></div>
          <div class="route-leg-info">
            {{ formatDistance(routeLegs[idx].distance) }} · {{ formatDuration(routeLegs[idx].duration) }}
            <span v-if="nextStopName(idx)" class="route-leg-next"> → tới {{ nextStopName(idx) }}</span>
          </div>
        </li>
      </template>
    </ol>

    <!-- Route map -->
    <ClientOnly>
      <div v-if="stopsWithCoords.length >= 2" class="route-map-section reveal">
        <h3>Bản đồ lộ trình</h3>
        <!-- declutter-3 T4: route-total dời từ panel transport-mode xuống đây —
             số liệu lộ trình đứng cạnh bản đồ, hết tranh chỗ với chips phương tiện -->
        <div v-if="routeResult" class="route-total">
          {{ formatDistance(routeResult.totalDistance) }} · {{ formatDuration(routeResult.totalDuration) }}
        </div>
        <div v-if="routeLoading" class="route-total route-loading">Đang tính...</div>
        <div v-if="routeError && !routeLoading" class="route-total" role="status">Chưa tính được lộ trình. <button type="button" class="chip" @click="computeRoute">Thử lại</button></div>
        <div class="route-map-wrap">
          <div v-if="routeLoading" class="route-map-loading" role="status">🗺️ Đang vẽ lộ trình…</div>
          <div ref="routeMapEl" class="route-map"></div>
        </div>
      </div>
    </ClientOnly>

    <!-- Related itineraries -->
    <div class="reveal">
      <NuxtErrorBoundary>
        <ClientOnly>
          <LazyAIRecommendations v-if="itinerary.area" title="Khám phá thêm" :limit="4" />
        </ClientOnly>
      </NuxtErrorBoundary>
    </div>
  </section>
  <div v-else-if="pending" class="page">
    <SkeletonList :count="4" />
  </div>
  <div v-else-if="fetchError" class="page">
    <EmptyState icon="⚠️" tone="error" title="Không thể tải lịch trình" message="Lỗi kết nối. Vui lòng thử lại.">
      <template #actions><NuxtLink to="/lich-trinh" class="btn btn-outline btn-sm">Về danh sách</NuxtLink></template>
    </EmptyState>
  </div>
  <div v-else class="page">
    <EmptyState message="Không tìm thấy lịch trình." />
  </div>
</template>

<script setup lang="ts">
import type { Itinerary, Entity} from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { fetchRoute, formatDistance, formatDuration, type TransportMode, type RouteResult, type RouteLeg } from '~/composables/useRouting'

useReveal()

const route = useRoute()
const router = useRouter()
const id = normalizeRouteParam(route.params.id)
const encodedId = encodePathId(id)

const goBack = () => goBackOr('/lich-trinh')

const { openReport } = useReport()

const { data: itinerary, error: fetchError, status } = await useAsyncData(`itinerary-${id}`, () =>
  apiFetch<Itinerary>(`/api/itineraries/${encodedId}`)
)
const pending = computed(() => status.value === 'pending')
const itineraryTitle = computed(() => itinerary.value?.title || itinerary.value?.name || 'Lịch trình')

if (import.meta.server && fetchError.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy lịch trình' })
}

const areaMeta = computed(() => {
  const area = itinerary.value?.area
  return (area ? AREA_META[area] : null) || { emoji: '📍', name: area || '' }
})

const itinerarySaveShape = computed(() => ({
  id: `itinerary-${id}`,
  name: itinerary.value?.title || itinerary.value?.name || '',
  type: 'itinerary',
  summary: itinerary.value?.summary || itinerary.value?.description || '',
  images: [] as string[],
}))

function typeEmoji(type?: string) {
  if (!type) return '📍'
  return TYPE_META[type]?.emoji || '📍'
}

function typeLabel(type?: string) {
  if (!type) return ''
  return TYPE_META[type]?.label || type
}

function catClass(type?: string) {
  if (!type) return 'place'
  return TYPE_META[type]?.cat || 'place'
}

function stopIdentity(stop: any): string {
  return String(stop?.id || stop?.entityId || stop?.entity_id || '')
}

// ── Time-of-day parsing (signature moment, §10 sun-arc rail + timeline
// chaptering). `stop.time` is free Vietnamese text — literal clock times
// ("06:30", "6h sáng"), period labels ("Sáng sớm", "Trưa", "Hoàng hôn"), and
// multi-day/weekday prefixes ("Ngày 2 – Chiều", "CN – Sáng"), plus non-time
// labels ("Mua quà", "Tráng miệng"). We resolve each to an hour-of-day (0–24)
// for positioning along the dawn→dusk gradient — real per-stop math, not
// decorative (§7 premium cue).
const PERIOD_HOUR: Record<string, number> = {
  'sáng sớm': 5.5, 'sớm': 5.5, 'bình minh': 5.5,
  'giữa sáng': 8.5, 'sáng': 7.5,
  'trưa': 11.5,
  'xế chiều': 15.5, 'xế': 15,
  'chiều': 14.5,
  'hoàng hôn': 17.5,
  'tối': 19, 'đêm': 20.5,
  'mua quà': 16, 'tráng miệng': 13,
}
function parseStopHour(timeStr?: string): number | null {
  if (!timeStr) return null
  // Strip a leading "Ngày N – " / "CN – " / "Thứ 7 – " day/weekday prefix —
  // the time-of-day tail is what matters for the sun-arc position.
  const tail = timeStr.split('–').pop()?.trim().toLowerCase() || timeStr.trim().toLowerCase()
  const clockMatch = tail.match(/(\d{1,2})[:h](\d{2})?/)
  if (clockMatch) {
    const h = Number(clockMatch[1])
    const m = clockMatch[2] ? Number(clockMatch[2]) : 0
    if (h >= 0 && h <= 24) return h + m / 60
  }
  for (const key of Object.keys(PERIOD_HOUR)) {
    if (tail.includes(key)) return PERIOD_HOUR[key]
  }
  return null
}

// Chapter boundaries mirror the sun-arc's dawn/noon/dusk bands (§3 detail-page
// layout: "Buổi sáng" / "Buổi trưa" / "Buổi chiều" dividers before 11:00 /
// 11:00–14:00 / after 14:00).
function stopChapter(hour: number | null): 'morning' | 'noon' | 'afternoon' | null {
  if (hour === null) return null
  if (hour < 11) return 'morning'
  if (hour < 14) return 'noon'
  return 'afternoon'
}
const CHAPTER_LABEL: Record<string, string> = { morning: 'Buổi sáng', noon: 'Buổi trưa', afternoon: 'Buổi chiều' }

const stopHours = computed(() => (itinerary.value?.stops || []).map(s => parseStopHour(s.time)))
const stopChapters = computed(() => stopHours.value.map(h => stopChapter(h)))
// Only render a chapter divider the FIRST time a chapter is seen, in order —
// turns one long list into 2-3 legible "chapters of the day."
function isNewChapter(idx: number) {
  const ch = stopChapters.value[idx]
  if (!ch) return false
  return stopChapters.value.slice(0, idx).every(prev => prev !== ch)
}

// Sun-arc rail dot positions (0–100%) — real per-stop time when available,
// even spread as a graceful fallback so the rail still reads meaningfully
// with zero timed stops.
const sunArcDots = computed(() => {
  const stops = itinerary.value?.stops || []
  const hours = stopHours.value
  const known = hours.filter((h): h is number => h !== null)
  return stops.map((s, i) => {
    const h = hours[i]
    const pct = h !== null
      ? Math.min(98, Math.max(2, ((h - 5) / 15) * 100)) // 5:00–20:00 span → 0–100%
      : (known.length ? (i / Math.max(1, stops.length - 1)) * 100 : 50)
    return { name: s.name || stopIdentity(s), pct }
  })
})
const nextStopName = (idx: number) => {
  const stops = itinerary.value?.stops || []
  const next = stops[idx + 1]
  return next ? (next.name || stopIdentity(next)) : ''
}

// --- Route map & routing ---
const transportModes = [
  { value: 'driving' as TransportMode, icon: '🚗', label: 'Ô tô' },
  { value: 'cycling' as TransportMode, icon: '🚲', label: 'Xe đạp' },
  { value: 'foot' as TransportMode, icon: '🚶', label: 'Đi bộ' },
]

const routeMapEl = ref<HTMLElement | null>(null)
const routeResult = ref<RouteResult | null>(null)
const routeLoading = ref(false)
const transportMode = ref<TransportMode>('driving')

const routeLegs = computed<Record<number, RouteLeg>>(() => {
  if (!routeResult.value?.legs) return {}
  const map: Record<number, RouteLeg> = {}
  const coordIdxs = stopsWithCoords.value.map(s => s.idx)
  for (let i = 0; i < routeResult.value.legs.length; i++) {
    const stopIdx = coordIdxs[i]
    const leg = routeResult.value.legs[i]
    if (stopIdx !== undefined && leg) {
      map[stopIdx] = leg
    }
  }
  return map
})

interface StopCoord {
  name: string
  idx: number
  coords: [number, number]
}

const stopsWithCoords = ref<StopCoord[]>([])

const { createMap: createNDAMap } = useNDAMap()
let mapInstance: any = null
let maplibre: any = null
let markers: any[] = []

// F3: dùng chuẩn chung normalizeCoords (validate hữu hạn + tự hoán đổi lat/lng đảo)
function extractCoords(raw: any): [number, number] | null {
  return normalizeCoords(raw)
}

function loadCoords() {
  const stops = itinerary.value?.stops
  if (!stops?.length) return

  const results: StopCoord[] = []
  for (let i = 0; i < stops.length; i++) {
    const s = stops[i]
    if (!s) continue
    const coords = extractCoords(s.coordinates)
    const stopId = s.id || s.entityId || s.entity_id || ''
    if (coords) {
      results.push({ name: s.name || stopId, idx: i, coords })
    }
  }

  stopsWithCoords.value = results
}

const routeError = ref(false)
async function computeRoute() {
  const coords = stopsWithCoords.value.map(s => s.coords)
  if (coords.length < 2) { routeResult.value = null; routeError.value = false; return }

  routeLoading.value = true
  routeResult.value = await fetchRoute(coords, transportMode.value)
  routeError.value = !routeResult.value
  routeLoading.value = false
  renderMap(routeResult.value)
}

function switchMode(mode: TransportMode) {
  transportMode.value = mode
  computeRoute()
}

let renderingMap = false
async function renderMap(result: RouteResult | null) {
  if (!import.meta.client || !routeMapEl.value || renderingMap) return
  renderingMap = true
  try {

  if (!mapInstance) {
    const res = await createNDAMap(routeMapEl.value)
    mapInstance = res.map
    maplibre = res.maplibregl
    mapInstance.on('styleimagemissing', (e: any) => {
      if (!mapInstance.hasImage(e.id)) mapInstance.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) })
    })
  }

  markers.forEach(m => m.remove())
  markers = []

  const stops = stopsWithCoords.value
  if (!stops.length) return

  stops.forEach((s) => {
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

  function addRouteLine() {
    if (mapInstance.getSource('route')) {
      mapInstance.removeLayer('route-line')
      mapInstance.removeSource('route')
    }
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
      const coords = stops.map(s => [s.coords[1], s.coords[0]])
      const bounds = coords.reduce(
        (b: { extend: (c: number[]) => typeof b }, c: number[]) => b.extend(c),
        new maplibre.LngLatBounds(coords[0], coords[0])
      )
      mapInstance.fitBounds(bounds, { padding: 40 })
    }
  }

  if (mapInstance.isStyleLoaded()) {
    addRouteLine()
  } else {
    mapInstance.once('load', addRouteLine)
  }

  } finally { renderingMap = false }
}

watch(routeMapEl, (el) => {
  if (el && stopsWithCoords.value.length >= 2) {
    renderMap(routeResult.value)
  }
})

onMounted(() => {
  loadCoords()
  computeRoute()
})

onBeforeUnmount(() => {
  if (mapInstance && typeof (mapInstance as any).remove === 'function') (mapInstance as any).remove()
  mapInstance = null
})

// --- SEO ---
if (itinerary.value && !itinerary.value.error) {
  const it = itinerary.value
  const itTitle = it.title || it.name || ''
  const itDesc = it.summary || it.description || ''
  useSeoMeta({
    title: `${itTitle} — vinhlong360`,
    description: itDesc,
    ogTitle: `${itTitle} — vinhlong360`,
    ogDescription: itDesc,
  })

  const ld: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': 'TouristTrip',
    name: itTitle,
    description: itDesc,
    touristType: 'Sightseeing',
  }
  if (it.stops?.length) {
    ld.itinerary = {
      '@type': 'ItemList',
      itemListElement: it.stops.map((s, i: number) => {
        const stopId = stopIdentity(s)
        const item: Record<string, any> = {
          '@type': 'ListItem',
          position: i + 1,
          name: s.name || stopId || `Diem dung ${i + 1}`,
        }
        if (stopId) item.item = canonicalUrl(entityPath(stopId))
        return item
      }),
    }
  }
  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
      { '@type': 'ListItem', position: 2, name: 'Lịch trình', item: 'https://vinhlong360.vn/lich-trinh' },
      { '@type': 'ListItem', position: 3, name: itTitle },
    ],
  }

  useHead({
    link: [{ rel: 'canonical', href: itineraryUrl(String(it.id || id)) }],
    script: [
      { type: 'application/ld+json', innerHTML: JSON.stringify(ld) },
      { type: 'application/ld+json', innerHTML: JSON.stringify(breadcrumb) },
    ],
  })
}
</script>

<!-- detail.css nạp theo route (bỏ khỏi global entry.css; phần dùng-chung ở detail-shared.css) -->
<style src="~/assets/css/detail.css"></style>

<style scoped>
/* ══════════════════════════════════════════════════════════════════════
   Sun-arc rail — signature moment (§10). Populated hero version of the
   day-arc strip on lich-trinh/index.vue: real per-stop dots positioned by
   parsed stop.time along a dawn→dusk gradient. Shows the SHAPE of the day
   before a single stop is read. Horizontal + time-of-day axis — distinct
   from tuyen-duong's vertical per-card .route-rail (a route path, not a
   day's rhythm).
   ══════════════════════════════════════════════════════════════════════ */
/* Local eyebrow — events.css's shared .dateline-eyebrow is page-scoped to
   le-hoi/su-kien only (not global), so this page carries its own copy of the
   same recipe rather than importing shared CSS out of scope. */
.itin-eyebrow {
  display: block; font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--muted);
  margin: 0 0 var(--space-2);
}
.day-arc { position: relative; margin-top: var(--space-6); }
.day-arc-hero { height: 64px; }
.day-arc-track {
  position: absolute; left: 0; right: 0; top: 22px; height: 3px; border-radius: var(--radius-full);
  background: linear-gradient(90deg,
    var(--river-600) 0%,
    color-mix(in srgb, var(--river-600) 40%, var(--amber-600) 60%) 30%,
    var(--amber-600) 50%,
    color-mix(in srgb, var(--amber-600) 45%, var(--clay-600) 55%) 72%,
    var(--clay-600) 100%);
  /* one-time left-to-right draw-on, "a day unfolding" */
  transform-origin: left center;
  animation: dayArcDraw .6s var(--ease-out-expo) both;
  animation-delay: .1s;
}
@keyframes dayArcDraw { from { transform: scaleX(0); } }
.day-arc-dot {
  position: absolute; top: 14px; transform: translateX(-50%);
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--card); color: var(--primary-fg);
  box-shadow: 0 0 0 2px var(--primary-fg) inset, var(--shadow-xs);
  font-size: var(--text-2xs); font-weight: var(--weight-bold); font-variant-numeric: tabular-nums;
  cursor: default;
  animation: dayArcDotIn .4s var(--ease-out) both;
  transition: transform .25s var(--ease-spring-gentle);
}
.day-arc-dot:hover { transform: translateX(-50%) scale(1.18); }
.day-arc-dot:nth-child(2) { animation-delay: .18s; }
.day-arc-dot:nth-child(3) { animation-delay: .22s; }
.day-arc-dot:nth-child(4) { animation-delay: .26s; }
.day-arc-dot:nth-child(5) { animation-delay: .30s; }
.day-arc-dot:nth-child(n+6) { animation-delay: .34s; }
@keyframes dayArcDotIn { from { opacity: 0; transform: translateX(-50%) translateY(4px); } }
.day-arc-dot-num { line-height: 1; }
.day-arc-legend {
  position: absolute; inset: auto 0 0 0; display: flex; justify-content: space-between;
  font-size: var(--text-2xs); color: var(--muted); text-transform: uppercase; letter-spacing: var(--tracking-caps);
  font-weight: var(--weight-semibold);
}
.dark .day-arc-dot { background: var(--card); box-shadow: 0 0 0 2px var(--primary-fg) inset, 0 1px 3px rgba(0,0,0,.4); }

.itin-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; margin: var(--space-4) 0; }
.itin-actions .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.itin-actions .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.itin-actions .btn:active { transform: scale(.95); transition-duration: .08s; }

/* Mode selector panel: snug card-like container */
.transport-mode-spaced {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-alt);
  border: .5px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  /* Reserve height so client-only mount doesn't shift layout (CLS) */
  min-height: 56px;
}
.dark .transport-mode-spaced { background: rgba(255,255,255,.03); border-color: var(--line); }
.transport-mode .chip { transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), background .3s var(--ease-out), border-color .3s var(--ease-out); }
.transport-mode .chip:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.transport-mode .chip:active { transform: scale(.95); transition-duration: .08s; }

/* Section head introducing the timeline (WCAG 1.3.1: was h1→h3, this restores h2) */
.timeline-head { margin: var(--space-5) 0 var(--space-2); }
.timeline { list-style: none; margin: 0; padding: 0 0 0 24px; position: relative; }
/* Branded vertical journey spine */
.timeline::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--primary-fg) 0%, rgba(var(--primary-rgb), .35) 100%);
  opacity: .4;
}
/* ── Timeline chapter divider — "chapters of the day" (§3). Quiet hairline +
   small serif label, reusing the sediment-head tick recipe so it reads as
   the same editorial system as the rest of the site, not a new device. ── */
.timeline-chapter { position: relative; margin: var(--space-6) 0 var(--space-3); padding-left: var(--space-1); }
.timeline-chapter:first-child { margin-top: 0; }
.tc-label {
  position: relative; display: inline-flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-editorial); font-size: var(--text-2xs); font-weight: 600;
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--muted);
  padding-left: var(--space-3);
}
.tc-label::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: .95em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .tc-label::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }

.step { position: relative; }
/* Connector dot anchoring each step to the spine */
.step::before {
  content: "";
  position: absolute;
  left: -19.5px;
  top: 22px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--primary-fg);
  box-shadow: 0 0 0 3px var(--bg);
  z-index: 1;
}
.step-card { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-xs); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.step-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.step-card:active { transform: scale(.97); transition-duration: .08s; }
.step-emoji { font-size: 1.6rem; line-height: 1; transition: transform .35s var(--ease-spring-gentle); }
.step-card:hover .step-emoji { transform: scale(1.1) rotate(-3deg); }
.stop-link { color: var(--ink); font-weight: var(--weight-semibold); transition: color .3s var(--ease-out); border-radius: var(--radius-sm); }
.stop-link:hover { color: var(--primary-fg); }
.stop-link:active { opacity: .7; }
.stop-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* Type label as scannable badge pill */
.step-type-label {
  background: var(--bg-alt);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  line-height: 1.4;
}
.dark .step-type-label { background: rgba(255,255,255,.06); }

/* Summary contrast lift in dark mode */
.dark .step-card .summary { color: rgba(255,255,255,.72); }

/* ── Note callout — respectful etiquette/context notes (§8: chùa Khmer,
   seasonal caveats) surfaced as a warm amber-tinted aside instead of plain
   gray text, so a cultural note reads as considered, not an afterthought. ── */
.step-note-callout {
  display: flex; align-items: flex-start; gap: var(--space-2);
  margin: var(--space-2) 0 0; padding: var(--space-2) var(--space-3);
  background: color-mix(in srgb, var(--amber-600) 10%, transparent);
  border-left: 2px solid color-mix(in srgb, var(--amber-600) 55%, transparent);
  border-radius: var(--radius-sm); font-size: var(--text-sm); line-height: var(--leading-normal);
  color: var(--ink);
}
.tnc-glyph { flex-shrink: 0; color: var(--amber-600); font-size: var(--text-sm); line-height: 1.4; }
.dark .step-note-callout { background: color-mix(in srgb, var(--amber-500) 14%, transparent); border-left-color: color-mix(in srgb, var(--amber-500) 55%, transparent); }
.dark .tnc-glyph { color: var(--amber-500); }

.route-leg { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) 0 var(--space-2) var(--space-6); }
.route-leg-line { width: 2px; height: 20px; background: var(--line); border-radius: 1px; transition: background .3s var(--ease-out); }
.route-leg-info { font-size: var(--text-xs); color: var(--muted); }
/* Narrative bridge — the next stop's name whispered inline, so a distance
   stat becomes a handoff between two moments in the day (§5/§7). */
.route-leg-next { color: var(--primary-fg); font-weight: var(--weight-medium); }

.route-map-section { margin-top: var(--space-6); }
/* Branded accent on the map section title */
.route-map-section h3 {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  margin-bottom: var(--space-3);
  padding-left: var(--space-3);
  border-left: 3px solid var(--secondary);
}
.route-map { height: clamp(240px, 50vh, 400px); border-radius: var(--radius-lg); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); transition: box-shadow .35s var(--ease-out-expo); }
.route-map-wrap { position: relative; }
/* Designed loading placeholder: shimmer surface + gentle pulse */
.route-map-loading {
  position: absolute; inset: 0; z-index: 1;
  display: flex; align-items: center; justify-content: center; gap: var(--space-2);
  color: var(--muted); border-radius: var(--radius-lg); font-size: var(--text-sm);
  background: linear-gradient(90deg, rgba(var(--primary-rgb),.06) 25%, rgba(var(--primary-rgb),.12) 50%, rgba(var(--primary-rgb),.06) 75%);
  background-size: 200% 100%;
  animation: routeMapShimmer 1.5s var(--ease-in-out) infinite;
}
@keyframes routeMapShimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.route-map:hover { box-shadow: var(--shadow-md); }
@media (max-width: 640px) { .route-map { height: clamp(200px, 45vh, 300px); } }

/* Route leg pill */
.route-leg-info { background: var(--bg-alt); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); transition: background .3s var(--ease-out); }

/* Route loading shimmer */
.route-loading { opacity: .6; animation: routePulse 1.5s var(--ease-in-out) infinite; }
@keyframes routePulse { 0%, 100% { opacity: .6; } 50% { opacity: 1; } }
/* Route total: prominent floating summary badge, pinned right */
.route-total {
  display: inline-block;
  margin: 0 0 var(--space-3);
  font-size: var(--text-sm);
  color: var(--primary-fg);
  font-weight: var(--weight-bold);
  padding: var(--space-2) var(--space-4);
  background: var(--card);
  border: 1.5px solid rgba(var(--primary-rgb), .35);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-xs);
  transition: background .3s var(--ease-out), box-shadow .3s var(--ease-out);
}
/* Error variant: warm, designed messaging */
.route-total[role="status"] {
  color: var(--accent-text);
  border-color: rgba(var(--accent-rgb), .35);
  font-weight: var(--weight-semibold);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.route-total[role="status"] .chip { font-weight: var(--weight-semibold); }
.dark .route-total { background: rgba(255,255,255,.04); border-color: rgba(var(--primary-rgb), .4); }

/* Dark mode */
.dark .step-card { border-color: var(--line); }
.dark .step-card:hover { box-shadow: var(--shadow-lg); border-color: rgba(255,255,255,.1); }
.dark .route-leg-line { background: rgba(255,255,255,.1); }
.dark .route-leg-info { background: rgba(255,255,255,.04); }
.dark .route-map { border-color: var(--line); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .step-card:hover { transform: none; }
  .step-card:active { transform: none; }
  .step-card:hover .step-emoji { transform: none; }
  .step:hover::before { transform: none; }
  .itin-actions .btn:hover { transform: none; }
  .itin-actions .btn:active { transform: none; }
  .transport-mode .chip:hover { transform: none; }
  .transport-mode .chip:active { transform: none; }
  .route-loading { animation: none; }
  .route-map-loading { animation: none; background: var(--bg-alt); }
  .day-arc-track { animation: none; transform: none; }
  .day-arc-dot { animation: none; }
  .day-arc-dot:hover { transform: translateX(-50%); }
}
@media (max-width: 640px) {
  .day-arc-legend { display: none; }
  .day-arc-hero { height: 44px; }
}
@media print {
  .itin-actions, .transport-mode-spaced, .route-map-section, .day-arc-hero { display: none; }
  .step-card { box-shadow: none; border: 1px solid #ccc; break-inside: avoid; }
  .step-card:hover { transform: none; }
  .timeline { padding-left: var(--space-4); }
  .timeline::before { background: #999; }
  .timeline-chapter { break-after: avoid; }
  .step-note-callout { background: none; border-left: 2px solid #999; }
}
</style>
