<template>
  <div
    class="page"
    data-color-system="tri-region-v1"
    data-page-recipe="discovery"
    :data-material-accent="activeMode.accent"
  >
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Du lịch' }]" />

    <section
      class="atlas-hero"
      :class="`mode-${activeMode.key}`"
      aria-label="Định hướng khám phá"
      data-catalog-section="orientation"
    >
      <div class="atlas-hero-inner">
        <p class="atlas-hero-eyebrow">Vĩnh Long · chỉ mục khám phá theo địa bàn</p>
        <h1 class="atlas-hero-title">
          <span class="atlas-hero-line1">{{ pc('hero_title', 'Ba tỉnh, một nhịp sông.') }}</span>
          <Transition name="mode-fade" mode="out-in">
            <span class="atlas-hero-line2" :key="activeModeKey">{{ activeMode.line }}</span>
          </Transition>
        </h1>
        <Transition name="mode-fade" mode="out-in">
          <p class="atlas-hero-sub" :key="activeModeKey">{{ pc('hero_subtitle', activeMode.sub) }}</p>
        </Transition>
      </div>
      <ol class="catalog-route-trace" data-route-trace="catalog-context" aria-label="Dòng địa bàn hiện tại">
        <li data-route-node><span>Khu vực</span><strong>Vĩnh Long</strong></li>
        <li data-route-node data-route-node-active><span>Cách khám phá</span><strong>{{ activeMode.label }}</strong></li>
        <li data-route-node><span>Thời điểm</span><strong>Tháng {{ currentMonthNumber }}</strong></li>
      </ol>
    </section>

    <section class="catalog-filter-ledger block reveal" data-catalog-section="filters" aria-labelledby="catalog-filter-title">
      <header class="catalog-filter-ledger__header">
        <div>
          <p>Quyết định khám phá</p>
          <h2 id="catalog-filter-title">Chọn cách khám phá</h2>
        </div>
        <p>Chọn một nhịp đi, rồi tinh chỉnh loại và thời điểm trước khi đọc kết quả.</p>
      </header>
      <div class="mode-dial" role="group" aria-label="Chọn cách khám phá">
        <button
          v-for="m in heroModes"
          :key="m.key"
          type="button"
          :class="['mode-pill', { active: activeModeKey === m.key }]"
          :aria-pressed="activeModeKey === m.key"
          @click="selectDiscoveryMode(m)"
        >
          <IconLine :name="m.icon" aria-hidden="true" />
          <span>{{ m.label }}</span>
        </button>
      </div>
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm trong du lịch…" aria-label="Tìm kiếm" />
          <select v-model="sortBy" aria-label="Sắp xếp">
            <option value="relevant">Phù hợp nhất</option>
            <option value="popular">Phổ biến</option>
            <option value="newest">Mới nhất</option>
            <option value="name">Tên A-Z</option>
          </select>
        </div>
        <p class="control-label">Loại</p>
        <FilterChips
          :filters="typeFilterOptions"
          :model-value="[typeFilter]"
          single-select
          aria-label="Lọc theo loại"
          @update:model-value="v => typeFilter = v[0] || 'all'"
        />
        <p class="control-label">Theo tháng</p>
        <FilterChips
          :filters="seasonFilterOptions"
          :model-value="[seasonFilter]"
          single-select
          aria-label="Lọc theo tháng"
          @update:model-value="v => seasonFilter = v[0] || 'all'"
        />
        <div v-if="activeFilterCount > 0" class="filter-status">
          <span class="filter-count">{{ activeFilterCount }} bộ lọc</span>
          <button type="button" class="filter-clear" @click="clearFilters">Xóa tất cả</button>
        </div>
      </div>
    </section>

    <section ref="gridSection" class="catalog-results block reveal" data-catalog-section="results" aria-label="Duyệt tất cả du lịch">
      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả{{ sortBy !== 'relevant' ? ` · ${sortLabels[sortBy]}` : '' }}</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới" aria-label="Dạng lưới"><IconLine name="layout-dashboard" aria-hidden="true" /></button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách" aria-label="Dạng danh sách"><IconLine name="list" aria-hidden="true" /></button>
        </div>
      </div>
      <EmptyState v-if="fetchError" title="Không thể tải dữ liệu" message="Mạng có thể đang chập chờn. Thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-tourism')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" :class="['catalog-result-surface', viewMode === 'list' ? 'list-view' : 'grid']">
        <div
          v-for="e in visible"
          :key="e.id"
          class="catalog-result-item"
          :data-entity-contract="catalogEntityContract(e)"
          data-catalog-result
        >
          <EntityCard :entity="e" :season-filter="seasonFilter" color-recipe="tri-region-v1" />
        </div>
      </div>
      <EmptyState v-else title="Không tìm thấy kết quả" message="Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/theo-mua" class="btn btn-outline"><IconLine name="calendar" aria-hidden="true" /> Xem theo mùa</NuxtLink>
          <NuxtLink to="/san-pham" class="btn btn-outline"><IconLine name="gift" aria-hidden="true" /> Đặc sản</NuxtLink>
          <NuxtLink to="/le-hoi" class="btn btn-outline"><IconLine name="flag" aria-hidden="true" /> Lễ hội</NuxtLink>
        </template>
      </EmptyState>
      <button
        v-if="filtered.length && visibleCount < filtered.length"
        type="button"
        class="btn btn-ghost catalog-more"
        @click="visibleCount += PAGE_SIZE"
      >
        Xem thêm ({{ filtered.length - visibleCount }} còn lại)
      </button>
    </section>

    <section class="catalog-evidence block reveal" data-catalog-section="evidence" aria-labelledby="catalog-evidence-title">
      <header>
        <p>Nguồn và độ mới</p>
        <h2 id="catalog-evidence-title">Đọc bằng chứng trước khi quyết định</h2>
      </header>
      <p>Những dòng dưới đây phản ánh đúng metadata nguồn hiện có; dữ liệu thiếu bằng chứng sẽ giữ nhãn chưa rõ thay vì được nâng cấp thành xác minh.</p>
      <div v-if="evidenceEntities.length" class="catalog-evidence__list" role="list">
        <article v-for="entity in evidenceEntities" :key="entity.id" class="catalog-evidence__row" role="listitem">
          <NuxtLink :to="entityPath(entity.id)">{{ entity.name }}</NuxtLink>
          <span class="catalog-evidence__meta">
            <SourceMark
              :tier="entitySourceTier(entity)"
              :source-title="entitySourceTitle(entity)"
              :source-url="entitySourceUrl(entity)"
              :verified-at="entityVerifiedAt(entity)"
              compact
            />
            <FreshnessLine
              :status="entityFreshnessStatus(entity)"
              :updated-label="catalogUpdatedLabel(entity)"
            />
          </span>
        </article>
      </div>
      <p v-else class="catalog-evidence__empty">Chưa có kết quả để đối chiếu nguồn. Bộ lọc vẫn được giữ để bạn thử lại.</p>
    </section>

    <section class="catalog-continuation block reveal" data-catalog-section="continuation" aria-labelledby="catalog-continuation-title">
      <div>
        <p>Tiếp tục hành trình</p>
        <h2 id="catalog-continuation-title">Mang lựa chọn sang bản đồ hoặc lịch trình</h2>
      </div>
      <nav aria-label="Bước tiếp theo">
        <NuxtLink to="/ban-do"><IconLine name="map" aria-hidden="true" /> Xem trên bản đồ</NuxtLink>
        <NuxtLink to="/lich-trinh"><IconLine name="route" aria-hidden="true" /> Mở lịch trình</NuxtLink>
      </nav>
      <ClientOnly><LazyJourneyBar /></ClientOnly>
    </section>
  </div>
