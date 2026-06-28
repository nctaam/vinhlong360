<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-product" aria-label="Giới thiệu sản phẩm">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🍊</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="allEntities.length" class="stat-num" />
          <span class="stat-label">sản phẩm</span>
        </div>
        <div class="stat-item">
          <CountUp :value="ocopCount" class="stat-num" />
          <span class="stat-label">OCOP</span>
        </div>
        <div class="stat-item">
          <CountUp :value="inSeasonCount" class="stat-num" />
          <span class="stat-label">đang mùa</span>
        </div>
      </div>
    </section>

    <!-- Spotlight nổi bật (magazine, dùng-chung) -->
    <CatalogSpotlight :items="allEntities" />

    <!-- Đang vào mùa -->
    <section v-if="seasonalHighlights.length" class="block band reveal">
      <div class="seasonal-banner seasonal-banner-live">
        <span class="seasonal-banner-icon" aria-hidden="true">🔥</span>
        <div>
          <strong>Tháng {{ currentMonth }} — đang vào mùa</strong>
          <p>Những sản phẩm đang chính vụ, ngon nhất thời điểm này.</p>
        </div>
        <span class="seasonal-banner-month" aria-hidden="true">Tháng {{ currentMonth }}</span>
      </div>
      <div class="scroll-row" role="region" aria-label="Đặc sản đang mùa" tabindex="0">
        <EntityCard v-for="e in seasonalHighlights" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
      </div>
    </section>

    <!-- OCOP Spotlight -->
    <section v-if="ocopHighlights.length" class="block reveal">
      <div class="section-head">
        <h2>⭐ Sản phẩm OCOP</h2>
        <button type="button" class="see-all" @click="ocopOnly = true; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Sản phẩm đạt chuẩn OCOP — Mỗi xã một sản phẩm, chất lượng được chứng nhận.</p>
      <div class="scroll-row" role="region" aria-label="Sản phẩm OCOP nổi bật" tabindex="0">
        <EntityCard v-for="e in ocopHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      fact="Ba tỉnh Vĩnh Long, Bến Tre, Trà Vinh là vựa trái cây lớn nhất ĐBSCL — mỗi mùa mang đến hương vị đặc trưng riêng."
      icon="🍊"
      variant="accent"
      :links="[{ to: '/theo-mua', label: 'Xem theo mùa' }, { to: '/ocop', label: 'Sản phẩm OCOP' }]"
    />

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2>Đặc sản vùng sông nước</h2>
      <p>Đồng bằng sông Cửu Long là vựa trái cây và nông sản lớn nhất cả nước. Riêng Vĩnh Long, Bến Tre và Trà Vinh đóng góp hàng chục loại đặc sản mang đậm bản sắc vùng miệt vườn: bưởi Năm Roi vỏ mỏng ruột ngọt, kẹo dừa Bến Tre dẻo thơm, nem chua Lai Vung chua cay đậm đà, hay bánh tráng Mỹ Lồng giòn rụm nướng than.</p>
      <p>Mỗi sản phẩm gắn liền với một vùng đất, một mùa vụ và một câu chuyện sản xuất riêng. Nhiều sản phẩm đã được chứng nhận OCOP (Mỗi xã Một sản phẩm) — đạt tiêu chuẩn chất lượng quốc gia từ 3 đến 5 sao.</p>

      <h2>Mua gì, tháng nào?</h2>
      <p>Trái cây miền Tây có tính mùa vụ rõ rệt. <strong>Tháng 5–7</strong> là mùa sầu riêng, măng cụt, chôm chôm — thời điểm trái ngon nhất và giá tốt nhất. <strong>Tháng 8–10</strong> là mùa bưởi và cam, cũng là lúc mùa nước nổi mang về cá linh, bông điên điển. <strong>Tháng 12–2</strong> là mùa dưa hấu, dưa lê phục vụ Tết Nguyên đán. Dừa và các sản phẩm từ dừa (kẹo, dầu, nước cốt) có quanh năm.</p>

      <h2>Sản phẩm OCOP</h2>
      <p>Chương trình OCOP đánh giá và xếp hạng sản phẩm địa phương theo 5 bậc sao. Sản phẩm 3 sao đạt tiêu chuẩn cơ bản, 4 sao có chất lượng cao với bao bì chuyên nghiệp, và 5 sao là cấp quốc gia — hiếm và rất uy tín. Khi mua sản phẩm OCOP, bạn biết chắc sản phẩm đã qua kiểm định chất lượng, có truy xuất nguồn gốc và hỗ trợ sinh kế cho nông dân bản địa.</p>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block" aria-label="Duyệt tất cả sản phẩm">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm trong sản phẩm…" aria-label="Tìm sản phẩm" />
          <select v-model="sortBy" aria-label="Sắp xếp">
            <option value="relevant">Phù hợp nhất</option>
            <option value="popular">Phổ biến</option>
            <option value="newest">Mới nhất</option>
            <option value="name">Tên A-Z</option>
          </select>
        </div>
        <p class="control-label">Theo tháng</p>
        <FilterChips
          :filters="seasonFilterOptions"
          :model-value="[seasonFilter]"
          single-select
          aria-label="Lọc theo tháng"
          @update:model-value="v => seasonFilter = v.length ? v[0] : 'all'"
        />
        <FilterChips
          :filters="[{ key: 'ocop', label: 'Chỉ sản phẩm OCOP', icon: '⭐' }]"
          :model-value="ocopOnly ? ['ocop'] : []"
          aria-label="Lọc nâng cao"
          @update:model-value="v => ocopOnly = v.includes('ocop')"
        />
        <div v-if="activeFilterCount > 0" class="filter-status">
          <span class="filter-count">{{ activeFilterCount }} bộ lọc</span>
          <button type="button" class="filter-clear" @click="clearFilters">Xóa tất cả</button>
        </div>
      </div>
      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả{{ sortBy !== 'relevant' ? ` · ${sortLabels[sortBy]}` : '' }}</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới" aria-label="Dạng lưới">⊞</button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách" aria-label="Dạng danh sách">☰</button>
        </div>
      </div>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Lỗi kết nối. Thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-products')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" :class="viewMode === 'list' ? 'list-view' : 'grid'">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🍊" title="Không tìm thấy sản phẩm" message="Thử chọn tháng khác hoặc bỏ bộ lọc OCOP.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/ocop" class="btn btn-outline">⭐ OCOP</NuxtLink>
          <NuxtLink to="/du-lich" class="btn btn-outline">🌿 Du lịch</NuxtLink>
          <NuxtLink to="/theo-mua" class="btn btn-outline">🗓️ Theo mùa</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block catalog-cross" aria-label="Khám phá thêm">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon" aria-hidden="true">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm đạt chuẩn</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="cross-icon" aria-hidden="true">📅</span>
          <div><strong>Theo mùa</strong><p>Lịch mùa vụ</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/kham-pha/am-thuc" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🍲</span>
          <div><strong>Ẩm thực</strong><p>Món ngon miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('san_pham')
