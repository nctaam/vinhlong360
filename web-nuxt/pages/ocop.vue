<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm', to: '/san-pham' }, { label: 'OCOP' }]" />

    <!-- Hero — "Sổ vàng" (the ledger opens; calmer/formal, structurally distinct
         from san-pham's market hero — kills the twin-collision, concept §2) -->
    <section class="catalog-hero cat-ocop ledger-hero">
      <div class="guilloche-texture" aria-hidden="true"></div>
      <div class="catalog-hero-inner">
        <div class="wax-seal" :aria-label="`Hạng cao nhất: ${topStarTier} sao`" role="img">
          <span class="wax-seal-notches" aria-hidden="true"></span>
          <span class="wax-seal-star" aria-hidden="true">★{{ topStarTier }}</span>
        </div>
        <div>
          <p class="ledger-kicker">Chứng nhận quốc gia · Mỗi xã một sản phẩm</p>
          <h1>{{ pc('hero_title') }}</h1>
          <p class="ledger-dek">{{ allOcop.length }} sản phẩm, từ 3 đến 5 sao — mỗi ngôi sao là một vòng kiểm định đã qua.</p>
          <p>{{ pc('hero_subtitle') }}</p>
          <div class="hero-creds">
            <span class="hero-cred hero-cred-seal">🏅 Chuẩn OCOP <em>Nhà nước</em></span>
            <span class="hero-cred">✓ Kiểm chứng</span>
            <span v-if="allOcop.length" class="hero-cred">📊 {{ allOcop.length }} sản phẩm</span>
          </div>
        </div>
      </div>
      <div v-if="allOcop.length" class="catalog-stats ledger-stats">
        <div class="stat-item">
          <CountUp :value="allOcop.length" class="stat-num" />
          <span class="stat-label">sản phẩm OCOP</span>
        </div>
        <div v-for="s in starStats" :key="s.stars" class="stat-item">
          <CountUp :value="s.count" class="stat-num" />
          <span class="stat-label">{{ s.stars }} sao</span>
        </div>
      </div>
    </section>

    <!-- declutter-3 T9: CatalogSpotlight đã bỏ — 3 star-band honor-roll là "what's great"
         signal đặc trưng của trang này. -->
    <!-- Star-rank quick-jump — subordinate to the ledger bands below, not equal rank -->
    <nav v-if="starStats.length" class="block reveal star-jump" aria-label="Nhảy nhanh tới hạng sao">
      <button type="button"
        v-for="s in starStats" :key="s.stars"
        :class="['star-jump-btn', { active: starFilter === s.stars }]"
        :aria-pressed="starFilter === s.stars"
        @click="starFilter = starFilter === s.stars ? 0 : s.stars; scrollToGrid()"
      >
        <span class="quick-pick-icon">{{ '⭐'.repeat(s.stars) }}</span>
        <span class="quick-pick-label">{{ s.stars }} sao</span>
        <span class="quick-pick-count">{{ s.count }} sản phẩm</span>
      </button>
    </nav>

    <!-- Star-rank ledger — structural centerpiece (concept §3/§10): a descending
         5→4→3 honor ledger that gets visually lighter/smaller as you scroll —
         you feel the hierarchy of trust through layout weight before reading a
         word. Bands reveal top-down staggered (5 first, 3 last). -->
    <section v-if="fiveStarHighlights.length" class="block reveal ocop-band ocop-band--5" data-stagger="0">
      <div class="section-head sediment-head">
        <h2>⭐ Bậc 5 sao</h2>
        <button type="button" class="see-all" @click="starFilter = 5; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Bậc cao nhất, hiếm nhất — sản phẩm đã chứng minh được cả chất lượng lẫn khả năng vươn xa.</p>
      <div class="honor-banner">
        <span class="honor-banner-icon" aria-hidden="true">👑</span>
        <span class="honor-banner-text">Danh sách vinh dự</span>
      </div>
      <div class="scroll-row honor-roll" role="region" aria-label="Sản phẩm OCOP 5 sao" tabindex="0">
        <EntityCard v-for="e in fiveStarHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <section v-if="fourStarHighlights.length" class="block reveal ocop-band ocop-band--4" data-stagger="1">
      <div class="section-head sediment-head">
        <h2>Bậc 4 sao</h2>
        <button type="button" class="see-all" @click="starFilter = 4; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Chất lượng cao, bao bì chuyên nghiệp — đã có câu chuyện sản phẩm rõ ràng.</p>
      <div class="scroll-row" role="region" aria-label="Sản phẩm OCOP 4 sao" tabindex="0">
        <EntityCard v-for="e in fourStarHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <section v-if="threeStarHighlights.length" class="block reveal ocop-band ocop-band--3" data-stagger="2">
      <div class="section-head sediment-head">
        <h2>Bậc 3 sao</h2>
        <button type="button" class="see-all" @click="starFilter = 3; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Mức cơ bản — đạt tiêu chuẩn an toàn thực phẩm, nhãn mác rõ ràng.</p>
      <div class="scroll-row" role="region" aria-label="Sản phẩm OCOP 3 sao" tabindex="0">
        <EntityCard v-for="e in threeStarHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- declutter-2 A5: region-picks đã bỏ — lớp discovery thứ 4 trùng FilterChips
         khu-vực trong controls (nhà của 3 tầng filter sao/khu-vực/tháng). -->

    <!-- Interstitial -->
    <!-- Editorial — drop-cap + pull-quote (declutter-2 A2: interstitial inline vào mạch bài) -->
    <section v-once class="page-article editorial-body reveal">
      <h2 class="sediment-head">OCOP là gì?</h2>
      <p>OCOP (One Commune One Product — Mỗi xã Một sản phẩm) là chương trình quốc gia nhằm phát triển kinh tế nông thôn thông qua việc nâng cao chất lượng và giá trị sản phẩm địa phương. Mỗi xã, phường xác định một hoặc vài sản phẩm thế mạnh, được hỗ trợ chuẩn hoá quy trình sản xuất, bao bì, truy xuất nguồn gốc và kết nối thị trường.</p>

      <CatalogInterstitial
        fact="Chương trình OCOP đã chứng nhận hàng trăm sản phẩm từ 3 tỉnh — mỗi sản phẩm đều qua đánh giá nghiêm ngặt về chất lượng và nguồn gốc."
        icon="🏅"
        variant="warm"
        :links="[{ to: '/san-pham', label: 'Tất cả sản phẩm' }, { to: '/theo-mua', label: 'Theo mùa vụ' }]"
      />

      <h2 class="sediment-head">Hệ thống xếp hạng sao</h2>
      <p>Sản phẩm OCOP được đánh giá theo thang 5 sao bởi hội đồng cấp tỉnh và trung ương. <strong>3 sao</strong> là mức cơ bản — sản phẩm đạt tiêu chuẩn an toàn thực phẩm, có nhãn mác rõ ràng. <strong>4 sao</strong> yêu cầu chất lượng cao hơn, bao bì chuyên nghiệp, có câu chuyện sản phẩm và khả năng mở rộng thị trường. <strong>5 sao</strong> là cấp quốc gia — rất hiếm, dành cho sản phẩm xuất sắc có tiềm năng xuất khẩu.</p>
      <blockquote class="pull-quote">Khi bạn thấy nhãn OCOP trên sản phẩm, bạn biết sản phẩm đó đã qua quy trình đánh giá nghiêm ngặt, có nguồn gốc rõ ràng và chất lượng được kiểm chứng — không phải tự phong hay tự gắn nhãn.</blockquote>

      <h2 class="sediment-head">OCOP vùng Vĩnh Long, Bến Tre, Trà Vinh</h2>
      <p>Ba tỉnh thuộc top đầu cả nước về số lượng sản phẩm OCOP, nhờ lợi thế nông nghiệp phong phú. Bến Tre dẫn đầu với các sản phẩm từ dừa: dầu dừa nguyên chất, kẹo dừa, thạch dừa, mỹ phẩm từ dừa. Vĩnh Long nổi bật với bưởi Năm Roi, nem chua Lai Vung, gạch gốm Mang Thít. Trà Vinh đóng góp các đặc sản Khmer như bánh tét lá cẩm, dừa sáp và mắm prohok.</p>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block reveal">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm sản phẩm OCOP…" aria-label="Tìm sản phẩm OCOP" />
          <select v-model="sortBy" aria-label="Sắp xếp">
            <option value="relevant">Phù hợp nhất</option>
            <option value="popular">Phổ biến</option>
            <option value="newest">Mới nhất</option>
            <option value="name">Tên A-Z</option>
          </select>
        </div>
        <p class="control-label">Hạng sao</p>
        <div :class="['star-filter-wrap', { 'star-filter-flash': starJustJumped }]">
          <FilterChips
            :filters="starFilterOptions"
            :model-value="[starFilterStr]"
            single-select
            aria-label="Lọc theo hạng sao"
            @update:model-value="v => starFilterStr = v[0] || '0'"
          />
        </div>
        <p class="control-label">Khu vực</p>
        <FilterChips
          :filters="areaFilterOptions"
          :model-value="[areaFilter]"
          single-select
          aria-label="Lọc theo khu vực"
          @update:model-value="v => areaFilter = v[0] || 'all'"
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

      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} sản phẩm OCOP{{ sortBy !== 'relevant' ? ` · ${sortLabels[sortBy]}` : '' }}</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới" aria-label="Dạng lưới">⊞</button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách" aria-label="Dạng danh sách">☰</button>
        </div>
      </div>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải sản phẩm OCOP" message="Mạng có thể đang chập chờn. Thử lại giúp mình nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-ocop')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" :class="viewMode === 'list' ? 'list-view' : 'grid'">
        <EntityCard v-for="e in visible" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="⭐" title="Không tìm thấy sản phẩm OCOP" message="Thử thay đổi hạng sao, khu vực hoặc tháng mùa vụ.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/san-pham" class="btn btn-outline">🍊 Tất cả sản phẩm</NuxtLink>
          <NuxtLink to="/du-lich" class="btn btn-outline">🌿 Du lịch</NuxtLink>
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

    <!-- Cross-links (declutter-2 A1: 4→3 script-driven; bỏ Theo-mùa — trùng interstitial links) -->
    <section class="block band reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink v-for="c in relatedCatalogs" :key="c.to" :to="c.to" class="cross-card">
          <span class="cross-icon" aria-hidden="true">{{ c.icon }}</span>
          <div><strong>{{ c.label }}</strong><p>{{ c.desc }}</p></div>
        </NuxtLink>
      </div>
    </section>
    <!-- declutter-3 T14 (A3c): JourneyBar page-level — trang thuộc luồng lập-kế-hoạch -->
    <ClientOnly><LazyJourneyBar /></ClientOnly>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('ocop')