</template>

<script lang="ts">
const MONTH_ABBR = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
</script>

<script setup lang="ts">
import type { Entity } from '~/types'
import type { RegionalAccent } from '~/utils/regionalColor'
import { resolveFreshnessStatus, resolveSourceTier } from '~/utils/regionalColor'
import { TYPE_META, TOURISM_TYPES } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('du_lich')
const TYPES = TOURISM_TYPES as readonly string[]
function typeMeta(type: string) {
  return TYPE_META[type] || { label: type, cat: type, icon: 'compass' }
}

const typeChips = TYPES.map(t => ({
  value: t,
  label: typeMeta(t).label,
}))

const q = ref('')
const typeFilter = ref('all')
const seasonFilter = ref('all')

type DiscoveryMode = {
  key: string
  icon: string
  label: string
  line: string
  sub: string
  filterType: string
  accent: RegionalAccent
}

const heroModes: readonly DiscoveryMode[] = [
  { key: 'trai-nghiem', icon: 'compass', label: 'Trải nghiệm', line: 'Khám phá theo mùa nước, theo mùa trái, theo mùa lễ.', sub: 'Miệt vườn, cù lao và những hoạt động gắn với nhịp sống địa phương.', filterType: 'experience', accent: 'leaf' },
  { key: 'am-thuc', icon: 'bowl', label: 'Ẩm thực', line: 'Một tô bún nước lèo, một mẻ bánh xèo mới đổ.', sub: 'Chọn món ăn và địa chỉ có dữ liệu nguồn để tiếp tục khám phá.', filterType: 'dish', accent: 'amber' },
  { key: 'lang-nghe', icon: 'vase', label: 'Làng nghề', line: 'Theo dấu đất, lửa và những nghề còn được truyền lại.', sub: 'Gốm đỏ, chiếu lác và các không gian nghề có thể ghé thăm.', filterType: 'craft_village', accent: 'clay' },
  { key: 'luu-tru', icon: 'home', label: 'Lưu trú', line: 'Tìm một điểm nghỉ phù hợp với nhịp hành trình.', sub: 'Nhà vườn và lưu trú ven sông được đưa vào cùng mặt kết quả.', filterType: 'accommodation', accent: 'river' },
]
const overviewMode: DiscoveryMode = {
  key: 'tat-ca',
  icon: 'compass',
  label: 'Tất cả loại hình',
  line: 'Đọc toàn bộ chỉ mục trước khi chọn một nhịp khám phá.',
  sub: 'Miệt vườn, điểm tham quan, làng nghề, ẩm thực và lưu trú trong cùng một mặt kết quả.',
  filterType: 'all',
  accent: 'river',
}
const filterAccents: Readonly<Record<string, RegionalAccent>> = {
  experience: 'leaf',
  attraction: 'leaf',
  nature: 'leaf',
  dish: 'amber',
  craft_village: 'clay',
  history: 'clay',
  accommodation: 'river',
}
const activeMode = computed<DiscoveryMode>(() => {
  const effectiveType = typeFilter.value
  const mode = heroModes.find(candidate => candidate.filterType === effectiveType)
  if (mode) return mode
  if (effectiveType === 'all') return overviewMode

  const meta = typeMeta(effectiveType)
  return {
    key: `type-${effectiveType}`,
    icon: meta.icon,
    label: meta.label,
    line: `Khám phá ${meta.label.toLocaleLowerCase('vi-VN')} theo dữ liệu hiện có.`,
    sub: 'Dòng địa bàn phản ánh trực tiếp loại kết quả đang được lọc.',
    filterType: effectiveType,
    accent: filterAccents[effectiveType] || 'river',
  }
})
const activeModeKey = computed(() => activeMode.value.key)

