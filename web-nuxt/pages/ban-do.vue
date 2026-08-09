<template>
  <section class="page" data-color-system="tri-region-v1" data-page-recipe="map">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Bản đồ' }]" />

    <section class="catalog-hero cat-map">
      <div class="catalog-hero-inner map-hero-inner">
        <span class="dateline-eyebrow">Bản đồ sống · Vĩnh Long · Bến Tre · Trà Vinh</span>
        <h1>Bản đồ</h1>
        <p>So sánh vị trí bằng bản đồ, đối chiếu bằng danh sách và địa chỉ ngay cả khi tile không tải.</p>
      </div>
    </section>

    <p v-if="searchView.hasMalformedUrl.value" class="search-state-notice" role="status">
      {{ searchView.malformedNotice.value }}
    </p>

    <ClientOnly>
      <div class="controls map-filters reveal">
        <FilterChips
          :filters="typeFilterOptions"
          :model-value="activeTypeArray"
          aria-label="Lọc theo loại địa điểm"
          @update:model-value="onTypeFilterChange"
        />
        <p class="result-meta" aria-live="polite">{{ visibleLabel }}</p>
      </div>
    </ClientOnly>

    <PageState v-if="status === 'pending' && !mapPins.length" :state="{ kind: 'loading' }" />
    <PageState
      v-else-if="fetchError"
      :state="{ kind: 'error', retry: { label: 'Tải lại dữ liệu' }, fallback: mapPins }"
      title="Không tải được dữ liệu địa điểm"
      :retry="retryData"
    >
      <MapListSurface
        v-if="mapResults.length"
        :results="mapResults"
        :selected-id="searchView.state.value.selectedId"
        :viewport="searchView.state.value.viewport"
        map-state="partial"
        :panel="searchView.state.value.panel"
        :scroll-key="searchView.state.value.scrollKey"
        @select="searchView.selectResult"
        @viewport-change="searchView.setViewport"
        @search-area="commitSearchArea"
        @panel-change="searchView.openPanel"
        @scroll-key-change="searchView.setScrollKey"
      />
    </PageState>
    <MapListSurface
      v-else
      :results="mapResults"
      :selected-id="searchView.state.value.selectedId"
      :viewport="searchView.state.value.viewport"
      :map-state="mapNetworkState"
      :panel="searchView.state.value.panel"
      :scroll-key="searchView.state.value.scrollKey"
      @select="searchView.selectResult"
      @viewport-change="searchView.setViewport"
      @search-area="commitSearchArea"
      @panel-change="searchView.openPanel"
      @scroll-key-change="searchView.setScrollKey"
    />
    <p v-if="scopeAnnouncement" class="sr-only" aria-live="polite">{{ scopeAnnouncement }}</p>
  </section>
</template>

<script setup lang="ts">
import MapListSurface from '~/components/public/MapListSurface.vue'
import PageState from '~/components/public/PageState.vue'
import type { Entity } from '~/types'
import type { MapViewport } from '~/types/publicExperience'
import { normalizeCoords } from '~/composables/useCoords'
import { viewportTileBounds } from '~/utils/publicStateUrl'

type MapListResult = Entity & {
  lat?: number | string
  lng?: number | string
  category_color?: string
  emoji?: string
}

