<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Bản đồ' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-map">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🗺️</span>
        <div>
          <h1>Bản đồ</h1>
          <p>Khám phá trực quan hơn 500 điểm đến trên bản đồ tương tác — lọc theo loại hình để tìm nhanh.</p>
        </div>
      </div>
    </section>

    <ClientOnly>
      <div class="controls map-filters reveal">
        <div class="chip-row" role="group" aria-label="Lọc theo loại địa điểm">
          <button type="button" v-for="f in typeFilters" :key="f.value" :class="['chip', { active: activeTypes.has(f.value) }]" :aria-pressed="activeTypes.has(f.value)" @click="toggleType(f.value)">
            {{ f.label }}
          </button>
        </div>
        <p class="result-meta" aria-live="polite">
          {{ visibleLabel }}
        </p>
      </div>
    </ClientOnly>

    <ClientOnly>
      <div v-if="!activeTypes.has('all') && visibleCount === 0 && !mapLoadError && !fetchError" class="block map-empty-block">
        <EmptyState
          icon="🗺️"
          title="Chưa có địa điểm nào"
          message="Không có địa điểm thuộc loại đang lọc trên bản đồ. Thử bỏ bớt bộ lọc để xem thêm."
        >
          <template #actions>
            <button type="button" class="btn btn-outline btn-sm" @click="toggleType('all')">Xem tất cả</button>
          </template>
        </EmptyState>
      </div>
    </ClientOnly>
    <div v-if="fetchError" class="block fetch-error">
      <EmptyState title="Không tải được dữ liệu" message="Không thể tải dữ liệu bản đồ. Vui lòng kiểm tra kết nối và thử lại." icon="🗺️" tone="error">
        <template #actions>
          <button type="button" class="btn btn-outline btn-sm" @click="$router.go(0)">Tải lại trang</button>
          <NuxtLink to="/" class="btn btn-ghost btn-sm">Về trang chủ</NuxtLink>
        </template>
      </EmptyState>
    </div>
    <div v-if="mapLoadError" class="block fetch-error">
      <EmptyState title="Không tải được bản đồ" message="Bản đồ không thể tải — có thể do kết nối mạng hoặc máy chủ bản đồ. Vui lòng thử lại." icon="🗺️" tone="error">
        <template #actions>
          <button type="button" class="btn btn-outline btn-sm" @click="retryMapLoad">Thử lại</button>
          <NuxtLink to="/" class="btn btn-ghost btn-sm">Về trang chủ</NuxtLink>
        </template>
      </EmptyState>
    </div>
    <ClientOnly>
      <p class="sr-only" id="map-instructions">Sử dụng phím +/- để phóng to/thu nhỏ. Kéo chuột hoặc dùng phím mũi tên để di chuyển bản đồ. Nhấp vào điểm đánh dấu để xem thông tin chi tiết.</p>
      <div ref="mapEl" id="mapContainer" v-show="!mapLoadError && !fetchError" role="application" aria-label="Bản đồ tương tác du lịch Vĩnh Long" aria-describedby="map-instructions" tabindex="0"></div>
      <div aria-live="polite" class="sr-only">{{ popupAnnouncement }}</div>
      <template #fallback>
        <div id="mapContainer" class="map-fallback" role="status" aria-label="Đang tải bản đồ">
          <div class="spinner"></div>
        </div>
      </template>
    </ClientOnly>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'

const MARKER_COLORS: Record<string, string> = {
  experience: '#2D7D46',
  attraction: '#9C3D22',
  nature: '#1A7A5C',
  history: '#8B5E3C',
  craft_village: '#B8860B',
  dish: '#D94F3D',
  product: '#E67E22',
  accommodation: '#4A6FA5',
  event: '#7B2D8E',
  organization: '#555',
}