const q = ref('')
const starFilter = ref(0)
const areaFilter = ref('all')
const seasonFilter = ref('all')
const sortBy = ref('relevant')
const sortLabels: Record<string, string> = { popular: 'Phổ biến', newest: 'Mới nhất', name: 'Tên A-Z' }
const viewMode = ref('grid')
const gridSection = ref<HTMLElement | null>(null)

const starFilterStr = computed({
  get: () => String(starFilter.value),
  set: (v: string) => { starFilter.value = parseInt(v) || 0 },
})
useFilterUrl({ sao: starFilterStr, vung: areaFilter, mua: seasonFilter, sort: sortBy }, { sao: '0', vung: 'all', mua: 'all', sort: 'relevant' })

const starFilterOptions = [
  { key: '0', label: 'Tất cả' },
  { key: '5', label: '5 sao', icon: '⭐⭐⭐⭐⭐' },
  { key: '4', label: '4 sao', icon: '⭐⭐⭐⭐' },
  { key: '3', label: '3 sao', icon: '⭐⭐⭐' },
]
const areaFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Object.entries(AREA_META).map(([slug, m]) => ({ key: slug, label: m.name, icon: m.emoji })),
])
const seasonFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Array.from({ length: 12 }, (_, i) => ({ key: String(i + 1), label: `T${i + 1}` })),
])
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

