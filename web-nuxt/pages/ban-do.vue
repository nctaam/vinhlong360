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
      <div class="map-filters reveal" role="group" aria-label="Lọc theo loại địa điểm">
        <button type="button" v-for="f in typeFilters" :key="f.value" :class="['chip', { active: activeTypes.has(f.value) }]" :aria-pressed="activeTypes.has(f.value)" @click="toggleType(f.value)">
          {{ f.label }}
        </button>
      </div>
    </ClientOnly>

    <ClientOnly>
      <p v-if="!activeTypes.has('all') && visibleCount === 0 && !mapLoadError && !fetchError" class="map-empty-notice" role="status" style="text-align:center; padding:var(--space-3); color:var(--muted); font-size:var(--text-sm)">
        Chưa có địa điểm nào thuộc loại này trên bản đồ. Thử bỏ bớt bộ lọc nhé.
      </p>
    </ClientOnly>
    <div v-if="fetchError" class="fetch-error">
      <EmptyState message="Không thể tải dữ liệu bản đồ." icon="🗺️">
        <template #actions>
          <button type="button" class="btn btn-outline btn-sm" @click="$router.go(0)">Tải lại trang</button>
          <NuxtLink to="/" class="btn btn-ghost btn-sm">Về trang chủ</NuxtLink>
        </template>
      </EmptyState>
    </div>
    <div v-if="mapLoadError" class="fetch-error">
      <EmptyState message="Không tải được bản đồ. Vui lòng kiểm tra kết nối và thử lại." icon="🗺️" tone="error">
        <template #actions>
          <button type="button" class="btn btn-outline btn-sm" @click="$router.go(0)">Tải lại trang</button>
        </template>
      </EmptyState>
    </div>
    <ClientOnly>
      <div ref="mapEl" id="mapContainer"></div>
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
  { value: 'all', label: 'Tất cả' },
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
  updateMarkers()
}

const mapEl = ref<HTMLElement | null>(null)
const { createMap } = useNDAMap()

const { data, error: fetchError } = await useAsyncData('map-entities', () =>
  $fetch<{ entities: Entity[] }>('/api/entities?limit=700')
)

let mapInited = false
let mapRef: unknown = null  // GĐ10.2: tham chiếu map để cập nhật source khi lọc

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

// GĐ10.2: dựng GeoJSON từ entity đã lọc (thay 700 DOM marker bằng nguồn GeoJSON + clustering).
const visibleCount = ref(0)
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
  // Lọc theo type = nạp lại dữ liệu nguồn (clustering tự dựng lại).
  mapRef?.getSource?.('entities')?.setData(buildGeoJSON())
}

const mapLoadError = ref(false)
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
  const loadTimer = setTimeout(() => { if (!map.isStyleLoaded()) mapLoadError.value = true }, 15000)
  map.on('load', () => { clearTimeout(loadTimer); mapLoadError.value = false })

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
      new maplibregl.Popup({ offset: 12 })
        .setLngLat(f.geometry.coordinates)
        .setHTML(`<strong>${esc(p.emoji)} ${esc(p.name)}</strong><br><small>${esc(p.label)}</small><br><a href="/dia-diem/${esc(p.id)}">Xem chi tiết →</a>`)
        .addTo(map)
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
      new maplibregl.Popup({ offset: 12 }).setLngLat([flng, flat])
        .setHTML(`<strong>${esc(m.emoji || '📍')} ${esc(nm)}</strong>${fent ? `<br><small>${esc(m.label || fent.type)}</small>` : ''}`)
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
    }),
  }],
})
</script>

<style scoped>
#mapContainer { height: 65vh; min-height: 400px; border-radius: var(--radius-lg, 16px); overflow: hidden; box-shadow: var(--shadow-md); border: .5px solid var(--line); transition: box-shadow .35s var(--ease-out-expo); }
#mapContainer:hover { box-shadow: var(--shadow-lg); }
.map-fallback { display: flex; align-items: center; justify-content: center; background: var(--bg-alt); }
.map-filters { margin-bottom: var(--space-4); }

/* Dark mode */
.dark #mapContainer { border-color: var(--line); box-shadow: var(--shadow-lg); }
</style>