type MapPin = MapListResult & {
  lat: number | string
  lng: number | string
  category_color?: string
  emoji?: string
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

const allowedTypes = new Set(typeFilters.map(filter => filter.value))
const route = useRoute()
const router = useRouter()
const searchView = useSearchViewState()
const { favorites } = useFavorites()
const mapNetworkState = ref<'ready' | 'offline'>('ready')
const scopeAnnouncement = ref('')

function filterTypes(value: unknown) {
  const values = Array.isArray(value) ? value : typeof value === 'string' ? value.split(',') : []
  const filtered = values.map(item => String(item).trim()).filter(item => allowedTypes.has(item) && item !== 'all')
  return filtered.length ? [...new Set(filtered)] : ['all']
}

const activeTypeArray = computed(() => filterTypes(searchView.state.value.filters.type))
const activeTypeQuery = computed(() => activeTypeArray.value.includes('all') ? '' : activeTypeArray.value.join(','))
const savedMode = computed(() => String(route.query.source || '').toLowerCase() === 'saved')
const mapSearchQuery = computed(() => searchView.state.value.query.trim().toLocaleLowerCase('vi-VN'))
const areaQuery = computed(() => searchView.state.value.area?.id || '')
const savedPinIds = computed(() => new Set(
  favorites.value.map((item: { id?: unknown }) => String(item?.id || '').trim()).filter(Boolean),
))

type MapFilterOption = { key: string; label: string; icon?: string }
const typeFilterOptions: MapFilterOption[] = typeFilters.map((filter) => {
  const parts = filter.label.match(/^(\S+)\s+(.+)$/)
  return parts ? { key: filter.value, label: parts[2] || filter.label, icon: parts[1] || undefined } : { key: filter.value, label: filter.label }
})

function onTypeFilterChange(values: string[]) {
  const current = activeTypeArray.value
  if (!values.length || (values.includes('all') && !current.includes('all'))) {
    searchView.setFilter('type', undefined)
    return
  }
  const filtered = values.filter(value => value !== 'all' && allowedTypes.has(value))
  searchView.setFilter('type', filtered.length ? filtered : undefined)
}

const mapPinApiPath = computed(() => {
  const params = new URLSearchParams()
  if (activeTypeQuery.value) params.set('type', activeTypeQuery.value)
  if (areaQuery.value) params.set('area', areaQuery.value)
  const query = params.toString()
  return `/api/map-pins${query ? `?${query}` : ''}`
})

const { data, error: fetchError, status, refresh } = await useAsyncData(
  computed(() => `map-pins-${activeTypeQuery.value || 'all'}-${areaQuery.value || 'all'}`),
  () => apiFetch<MapPin[]>(mapPinApiPath.value),
  { watch: [mapPinApiPath] },
)
const retryData = () => refresh()

const mapPins = computed(() => Array.isArray(data.value) ? data.value : [])
const committedBounds = computed(() => searchView.committedViewport.value ? viewportTileBounds(searchView.committedViewport.value) : undefined)
const filteredPins = computed(() => mapPins.value.filter((pin) => {
  const matchesQuery = !mapSearchQuery.value || [pin.name, pin.type, pin.place_name, pin.place_area, pin.area]
    .some(part => String(part || '').toLocaleLowerCase('vi-VN').includes(mapSearchQuery.value))
  const bounds = committedBounds.value
  const coordinates = bounds ? normalizeCoords(pin.coordinates || { lat: pin.lat, lng: pin.lng }) : null
  const matchesViewport = !bounds || Boolean(coordinates
    && coordinates[1] >= bounds.west
    && coordinates[1] <= bounds.east
    && coordinates[0] >= bounds.south
    && coordinates[0] <= bounds.north)
  return (
    (!savedMode.value || savedPinIds.value.has(String(pin.id)))
    && (activeTypeArray.value.includes('all') || activeTypeArray.value.includes(pin.type))
    && (!areaQuery.value || pin.place_area === areaQuery.value || pin.area === areaQuery.value)
    && matchesQuery
    && matchesViewport
  )
}))

const mapResults = computed<MapListResult[]>(() => filteredPins.value.slice(0, 120).map((pin) => {
  const coordinates = normalizeCoords(pin.coordinates || { lat: pin.lat, lng: pin.lng })
  return {
    ...pin,
    ...(coordinates ? { coordinates: { lat: coordinates[0], lng: coordinates[1] } } : {}),
    attributes: {
      ...(pin.attributes || {}),
      address: pin.attributes?.address || pin.place_name || pin.place_area || pin.area || '',
    },
  }
}))

const visibleLabel = computed(() => savedMode.value
  ? `${filteredPins.value.length} địa điểm đã lưu`
  : activeTypeArray.value.includes('all')
    ? `${filteredPins.value.length} địa điểm`
    : `${filteredPins.value.length} địa điểm phù hợp`)

function commitSearchArea(viewport: MapViewport) {
  searchView.commitViewport(viewport)
  scopeAnnouncement.value = 'Đã xác nhận phạm vi bản đồ mới.'
}

function updateNetworkState() {
  mapNetworkState.value = navigator.onLine ? 'ready' : 'offline'
}

onMounted(() => {
  updateNetworkState()
  const selectedFromLegacyLink = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
  if (typeof selectedFromLegacyLink === 'string' && selectedFromLegacyLink) searchView.selectResult(selectedFromLegacyLink)
  if (route.query.id || route.query.lat || route.query.lng) router.replace(searchView.url.value).catch(() => {})
  window.addEventListener('online', updateNetworkState)
  window.addEventListener('offline', updateNetworkState)
})

onBeforeUnmount(() => {
  window.removeEventListener('online', updateNetworkState)
  window.removeEventListener('offline', updateNetworkState)
})

useReveal()

useSeoMeta({
  title: 'Bản đồ du lịch Vĩnh Long — vinhlong360',
  description: 'Bản đồ và danh sách địa chỉ điểm du lịch, đặc sản, lưu trú, làng nghề tại Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: 'Bản đồ du lịch — vinhlong360',
  ogDescription: 'Khám phá vị trí và đối chiếu địa chỉ trên danh sách luôn khả dụng.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/ban-do') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: 'Bản đồ du lịch vinhlong360',
      description: 'Bản đồ và danh sách địa chỉ điểm du lịch, đặc sản, lưu trú và làng nghề.',
      url: canonicalUrl('/ban-do'),
      spatialCoverage: {
        '@type': 'Place',
        name: 'Vĩnh Long – Bến Tre – Trà Vinh',
        geo: { '@type': 'GeoShape', box: '9.8 105.8 10.4 106.7' },
      },
    }),
  }],
})
</script>

<style scoped>
.map-hero-inner { display: flex; flex-direction: column; align-items: flex-start; }
.map-hero-inner .dateline-eyebrow {
  display: block;
  width: 100%;
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: .5px solid var(--line);
  color: var(--muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
}
</style>