const typeFilters = [
  { value: 'all', label: '🌐 Tất cả' },
  { value: 'attraction', label: '🛕 Tham quan' },
  { value: 'experience', label: '🌾 Trải nghiệm' },
  { value: 'nature', label: '🌿 Thiên nhiên' },
  { value: 'history', label: '🏛️ Lịch sử' },
  { value: 'dish', label: '🍲 Ẩm thực' },
  { value: 'craft_village', label: '🏺 Làng nghề' },
  { value: 'accommodation', label: '🏡 Lưu trú' },
  { value: 'product', label: '🍊 Đặc sản' },
]

const route = useRoute()
const activeTypes = ref(new Set(['all']))

let updateRaf: number | null = null
function toggleType(type: string) {
  if (type === 'all') {
    activeTypes.value = new Set(['all'])
  } else {
    const next = new Set(activeTypes.value)
    next.delete('all')
    if (next.has(type)) next.delete(type)
    else next.add(type)
    if (next.size === 0) next.add('all')
    activeTypes.value = next
  }
  if (updateRaf) cancelAnimationFrame(updateRaf)
  updateRaf = requestAnimationFrame(() => { updateRaf = null; updateMarkers() })
}

const mapEl = ref<HTMLElement | null>(null)
const { createMap } = useNDAMap()

const { data, error: fetchError } = await useAsyncData('map-entities', () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?limit=700')
)

let mapInited = false
let mapRef: unknown = null  // GĐ10.2: tham chiếu map để cập nhật source khi lọc

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// GĐ-UX: popup có bố cục flex + viền trái theo màu loại điểm (etype) cho cảm giác premium.
// Inputs phải đã esc() trước khi truyền vào (color là literal hex an toàn).
function popupHTML(emoji: string, name: string, label: string, color: string, id: string) {
  const labelLine = label ? `<small style="display:block;color:var(--muted,#666);margin-top:2px">${label}</small>` : ''
  const linkLine = id ? `<a href="/dia-diem/${id}" style="display:inline-block;margin-top:6px;font-weight:600">Xem chi tiết →</a>` : ''
  return `<div style="display:flex;gap:8px;border-left:4px solid ${color};padding-left:8px"><div style="font-size:1.15rem;line-height:1.2">${emoji}</div><div style="min-width:0"><strong style="display:block">${name}</strong>${labelLine}${linkLine}</div></div>`
}

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

// GĐ10.2: dựng GeoJSON từ entity đã lọc (thay 700 DOM marker bằng nguồn GeoJSON + clustering).
const visibleCount = ref(0)
const visibleLabel = computed(() =>
  activeTypes.value.has('all')
    ? `${visibleCount.value} địa điểm`
    : `${visibleCount.value} địa điểm phù hợp`
)
function buildGeoJSON() {
  const show = activeTypes.value
  const features: Record<string, unknown>[] = []
  for (const e of (data.value?.entities || [])) {
    if (!(show.has('all') || show.has(e.type))) continue
    const coords = normalizeCoords(e.coordinates)
    if (!coords) continue
    const [lat, lng] = coords
    const meta = TYPE_META[e.type] || { emoji: '📍' }
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: {
        id: e.id, name: e.name, etype: e.type,
        emoji: meta.emoji, label: meta.label || e.type,
        color: MARKER_COLORS[e.type] || '#9C3D22',
      },
    })
  }
  visibleCount.value = features.length
  return { type: 'FeatureCollection', features }
}

function updateMarkers() {
  const src = mapRef?.getSource?.('entities')
  if (src) src.setData(buildGeoJSON())
}

// Seed result-meta đếm số điểm ngay khi có dữ liệu (trước khi map style load xong),
// tránh nháy "0 địa điểm" trong pill. Chỉ chạy client (pill nằm trong ClientOnly).
onMounted(() => { buildGeoJSON() })

const popupAnnouncement = ref('')
const mapLoadError = ref(false)
let loadTimer: ReturnType<typeof setTimeout> | null = null