const { data, error: fetchError } = await useAsyncData('catalog-ocop', () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?type=product&limit=200')
)

const allOcop = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => e.attributes?.ocop)
})

// Total catalog size (san-pham.vue's full scope) minus the certified subset —
// resolves the "why two pages exist" confusion on the cross-link (concept §6):
// this page is the OCOP subset, san-pham is everything.
const otherProductsCount = computed(() => {
  const raw = data.value
  if (!raw) return 0
  return (raw.entities || []).length - allOcop.value.length
})

// declutter-2 A1: cross-links 3 card script-driven (bỏ Theo-mùa — trùng interstitial links).
const relatedCatalogs = computed(() => [
  { to: '/san-pham', icon: '🍊', label: 'Đặc sản', desc: `Còn ${otherProductsCount.value} đặc sản khác chưa có sao` },
  { to: '/du-lich', icon: '🌿', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn' },
  { to: '/kham-pha/am-thuc', icon: '🍲', label: 'Ẩm thực', desc: 'Món ngon Vĩnh Long' },
])

function getStars(e: Entity): number {
  return parseInt(String(e.attributes?.ocop || ''), 10) || 0
}

const starStats = computed(() => {
  const counts: Record<number, number> = {}
  for (const e of allOcop.value) {
    const s = getStars(e)
    if (s >= 3) counts[s] = (counts[s] || 0) + 1
  }
  return [5, 4, 3].filter(s => counts[s]).map(s => ({ stars: s, count: counts[s] || 0 }))
})

const fiveStarHighlights = computed(() =>
  allOcop.value.filter(e => getStars(e) >= 5).slice(0, 8)
)
const fourStarHighlights = computed(() =>
  allOcop.value.filter(e => getStars(e) === 4).slice(0, 8)
)
const threeStarHighlights = computed(() =>
  allOcop.value.filter(e => getStars(e) === 3).slice(0, 8)
)

// Wax-seal emblem shows the highest certified tier present in the ledger —
// falls back to 5 (the program ceiling) if the dataset is still loading.
const topStarTier = computed(() => starStats.value[0]?.stars || 5)

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

// Closes the loop between "I clicked 5-star" and "I see why the grid changed"
// (concept §5): briefly flash the grid's star-rank chip whenever the star
// filter changes via a band/jump click, guiding the eye to what moved.
const starJustJumped = ref(false)
let starFlashTimer: ReturnType<typeof setTimeout> | undefined
watch(starFilter, () => {
  starJustJumped.value = false
  nextTick(() => {
    starJustJumped.value = true
    clearTimeout(starFlashTimer)
    starFlashTimer = setTimeout(() => { starJustJumped.value = false }, 900)
  })
})
onUnmounted(() => clearTimeout(starFlashTimer))

const activeFilterCount = computed(() => {
  let n = 0
  if (starFilter.value > 0) n++
  if (areaFilter.value !== 'all') n++
  if (seasonFilter.value !== 'all') n++
  if (q.value.trim()) n++
  return n
})

function clearFilters() {
  starFilter.value = 0
  areaFilter.value = 'all'
  seasonFilter.value = 'all'
  q.value = ''
  sortBy.value = 'relevant'
}

const filtered = computed(() => {
  let list = allOcop.value

  if (starFilter.value > 0) {
    list = list.filter((e: Entity) => getStars(e) >= starFilter.value)
  }

  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getEntityArea(e) === areaFilter.value)
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
watch([q, starFilter, areaFilter, seasonFilter, sortBy], () => { visibleCount.value = PAGE_SIZE })

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/ocop') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Sản phẩm OCOP Vĩnh Long',
        description: 'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre, Trà Vinh.',
        url: 'https://vinhlong360.vn/ocop',
        numberOfItems: allOcop.value.length,
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Sản phẩm', item: 'https://vinhlong360.vn/san-pham' },
          { '@type': 'ListItem', position: 3, name: 'OCOP' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Sản phẩm OCOP Vĩnh Long, Bến Tre, Trà Vinh',
      'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre và Trà Vinh.',
      '/ocop',
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
/* Hero provenance / trust signals (OCOP official seal credibility) */
.hero-creds {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-6);
  font-size: var(--text-xs);
  padding: var(--space-4) 0 0;
  margin-top: var(--space-4);
  border-top: .5px solid var(--line);
}
.hero-cred {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--muted);
  font-weight: var(--weight-medium);
}
.hero-cred-seal {
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: .03em;
  color: var(--primary-fg);
}
.hero-cred-seal em { font-style: normal; color: var(--muted); text-transform: none; letter-spacing: 0; }

/* Honor roll banner above the 5-star carousel */
.honor-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  border-left: 3px solid var(--secondary);
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, rgba(var(--secondary-rgb), .08), transparent);
}
.honor-banner-icon { font-size: 1.25rem; }
.honor-banner-text {
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  color: var(--secondary-fg, var(--secondary));
  letter-spacing: var(--tracking-tight);
}
/* Curated-collection lift + glow for honor-roll cards */
.honor-roll :deep(.card:hover) {
  box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--secondary-rgb), .2), 0 18px 40px -18px rgba(var(--secondary-rgb), .35);
  transform: translateY(-8px);
}

