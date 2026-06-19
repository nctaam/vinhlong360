<template>
  <section v-if="itinerary" class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: itinerary.title || itinerary.name }]" />

    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🗓️</span>
        <div>
          <h1>{{ itinerary.title || itinerary.name }}</h1>
          <p>{{ areaMeta.emoji }} {{ areaMeta.name }} · {{ itinerary.duration }} · {{ itinerary.stops?.length || 0 }} điểm dừng</p>
        </div>
      </div>
    </section>
    <p class="lead lead-flush">{{ itinerary.summary || itinerary.description || '' }}</p>

    <div class="itin-actions">
      <ClientOnly>
        <ShareButton :title="itinerary.title || itinerary.name" :text="itinerary.summary || itinerary.description" />
      </ClientOnly>
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline btn-sm">+ Tự tạo lịch trình</NuxtLink>
    </div>

    <!-- Transport mode + total -->
    <ClientOnly>
      <div v-if="stopsWithCoords.length >= 2" class="transport-mode transport-mode-spaced">
        <span class="tm-label">Phương tiện:</span>
        <button type="button" v-for="m in transportModes" :key="m.value" :class="['chip', { active: transportMode === m.value }]" @click="switchMode(m.value)">
          {{ m.icon }} {{ m.label }}
        </button>
        <div v-if="routeResult" class="route-total">
          {{ formatDistance(routeResult.totalDistance) }} · {{ formatDuration(routeResult.totalDuration) }}
        </div>
        <div v-if="routeLoading" class="route-total route-loading">Đang tính...</div>
      </div>
    </ClientOnly>

    <ol class="timeline">
      <template v-for="(stop, idx) in (itinerary.stops || [])" :key="stop.id || idx">
        <li class="step">
          <span class="step-time">{{ stop.time || '' }}</span>
          <div :class="['step-card', stop.type ? `cat-${catClass(stop.type)}` : '']">
            <span class="step-emoji">{{ typeEmoji(stop.type) }}</span>
            <div class="step-content">
              <h3>
                <NuxtLink v-if="stop.id" :to="`/dia-diem/${stop.id}`" class="stop-link">{{ stop.name || stop.id }}</NuxtLink>
                <span v-else>{{ stop.name || 'Điểm dừng' }}</span>
              </h3>
              <span v-if="stop.type" class="step-type-label">{{ typeLabel(stop.type) }}</span>
              <p v-if="stop.summary" class="summary">{{ stop.summary }}</p>
              <p v-if="stop.note" class="step-note">{{ stop.note }}</p>
            </div>
          </div>
        </li>
        <!-- Route leg info between stops -->
        <li v-if="idx < (itinerary.stops || []).length - 1 && routeLegs[idx]" class="route-leg" :key="'leg-' + idx">
          <div class="route-leg-line"></div>
          <div class="route-leg-info">
            {{ formatDistance(routeLegs[idx].distance) }} · {{ formatDuration(routeLegs[idx].duration) }}
          </div>
        </li>
      </template>
    </ol>

    <!-- Route map -->
    <ClientOnly>
      <div v-if="stopsWithCoords.length >= 2" class="route-map-section reveal">
        <h3>Bản đồ lộ trình</h3>
        <div ref="routeMapEl" class="route-map"></div>
      </div>
    </ClientOnly>

    <!-- Related itineraries -->
    <div class="reveal">
      <NuxtErrorBoundary>
        <ClientOnly>
          <AIRecommendations v-if="itinerary.area" title="Khám phá thêm" :limit="4" />
        </ClientOnly>
      </NuxtErrorBoundary>
    </div>
  </section>
  <div v-else class="page">
    <EmptyState message="Không tìm thấy lịch trình." />
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { fetchRoute, formatDistance, formatDuration, type TransportMode, type RouteResult, type RouteLeg } from '~/composables/useRouting'

useReveal()

const route = useRoute()
const id = route.params.id as string

const { data: itinerary, error: fetchError } = await useAsyncData(`itinerary-${id}`, () =>
  $fetch<any>(`/api/itineraries/${id}`)
)

if (fetchError.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy lịch trình' })
}

const areaMeta = computed(() => AREA_META[itinerary.value?.area] || { emoji: '📍', name: itinerary.value?.area || '' })

function typeEmoji(type: string) {
  return TYPE_META[type]?.emoji || '📍'
}

function typeLabel(type: string) {
  return TYPE_META[type]?.label || type
}