function retryMapLoad() {
  if (loadTimer) { clearTimeout(loadTimer); loadTimer = null }
  mapLoadError.value = false
  mapInited = false
  mapRef = null
  // Re-trigger the watcher by toggling the ref
  const el = mapEl.value
  if (el) {
    mapEl.value = null
    nextTick(() => { mapEl.value = el })
  }
}

watch(mapEl, async (el) => {
  if (!el || mapInited) return
  mapInited = true

  let map: any, maplibregl: any
  try {
    const r = await createMap(el)
    map = r.map
    maplibregl = r.maplibregl
  } catch {
    mapLoadError.value = true
    return
  }
  mapRef = map
  // Fallback if the style/tiles never load (bad key, host down, offline). Generous
  // timeout for slow rural connections; self-clears the moment the map loads.
  if (loadTimer) clearTimeout(loadTimer)
  loadTimer = setTimeout(() => { loadTimer = null; if (!map.isStyleLoaded()) mapLoadError.value = true }, 15000)
  map.on('load', () => { if (loadTimer) { clearTimeout(loadTimer); loadTimer = null }; mapLoadError.value = false })

  function addClusterLayers() {
    if (map.getSource('entities')) return
    map.addSource('entities', {
      type: 'geojson',
      data: buildGeoJSON(),
      cluster: true,
      clusterMaxZoom: 14,
      clusterRadius: 50,
    })
    map.addLayer({
      id: 'clusters', type: 'circle', source: 'entities', filter: ['has', 'point_count'],
      paint: {
        'circle-color': '#9C3D22',
        'circle-opacity': 0.85,
        'circle-radius': ['step', ['get', 'point_count'], 16, 10, 22, 50, 30],
      },
    })
    map.addLayer({
      id: 'cluster-count', type: 'symbol', source: 'entities', filter: ['has', 'point_count'],
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
      paint: { 'text-color': '#ffffff' },
    })
    map.addLayer({
      id: 'unclustered', type: 'circle', source: 'entities', filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': ['get', 'color'],
        'circle-radius': 7,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff',
      },
    })

    map.on('click', 'clusters', (ev: { features?: { properties: Record<string, unknown> }[] }) => {
      const f = map.queryRenderedFeatures(ev.point, { layers: ['clusters'] })[0]
      if (!f) return
      ;(map.getSource('entities') as { getClusterExpansionZoom: Function }).getClusterExpansionZoom(f.properties.cluster_id, (err: Error | null, zoom: number) => {
        if (err) return
        map.easeTo({ center: f.geometry.coordinates, zoom })
      })
    })
    map.on('click', 'unclustered', (ev: { features?: { properties: Record<string, unknown> }[] }) => {
      const f = ev.features?.[0]
      if (!f) return
      const p = f.properties
      const pColor = MARKER_COLORS[p.etype as string] || (p.color as string) || '#9C3D22'
      new maplibregl.Popup({ offset: 12 })
        .setLngLat(f.geometry.coordinates)
        .setHTML(popupHTML(esc(p.emoji), esc(p.name), esc(p.label), pColor, esc(p.id)))
        .addTo(map)
      // Announce popup content to screen readers
      popupAnnouncement.value = `${p.name}, ${p.label}. Nhấn Enter để xem chi tiết.`
    })
    for (const lid of ['clusters', 'unclustered']) {
      map.on('mouseenter', lid, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', lid, () => { map.getCanvas().style.cursor = '' })
    }

    // Focus 1 điểm khi đến từ trang chi tiết (?id hoặc ?lat&lng) — thay vì chỉ hiện bản đồ chung
    const fid = route.query.id as string | undefined
    let flat = parseFloat(route.query.lat as string)
    let flng = parseFloat(route.query.lng as string)
    const fent = fid ? (data.value?.entities || []).find((e: Entity) => e.id === fid) : null
    if (fent) { const c = normalizeCoords(fent.coordinates ?? fent.coords); if (c) { flat = c[0]; flng = c[1] } }
    if (isFinite(flat) && isFinite(flng)) {
      map.flyTo({ center: [flng, flat], zoom: 15 })
      const m: any = fent ? (TYPE_META[fent.type] || { emoji: '📍' }) : { emoji: '📍' }
      const nm = fent ? fent.name : 'Địa điểm'
      const fColor = fent ? (MARKER_COLORS[fent.type] || '#9C3D22') : '#9C3D22'
      new maplibregl.Popup({ offset: 12 }).setLngLat([flng, flat])
        .setHTML(popupHTML(esc(m.emoji || '📍'), esc(nm), fent ? esc(m.label || fent.type) : '', fColor, fent ? esc(fent.id) : ''))
        .addTo(map)
    }
  }

  if (map.isStyleLoaded()) addClusterLayers()
  else map.on('load', addClusterLayers)
})