/* Filter panel labeled sections — clearer scannable groups (OCOP page only) */
.controls .control-label {
  position: relative;
  font-size: .8rem;
  padding-left: var(--space-3);
}
.controls .control-label::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: .85em;
  border-radius: 2px;
  background: var(--primary-fg);
}

.dark .hero-cred-seal { color: var(--primary-fg); }
.dark .honor-banner { background: linear-gradient(90deg, rgba(var(--secondary-rgb), .12), transparent); }

@media (prefers-reduced-motion: reduce) {
  .honor-roll :deep(.card:hover) { transform: none; }
}

@media (max-width: 640px) {
  .hero-creds { gap: var(--space-4); }
}

.controls {
  position: sticky;
  top: 0;
  z-index: 10;
}
/* .filter-status/.result-bar/.view-toggle/.vt-btn/.list-view moved to
   assets/css/catalog.css (was identical across du-lich/ocop/san-pham). */

/* ══════════════════════════════════════════════════════════════════════
   "Sổ vàng OCOP" — signature moment: wax-seal emblem + descending 5→4→3
   star-ledger bands that get visually lighter/smaller as you scroll.
   Scoped to this page only; calmer/formal register than san-pham's market
   hero — kills the "twin collision" (concept 06-products.md §2/§10).
   ══════════════════════════════════════════════════════════════════════ */