const currentMonth = new Date().getMonth() + 1

const q = ref('')
const seasonFilter = ref(String(currentMonth))
const ocopOnly = ref(false)

const seasonFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Array.from({ length: 12 }, (_, i) => ({ key: String(i + 1), label: `T${i + 1}` })),
  { key: 'flood', label: 'Mùa nước nổi', icon: '🌊' },
])
const sortBy = ref('relevant')
const sortLabels: Record<string, string> = { popular: 'Phổ biến', newest: 'Mới nhất', name: 'Tên A-Z' }
const viewMode = ref('grid')
const gridSection = ref<HTMLElement | null>(null)

useFilterUrl({ mua: seasonFilter, sort: sortBy }, { mua: String(currentMonth), sort: 'relevant' })
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

const { data, error: fetchError } = await useAsyncData('catalog-products', () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?type=product&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const ocopCount = computed(() => allEntities.value.filter((e: Entity) => e.attributes?.ocop).length)
const inSeasonCount = computed(() => allEntities.value.filter((e: Entity) => inSeason(e, String(currentMonth))).length)

const seasonalHighlights = computed(() => {
  return allEntities.value
    .filter((e: Entity) => inSeason(e, String(currentMonth)))
    .sort((a: Entity, b: Entity) => (relevanceScore(b, String(currentMonth)) || 0) - (relevanceScore(a, String(currentMonth)) || 0))
    .slice(0, 8)
})

const ocopHighlights = computed(() => {
  return allEntities.value
    .filter((e: Entity) => e.attributes?.ocop)
    .slice(0, 8)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const activeFilterCount = computed(() => {
  let n = 0
  if (seasonFilter.value !== 'all' && seasonFilter.value !== String(currentMonth)) n++
  if (ocopOnly.value) n++
  if (q.value.trim()) n++
  return n
})

function clearFilters() {
  seasonFilter.value = String(currentMonth)
  ocopOnly.value = false
  q.value = ''
  sortBy.value = 'relevant'
}

const filtered = computed(() => {
  let list = allEntities.value

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: Entity) => inSeason(e, seasonFilter.value))
  }

  if (ocopOnly.value) {
    list = list.filter((e: Entity) => e.attributes?.ocop)
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

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/san-pham') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Sản phẩm địa phương Vĩnh Long',
        description: 'Đặc sản & sản phẩm OCOP Vĩnh Long theo mùa.',
        url: 'https://vinhlong360.vn/san-pham',
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
          { '@type': 'ListItem', position: 2, name: 'Sản phẩm' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Sản phẩm địa phương Vĩnh Long',
      'Đặc sản và sản phẩm OCOP Vĩnh Long theo mùa.',
      '/san-pham',
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
/* Seasonal "đang vào mùa" banner — gentle live-pulse + month context label.
   Scoped to .seasonal-banner-live so other pages' banners are unaffected. */
.seasonal-banner-live .seasonal-banner-icon {
  display: inline-block;
  animation: season-fire-pulse 2.8s var(--ease-out-expo) infinite;
}
.seasonal-banner-month {
  margin-left: auto;
  flex-shrink: 0;
  align-self: center;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--accent-fg, var(--muted));
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: rgba(var(--accent-rgb), .12);
  white-space: nowrap;
}

@keyframes season-fire-pulse {
  0%, 100% { transform: scale(1); filter: drop-shadow(0 0 0 rgba(var(--accent-rgb), 0)); }
  50% { transform: scale(1.08); filter: drop-shadow(0 0 4px rgba(var(--accent-rgb), .45)); }
}

.dark .seasonal-banner-month { background: rgba(var(--accent-rgb), .18); }

@media (prefers-reduced-motion: reduce) {
  .seasonal-banner-live .seasonal-banner-icon { animation: none; }
}

@media (max-width: 640px) {
  /* Keep the month chip from crowding the copy on small screens */
  .seasonal-banner-month { display: none; }
}

.controls {
  position: sticky;
  top: 0;
  z-index: 10;
}
.filter-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: .5px solid var(--line);
}
.filter-count {
  font-size: var(--text-xs);
  color: var(--muted);
  font-weight: var(--weight-medium);
}
.filter-clear {
  font-size: var(--text-xs);
  color: var(--primary-fg);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: var(--weight-semibold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: background .2s;
}
.filter-clear:hover {
  background: rgba(var(--primary-rgb), .08);
}
.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: 2px;
}
.vt-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-xs);
  font-size: var(--text-sm);
  color: var(--muted);
  transition: background .15s, color .15s;
  line-height: 1;
}
.vt-btn.active {
  background: var(--card);
  color: var(--fg);
  box-shadow: var(--shadow-xs);
}
.list-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.list-view :deep(.card) {
  flex-direction: row;
  align-items: stretch;
}
.list-view :deep(.cover) {
  width: 180px;
  min-height: 120px;
  flex-shrink: 0;
  aspect-ratio: auto;
}
.list-view :deep(.card-b) {
  flex: 1;
  min-width: 0;
}
.list-view :deep(.card-b h3) {
  -webkit-line-clamp: 1;
}
.list-view :deep(.summary) {
  -webkit-line-clamp: 2;
}
@media (max-width: 600px) {
  .list-view :deep(.card) { flex-direction: column; }
  .list-view :deep(.cover) { width: 100%; min-height: 140px; aspect-ratio: 16/9; }
}
</style>
