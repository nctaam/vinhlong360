<template>
  <section class="page" data-color-system="tri-region-v1" data-page-recipe="map" :data-outdoor-contrast="outdoorContrast ? 'high' : 'normal'">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Bản đồ' }]" :json-ld="true" />

    <section class="catalog-hero cat-map">
      <div class="catalog-hero-inner map-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true"><IconLine name="map" /></span>
        <div>
          <span class="dateline-eyebrow">Bản đồ sống · Tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025)</span>
          <h1>Bản đồ</h1>
          <p>So sánh vị trí bằng bản đồ, đối chiếu bằng danh sách và địa chỉ ngay cả khi tile không tải.</p>
        </div>
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
        <div class="map-field-dock" role="toolbar" aria-label="Tiện ích thực địa & lọc chuyên đề">
          <div class="map-quick-presets" role="group" aria-label="Lọc theo đặc trưng sông nước">
            <button
              v-for="preset in quickWaterPresets"
              :key="preset.id"
              type="button"
              :class="['map-quick-preset-btn', { 'is-active': activeWaterPreset === preset.id }]"
              :aria-pressed="activeWaterPreset === preset.id"
              @click="toggleWaterPreset(preset.id)"
            >
              <IconLine :name="preset.icon" aria-hidden="true" />
              <span>{{ preset.label }}</span>
            </button>
          </div>
          <button
            type="button"
            class="map-contrast-toggle"
            :class="{ 'is-high': outdoorContrast }"
            :aria-pressed="outdoorContrast"
            title="Tăng tương phản để dễ nhìn dưới nắng ngoài trời"
            @click="outdoorContrast = !outdoorContrast"
          >
            <IconLine :name="outdoorContrast ? 'sun' : 'bulb'" aria-hidden="true" />
            <span>{{ outdoorContrast ? 'Tương phản ngoài trời: BẬT' : 'Độ tương phản thực địa' }}</span>
          </button>
        </div>
        <div v-if="hasActiveFilters" class="active-filter-ledger" role="region" aria-label="Bộ lọc đang áp dụng">
          <span class="afl-heading">Đang lọc:</span>
          <div class="afl-chips">
            <span v-if="savedMode" class="afl-chip">
              <span class="afl-text">Đã lưu</span>
              <button type="button" class="afl-remove" aria-label="Bỏ lọc điểm đã lưu" @click="clearSavedMode"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <span v-if="activeWaterPreset !== 'all'" class="afl-chip">
              <span class="afl-text">{{ quickWaterPresets.find(p => p.id === activeWaterPreset)?.label }}</span>
              <button type="button" class="afl-remove" aria-label="Bỏ lọc đặc trưng" @click="activeWaterPreset = 'all'"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <template v-if="!activeTypeArray.includes('all')">
              <span v-for="t in activeTypeArray" :key="t" class="afl-chip">
                <span class="afl-text">{{ getTypeLabel(t) }}</span>
                <button type="button" class="afl-remove" :aria-label="`Bỏ lọc ${getTypeLabel(t)}`" @click="removeTypeFilter(t)"><IconLine name="x" aria-hidden="true" /></button>
              </span>
            </template>
            <button type="button" class="afl-clear-all" aria-label="Xóa tất cả bộ lọc" @click="clearAllFilters">Xóa tất cả</button>
          </div>
        </div>
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
        :viewport-pending="searchView.viewportPending.value"
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
      :viewport-pending="searchView.viewportPending.value"
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
  { value: 'all', label: 'Tất cả' },
  { value: 'attraction', label: 'Tham quan' },
  { value: 'experience', label: 'Trải nghiệm' },
  { value: 'nature', label: 'Thiên nhiên' },
  { value: 'history', label: 'Lịch sử' },
  { value: 'dish', label: 'Ẩm thực' },
  { value: 'craft_village', label: 'Làng nghề' },
  { value: 'accommodation', label: 'Lưu trú' },
  { value: 'product', label: 'Đặc sản' },
]

const allowedTypes = new Set(typeFilters.map(filter => filter.value))
const route = useRoute()
const router = useRouter()
const searchView = useSearchViewState()
const { favorites } = useFavorites()
const mapNetworkState = ref<'ready' | 'offline'>('ready')
const scopeAnnouncement = ref('')
const outdoorContrast = ref(false)
const activeWaterPreset = ref<'all' | 'river' | 'pottery' | 'ferry'>('all')

const quickWaterPresets = [
  { id: 'river' as const, label: 'Cù lao & Ven sông', icon: 'droplet' },
  { id: 'pottery' as const, label: 'Lò gốm Mang Thít', icon: 'flame' },
  { id: 'ferry' as const, label: 'Bến đò - Phà', icon: 'compass' },
]

function toggleWaterPreset(presetId: 'river' | 'pottery' | 'ferry') {
  activeWaterPreset.value = activeWaterPreset.value === presetId ? 'all' : presetId
}

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

type MapFilterOption = { key: string; label: string }
const typeFilterOptions: MapFilterOption[] = typeFilters.map(filter => ({ key: filter.value, label: filter.label }))

function onTypeFilterChange(values: string[]) {
  const current = activeTypeArray.value
  if (!values.length || (values.includes('all') && !current.includes('all'))) {
    searchView.setFilter('type', undefined)
    return
  }
  const filtered = values.filter(value => value !== 'all' && allowedTypes.has(value))
  searchView.setFilter('type', filtered.length ? filtered : undefined)
}