/* Guilloché texture — fine wavy-line certificate engraving, echoing "official
   seal" WITHOUT a literal seal clipart. Inline SVG tile, ~4% opacity. */
.ledger-hero { position: relative; }
.guilloche-texture {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: .045;
  background-repeat: repeat;
  background-size: 64px 64px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'%3E%3Cg fill='none' stroke='%239C3D22' stroke-width='1'%3E%3Cpath d='M0 32 Q16 8 32 32 T64 32'/%3E%3Cpath d='M0 16 Q16 -8 32 16 T64 16'/%3E%3Cpath d='M0 48 Q16 24 32 48 T64 48'/%3E%3C/g%3E%3C/svg%3E");
}
.dark .guilloche-texture { opacity: .06; }

/* Wax-seal emblem — pure CSS circular seal, no image asset. Radial-gradient
   disc + notched clip-path edge + inset shadow for depth, showing the
   highest certified tier present. One-time "stamp" settle on first paint. */
.wax-seal {
  position: relative;
  flex-shrink: 0;
  width: clamp(64px, 6vw + 40px, 84px);
  height: clamp(64px, 6vw + 40px, 84px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 34% 30%, rgba(var(--secondary-rgb), .95), rgba(var(--primary-rgb), .9) 72%);
  clip-path: polygon(
    50% 0%, 61% 7%, 74% 3%, 82% 13%, 95% 15%, 96% 28%, 100% 38%,
    92% 48%, 100% 58%, 96% 68%, 95% 81%, 82% 83%, 74% 93%, 61% 89%,
    50% 100%, 39% 89%, 26% 93%, 18% 83%, 5% 81%, 4% 68%, 0% 58%,
    8% 48%, 0% 38%, 4% 28%, 5% 15%, 18% 13%, 26% 3%, 39% 7%
  );
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, .28), 0 4px 14px -6px rgba(var(--primary-rgb), .5);
  animation: seal-stamp .4s var(--ease-spring-gentle) both;
}
.wax-seal-notches {
  position: absolute;
  inset: 6%;
  border-radius: 50%;
  border: 1px dashed rgba(255, 255, 255, .4);
}
.wax-seal-star {
  position: relative;
  z-index: 1;
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(1.1rem, .6vw + 1rem, 1.35rem);
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, .35);
  letter-spacing: -.01em;
}
@keyframes seal-stamp {
  0% { transform: scale(.9); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
.dark .wax-seal { box-shadow: inset 0 2px 6px rgba(0, 0, 0, .4), 0 4px 14px -6px rgba(var(--primary-rgb), .35); }

/* Kicker / dek — calmer, more formal register than san-pham's market voice */
.catalog-hero-inner p.ledger-kicker {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--secondary-fg, var(--secondary));
  margin: 0 0 var(--space-2);
}
.dark .catalog-hero-inner p.ledger-kicker { color: var(--secondary-fg); }
.catalog-hero-inner p.ledger-dek {
  font-family: var(--font-editorial);
  font-size: clamp(1rem, .94rem + .3vw, 1.1rem);
  line-height: var(--leading-snug);
  color: var(--ink);
  max-width: 58ch;
  margin: var(--space-2) 0 0;
}

/* Stats row — same sediment-tick visual language as san-pham's, applied
   identically so both pages still feel like one publication (§0 luận đề). */
.ledger-stats { position: relative; padding-left: var(--space-4); }
.ledger-stats::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 1.6em;
  border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .ledger-stats::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }

/* Star-rank quick-jump nav — compact, subordinate to the ledger bands below */
.star-jump { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.star-jump-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: .5px solid var(--line);
  border-radius: var(--radius-full);
  background: var(--card);
  cursor: pointer;
  font-size: var(--text-xs);
  transition: border-color .2s var(--ease-out), background .2s var(--ease-out);
}
.star-jump-btn:hover { border-color: var(--primary-fg); }
.star-jump-btn.active { border-color: var(--primary); background: rgba(var(--primary-rgb), .06); }
.star-jump-btn .quick-pick-icon { font-size: .85rem; }
.star-jump-btn .quick-pick-count { color: var(--muted); font-size: var(--text-xs); }

/* Descending star-ledger bands — border weight + glow + numeral size decrease
   5→4→3, so trust hierarchy reads through layout weight before a word is
   read (signature moment, concept §10). Reuses EntityCard unchanged. */
.ocop-band { border-radius: var(--radius-xl); padding: var(--space-6); margin-bottom: var(--space-6); }
.ocop-band--5 {
  border: 1px solid rgba(var(--accent-rgb), .35);
  background: linear-gradient(180deg, rgba(var(--accent-rgb), .07), transparent 65%);
  box-shadow: 0 0 0 1px rgba(var(--accent-rgb), .08), var(--shadow-sm);
}
.ocop-band--5 .section-head h2 {
  font-size: clamp(1.6rem, 1.3rem + 1vw, 2.1rem);
}
.ocop-band--4 {
  border: .5px solid rgba(var(--accent-rgb), .2);
  background: linear-gradient(180deg, rgba(var(--accent-rgb), .035), transparent 65%);
  padding: var(--space-5);
}
.ocop-band--4 .section-head h2 { font-size: var(--text-xl); }
.ocop-band--3 {
  border: .5px solid var(--line);
  background: none;
  padding: var(--space-4) var(--space-5);
  box-shadow: none;
}
.ocop-band--3 .section-head h2 { font-size: var(--text-lg); }
.dark .ocop-band--5 { background: linear-gradient(180deg, rgba(var(--accent-rgb), .1), transparent 65%); }
.dark .ocop-band--4 { background: linear-gradient(180deg, rgba(var(--accent-rgb), .05), transparent 65%); }

/* Explicit top-down stagger reinforcement (5 settles first, 3 last) — modest
   nudge on top of each band's own independent scroll-triggered reveal. */
.ocop-band[data-stagger="0"].reveal.revealed { animation-delay: 0s; }
.ocop-band[data-stagger="1"].reveal.revealed { animation-delay: .1s; }
.ocop-band[data-stagger="2"].reveal.revealed { animation-delay: .2s; }

/* Region quick-picks visually quieter/subordinate to the star ledger above */

/* Star-filter chip highlight-flash — closes the loop between "I clicked
   5-star" and "I see why the grid changed" (concept §5). */
.star-filter-wrap { border-radius: var(--radius-lg); transition: box-shadow .3s var(--ease-out); }
.star-filter-flash { box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .35); animation: star-filter-glow .9s var(--ease-out) both; }
@keyframes star-filter-glow {
  0% { box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .5); }
  100% { box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0); }
}
.dark .star-filter-flash { box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .4); }

@media (prefers-reduced-motion: reduce) {
  .wax-seal { animation: none; }
  .ocop-band[data-stagger].reveal.revealed { animation-delay: 0s; }
  .star-filter-flash { animation: none; box-shadow: 0 0 0 3px rgba(var(--accent-rgb), .3); }
}

@media (max-width: 640px) {
  .ocop-band { padding: var(--space-4); }
  .ocop-band--4 { padding: var(--space-4); }
  .ocop-band--3 { padding: var(--space-3) var(--space-4); }
}
</style>