useReveal()

useSeoMeta({
  title: 'Bản đồ du lịch Vĩnh Long — vinhlong360',
  description: 'Bản đồ tương tác hiển thị tất cả điểm du lịch, đặc sản, lưu trú, làng nghề tại Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: 'Bản đồ du lịch — vinhlong360',
  ogDescription: 'Xem tất cả điểm đến trên bản đồ tương tác.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/ban-do') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: 'Bản đồ du lịch vinhlong360',
      description: 'Bản đồ tương tác hiển thị điểm du lịch, đặc sản, lưu trú và làng nghề tại Vĩnh Long, Bến Tre, Trà Vinh.',
      url: canonicalUrl('/ban-do'),
      spatialCoverage: {
        '@type': 'Place',
        name: 'Vĩnh Long – Bến Tre – Trà Vinh',
        geo: {
          '@type': 'GeoShape',
          box: '9.8 105.8 10.4 106.7',
        },
      },
    }),
  }],
})

onBeforeUnmount(() => {
  if (updateRaf) cancelAnimationFrame(updateRaf)
  if (loadTimer) { clearTimeout(loadTimer); loadTimer = null }
  if (mapRef && typeof (mapRef as any).remove === 'function') (mapRef as any).remove()
  mapRef = null
})
</script>

<style scoped>
#mapContainer {
  height: 65vh; height: 65dvh; min-height: 400px;
  border-radius: var(--radius-lg, 16px);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: .5px solid var(--line);
  transition: box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-out-expo);
  will-change: transform;
}
#mapContainer:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
/* Refined elevation: stacked brand-tinted + ambient depth shadow with a hair of lift. */
#mapContainer:hover {
  box-shadow:
    0 8px 28px -8px rgba(var(--primary-rgb), .28),
    0 20px 48px -20px rgba(0, 0, 0, .35);
  transform: scale(1.005);
}

/* Designed loading state: card-like surface with radial brand wash, matching
   the .block .empty-state aesthetic so the wait moment feels intentional. */
.map-fallback {
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .06), transparent 60%),
    var(--bg-alt);
  border: .5px solid var(--line);
}
.dark .map-fallback {
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .08), transparent 60%),
    var(--bg-alt);
}

/* Controls panel spacing for the filter/result row. */
.map-filters { margin-bottom: var(--space-4); }

/* Dark mode: keep a visible hairline + deeper ambient hover shadow. */
.dark #mapContainer { border-color: var(--line); box-shadow: var(--shadow-lg); }
.dark #mapContainer:hover {
  box-shadow:
    0 8px 28px -8px rgba(var(--primary-rgb), .34),
    0 22px 52px -20px rgba(0, 0, 0, .6);
}

/* Reduced motion: no scale/transform on hover; keep the elevation cue. */
/* Mobile: reduce min-height so the map doesn't push controls off-screen on small viewports */
@media (max-width: 640px) {
  #mapContainer { min-height: 300px; height: 55vh; }
}

@media (prefers-reduced-motion: reduce) {
  #mapContainer { transition: box-shadow .35s var(--ease-out-expo); will-change: auto; }
  #mapContainer:hover { transform: none; }
}

</style>
