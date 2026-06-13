<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Bản đồ' }]" />
    <div class="page-head">
      <h1>Bản đồ</h1>
      <p>Xem tất cả điểm đến trên bản đồ.</p>
    </div>

    <ClientOnly>
      <div class="map-filters">
        <button v-for="f in typeFilters" :key="f.value" :class="['chip', { active: activeTypes.has(f.value) }]" @click="toggleType(f.value)">
          {{ f.label }}
        </button>
      </div>
    </ClientOnly>

    <p v-if="fetchError" style="color: #D94F3D; text-align: center; padding: 20px">Không thể tải dữ liệu bản đồ. Vui lòng thử lại.</p>
    <ClientOnly>
      <div ref="mapEl" id="mapContainer"></div>
      <template #fallback>
        <div id="mapContainer" style="display: flex; align-items: center; justify-content: center">
          <div class="spinner"></div>
        </div>
      </template>
    </ClientOnly>
  </section>
</template>

<script setup lang="ts">
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
  $fetch<any>('/api/entities?limit=700')
)

let mapInited = false
let allMarkers: { marker: any; type: string }[] = []

function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

function updateMarkers() {
  const show = activeTypes.value
  for (const { marker, type } of allMarkers) {
    const el = marker.getElement()
    if (show.has('all') || show.has(type)) {
      el.style.display = ''
    } else {
      el.style.display = 'none'
    }
  }
}

watch(mapEl, async (el) => {
  if (!el || mapInited) return
  mapInited = true

  const { map, maplibregl } = await createMap(el)

  function addMarkers() {
    const entities = data.value?.entities || []
    for (const e of entities) {
      const coords = normalizeCoords(e.coordinates ?? e.coords)
      if (!coords) continue
      const [lat, lng] = coords
      const meta = TYPE_META[e.type] || { emoji: '📍' }
      const color = MARKER_COLORS[e.type] || '#9C3D22'

      const popup = new maplibregl.Popup({ offset: 25 }).setHTML(
        `<strong>${esc(meta.emoji)} ${esc(e.name)}</strong><br><small>${esc(meta.label || e.type)}</small><br><a href="/dia-diem/${esc(e.id)}">Xem chi tiết →</a>`
      )

      const marker = new maplibregl.Marker({ color })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(map)

      allMarkers.push({ marker, type: e.type })
    }
  }

  addMarkers()
})

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