function selectDiscoveryMode(mode: DiscoveryMode) {
  typeFilter.value = mode.filterType
}

const typeFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...typeChips.map(t => ({ key: t.value, label: t.label })),
])
const seasonFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Array.from({ length: 12 }, (_, i) => ({ key: String(i + 1), label: MONTH_ABBR[i] || String(i + 1) })),
  { key: 'flood', label: 'Mùa nước nổi' },
])
const sortBy = ref('relevant')
const sortLabels: Record<string, string> = { popular: 'Phổ biến', newest: 'Mới nhất', name: 'Tên A-Z' }
const viewMode = ref('grid')
const gridSection = ref<HTMLElement | null>(null)
const currentMonthNumber = new Date().getMonth() + 1

useFilterUrl({ q, type: typeFilter, mua: seasonFilter, sort: sortBy }, { q: '', type: 'all', mua: 'all', sort: 'relevant' })
const { sortByRegion } = useRegionPref()

onMounted(() => {
  const h = (e: KeyboardEvent) => {
    if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as Element)?.tagName)) {
      e.preventDefault()
      document.querySelector<HTMLInputElement>('.search-row input[type="search"]')?.focus()
    }
  }
  document.addEventListener('keydown', h)
  onUnmounted(() => document.removeEventListener('keydown', h))
})