function catClass(type: string) {
  return TYPE_META[type]?.cat || 'place'
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
    if (stopIdx !== undefined) {
      map[stopIdx] = routeResult.value.legs[i]
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

function extractCoords(raw: any): [number, number] | undefined {
  let c = raw
  if (!c) return undefined
  if (typeof c === 'string') { try { c = JSON.parse(c) } catch { return undefined } }
  if (Array.isArray(c) && c.length >= 2) return [c[0], c[1]]
  if (c.lat && c.lng) return [c.lat, c.lng]
  return undefined
}

function loadCoords() {
  const stops = itinerary.value?.stops
  if (!stops?.length) return

  const results: StopCoord[] = []
  for (let i = 0; i < stops.length; i++) {
    const s = stops[i]
    const coords = extractCoords(s.coordinates)
    if (coords) {
      results.push({ name: s.name || s.id, idx: i, coords })
    }
  }

  stopsWithCoords.value = results
}

async function computeRoute() {
  const coords = stopsWithCoords.value.map(s => s.coords)
  if (coords.length < 2) { routeResult.value = null; return }

  routeLoading.value = true
  routeResult.value = await fetchRoute(coords, transportMode.value)
  routeLoading.value = false
  renderMap(routeResult.value)
}

function switchMode(mode: TransportMode) {
  transportMode.value = mode
  computeRoute()
}

async function renderMap(result: RouteResult | null) {
  if (!import.meta.client || !routeMapEl.value) return

  if (!mapInstance) {
    const res = await createNDAMap(routeMapEl.value)
    mapInstance = res.map
    maplibre = res.maplibregl
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
      .setPopup(new maplibre.Popup({ offset: 25 }).setHTML(`<strong>${num}. ${s.name}</strong>`))
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
        (b: any, c: number[]) => b.extend(c),
        new maplibre.LngLatBounds(coords[0], coords[0])
      )
      mapInstance.fitBounds(bounds, { padding: 40 })
    } else {
      const coords = stops.map(s => [s.coords[1], s.coords[0]])
      const bounds = coords.reduce(
        (b: any, c: number[]) => b.extend(c),
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
      itemListElement: it.stops.map((s: any, i: number) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: s.name || s.id,
      })),
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

<style scoped>
.itin-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; margin: var(--space-4) 0; }
.itin-actions .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.itin-actions .btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.itin-actions .btn:active { transform: scale(.95); transition-duration: .08s; }

.transport-mode-spaced { margin-bottom: var(--space-4); }
.transport-mode .chip { transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), background .3s var(--ease-out), border-color .3s var(--ease-out); }
.transport-mode .chip:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.transport-mode .chip:active { transform: scale(.95); transition-duration: .08s; }

.timeline { list-style: none; padding: 0; margin: 0; }
.step { position: relative; }
.step-card { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-4); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-xs); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.step-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.step-card:active { transform: scale(.97); transition-duration: .08s; }
.step-emoji { font-size: var(--text-xl); transition: transform .35s var(--ease-spring-gentle); }
.step-card:hover .step-emoji { transform: scale(1.1) rotate(-3deg); }
.stop-link { color: var(--ink); font-weight: var(--weight-semibold); transition: color .3s var(--ease-out); border-radius: var(--radius-sm); }
.stop-link:hover { color: var(--primary-fg); }
.stop-link:active { opacity: .7; }
.stop-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

.route-leg { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) 0 var(--space-2) var(--space-6); }
.route-leg-line { width: 2px; height: 20px; background: var(--line); border-radius: 1px; transition: background .3s var(--ease-out); }
.route-leg-info { font-size: var(--text-xs); color: var(--muted); }

.route-map-section { margin-top: var(--space-6); }
.route-map-section h3 { font-size: var(--text-lg); font-weight: var(--weight-semibold); margin-bottom: var(--space-3); }
.route-map { height: 400px; border-radius: var(--radius-lg); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); transition: box-shadow .35s var(--ease-out-expo); }
.route-map:hover { box-shadow: var(--shadow-md); }

/* Route leg pill */
.route-leg-info { background: var(--bg-alt); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); transition: background .3s var(--ease-out); }

/* Route loading shimmer */
.route-loading { opacity: .6; animation: routePulse 1.5s ease-in-out infinite; }
@keyframes routePulse { 0%, 100% { opacity: .6; } 50% { opacity: 1; } }
.route-total { font-size: var(--text-sm); color: var(--ink-secondary); font-weight: var(--weight-semibold); padding: var(--space-1) var(--space-3); background: var(--bg-alt); border-radius: var(--radius-full); transition: background .3s var(--ease-out); }

/* Dark mode */
.dark .step-card { border-color: var(--line); }
.dark .step-card:hover { box-shadow: var(--shadow-lg); border-color: rgba(255,255,255,.1); }
.dark .route-leg-line { background: rgba(255,255,255,.1); }
.dark .route-leg-info { background: rgba(255,255,255,.04); }
.dark .route-total { background: rgba(255,255,255,.04); }
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
}
</style>