const hasActiveFilters = computed(() => savedMode.value || !activeTypeArray.value.includes('all') || activeWaterPreset.value !== 'all')

function clearSavedMode() {
  const query = { ...route.query }
  delete query.source
  router.push({ path: '/ban-do', query })
}

function removeTypeFilter(typeToRemove: string) {
  const remaining = activeTypeArray.value.filter(t => t !== typeToRemove && t !== 'all')
  searchView.setFilter('type', remaining.length ? remaining : undefined)
}

function clearAllFilters() {
  searchView.setFilter('type', undefined)
  activeWaterPreset.value = 'all'
  if (savedMode.value) {
    clearSavedMode()
  }
}

function getTypeLabel(type: string): string {
  return typeFilters.find(f => f.value === type)?.label || type
}

const mapPinApiPath = computed(() => {
  const params = new URLSearchParams()
  if (activeTypeQuery.value) params.set('type', activeTypeQuery.value)
  if (areaQuery.value) params.set('area', areaQuery.value)
  const query = params.toString()
  return `/api/map-pins${query ? `?${query}` : ''}`
})

const mapAsyncData = useAsyncData(
  computed(() => `map-pins-${activeTypeQuery.value || 'all'}-${areaQuery.value || 'all'}`),
  () => apiFetch<MapPin[]>(mapPinApiPath.value),
  { watch: [mapPinApiPath] },
)
const { data, error: fetchError, status, refresh } = mapAsyncData
const retryData = () => refresh()

const lastSuccessfulMapPins = ref<MapPin[]>([])
watch(data, (value) => {
  if (Array.isArray(value)) lastSuccessfulMapPins.value = value
}, { immediate: true })
const mapPins = computed(() => Array.isArray(data.value)
  ? data.value
  : fetchError.value ? lastSuccessfulMapPins.value : [])
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
    && (activeWaterPreset.value === 'all' || (() => {
      const text = `${pin.name || ''} ${pin.place_name || ''} ${pin.place_area || ''} ${pin.area || ''}`.toLocaleLowerCase('vi-VN')
      if (activeWaterPreset.value === 'river') return text.includes('cù lao') || text.includes('sông') || text.includes('an bình') || text.includes('đồng phú') || text.includes('bình hòa phước')
      if (activeWaterPreset.value === 'pottery') return text.includes('gốm') || text.includes('mang thít') || text.includes('lò gạch') || text.includes('thầy cai')
      if (activeWaterPreset.value === 'ferry') return text.includes('phà') || text.includes('đò') || text.includes('bến phà') || text.includes('bến đò')
      return true
    })())
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

const visibleLabel = computed(() => {
  const count = filteredPins.value.length
  if (savedMode.value) return `${count} địa điểm đã lưu`
  if (activeWaterPreset.value !== 'all') {
    const preset = quickWaterPresets.find(p => p.id === activeWaterPreset.value)
    return `${count} địa điểm ${preset?.label || ''}`
  }
  return activeTypeArray.value.includes('all')
    ? `${count} địa điểm`
    : `${count} địa điểm phù hợp`
})

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

await mapAsyncData

useReveal()

useSeoMeta({
  title: 'Bản đồ du lịch Vĩnh Long — vinhlong360',
  description: 'Bản đồ và danh sách địa chỉ điểm du lịch, đặc sản, lưu trú, làng nghề tại tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  ogTitle: 'Bản đồ du lịch — vinhlong360',
  ogDescription: 'Khám phá vị trí và đối chiếu địa chỉ trên danh sách luôn khả dụng.',
  ogUrl: () => canonicalUrl('/ban-do'),
  twitterCard: 'summary_large_image',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/ban-do') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: 'Bản đồ du lịch vinhlong360',
      description: 'Bản đồ và danh sách địa chỉ điểm du lịch, đặc sản, lưu trú và làng nghề.',
      url: canonicalUrl('/ban-do'),
      spatialCoverage: {
        '@type': 'Place',
        name: 'Tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025)',
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
.map-field-dock {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--line);
}
.map-quick-presets { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.map-quick-preset-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--muted);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background .2s var(--ease-out), border-color .2s var(--ease-out), color .2s var(--ease-out);
}
.map-quick-preset-btn:hover { background: var(--bg-warm); border-color: var(--border); color: var(--ink); }
.map-quick-preset-btn.is-active {
  background: color-mix(in srgb, var(--color-brand) 12%, var(--card));
  border-color: var(--color-brand);
  color: var(--color-brand);
  font-weight: var(--weight-semibold);
}
.map-contrast-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  color: var(--muted);
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all .2s var(--ease-out);
}
.map-contrast-toggle:hover { background: var(--bg-warm); color: var(--ink); }
.map-contrast-toggle.is-high {
  background: var(--color-brand);
  border-color: var(--color-brand);
  color: var(--color-on-action, var(--white));
  font-weight: var(--weight-semibold);
}
[data-outdoor-contrast="high"] .map-filters {
  border: 2px solid var(--color-brand);
  box-shadow: var(--shadow-md);
}
[data-outdoor-contrast="high"] .map-quick-preset-btn {
  border-width: 2px;
  font-weight: var(--weight-bold);
}
</style>