const { data, error: fetchError } = await useAsyncData('catalog-tourism', () =>
  apiFetch<{ entities: Entity[]; total: number }>(`/api/entities?type=${TYPES.join(',')}&limit=500`)
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const activeFilterCount = computed(() => {
  let n = 0
  if (typeFilter.value !== 'all') n++
  if (seasonFilter.value !== 'all') n++
  if (q.value.trim()) n++
  return n
})

function clearFilters() {
  typeFilter.value = 'all'
  seasonFilter.value = 'all'
  q.value = ''
  sortBy.value = 'relevant'
}

const filtered = computed(() => {
  let list = allEntities.value

  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: Entity) => inSeason(e, seasonFilter.value))
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query)
    )
  }

  list = [...list]
  switch (sortBy.value) {
    case 'popular':
      list.sort((a: Entity, b: Entity) => (b.relationship_total || 0) - (a.relationship_total || 0))
      break
    case 'newest':
      list.sort((a: Entity, b: Entity) => (b.updatedAt || '').localeCompare(a.updatedAt || ''))
      break
    case 'name':
      list.sort((a: Entity, b: Entity) => (a.name || '').localeCompare(b.name || '', 'vi'))
      break
    default:
      if (seasonFilter.value !== 'all') {
        list.sort((a: Entity, b: Entity) => (relevanceScore(b, seasonFilter.value) || 0) - (relevanceScore(a, seasonFilter.value) || 0))
      }
      break
  }
  return sortByRegion(list)
})

// Client-side pagination: bound hydration cost on the full filtered grid
// (perf audit P2). First PAGE_SIZE render on the server for SEO/first-paint;
// "Xem thêm" reveals more without a refetch. Resets whenever a filter/search/
// sort input changes so the visible window always starts from the top.
const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const visible = computed(() => filtered.value.slice(0, visibleCount.value))
const evidenceEntities = computed(() => visible.value.slice(0, 3))
watch([q, typeFilter, seasonFilter, sortBy], () => { visibleCount.value = PAGE_SIZE })

function firstText(...values: unknown[]): string {
  const value = values.find(item => typeof item === 'string' && item.trim())
  return typeof value === 'string' ? value.trim() : ''
}

function hasCatalogMedia(entity: Entity): boolean {
  return Boolean(
    entity.image_descriptor?.url
    || entity.image_descriptors?.some(descriptor => descriptor.url)
    || entity.images?.some(Boolean)
    || entity.image_urls?.some(Boolean)
    || entity.image,
  )
}

function catalogEntityContract(entity: Entity): 'entity-row' | 'entity-tile' {
  return viewMode.value === 'grid' && hasCatalogMedia(entity) ? 'entity-tile' : 'entity-row'
}

function entitySourceTier(entity: Entity) {
  return resolveSourceTier(entity.source_freshness?.source_tier || entity.quality?.source_tier)
}

function entitySourceTitle(entity: Entity): string {
  return firstText(entity.source_freshness?.source_title, entity.quality?.source_title, entity.source?.[0]?.name)
}

function entitySourceUrl(entity: Entity): string {
  return firstText(entity.source_freshness?.source_url, entity.quality?.source_url, entity.source?.[0]?.url)
}

function entityVerifiedAt(entity: Entity): string {
  return firstText(entity.source_freshness?.verified_at, entity.quality?.verified_at)
}

function entityFreshnessStatus(entity: Entity) {
  return resolveFreshnessStatus(entity.source_freshness?.freshness_status)
}

function catalogUpdatedLabel(entity: Entity): string {
  const value = firstText(entity.source_freshness?.updated_at, entity.updatedAt)
  if (!value || !Number.isFinite(Date.parse(value))) return ''
  return `Cập nhật ${new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(value))}`
}

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/du-lich') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Du lịch Vĩnh Long',
        description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.',
        url: 'https://vinhlong360.vn/du-lich',
        numberOfItems: allEntities.value.length,
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Du lịch' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Du lịch Vĩnh Long, Bến Tre, Trà Vinh',
      'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực Vĩnh Long.',
      '/du-lich',
      filtered.value,
    )),
  }],
}))
</script>
