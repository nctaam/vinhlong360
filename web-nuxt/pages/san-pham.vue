<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm' }]" />

    <!-- Hero — "Phiên chợ đang họp" (month-alive market masthead; signature moment) -->
    <section class="catalog-hero cat-product market-hero" aria-label="Giới thiệu sản phẩm">
      <div class="woven-texture" aria-hidden="true"></div>
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🍊</span>
        <div>
          <p class="market-kicker">Phiên chợ · Tháng {{ currentMonth }}</p>
          <h1>{{ pc('hero_title') }}</h1>
          <p class="market-dek">Tháng {{ currentMonth }}, {{ inSeasonCount }} loại đặc sản đang chính vụ — ngon nhất, rẻ nhất, đúng lúc.</p>
          <p class="market-subtitle">{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats market-stats">
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

    <!-- declutter-3 T10: CatalogSpotlight đã bỏ — market-shelf mùa vụ thay vai khối tease
         duy nhất trước grid (chốt spec-review). -->
    <!-- Đang vào mùa — promoted above OCOP teaser: season is this page's spine -->
    <section v-if="seasonalHighlights.length" class="block band reveal market-shelf">
      <div class="seasonal-banner seasonal-banner-live">
        <span class="seasonal-banner-icon" aria-hidden="true">🔥</span>
        <div>
          <strong>Chợ phiên tháng này</strong>
          <p>Trái chín đúng độ, người vườn vừa hái, chưa kịp nguội hơi đất.</p>
        </div>
        <span class="seasonal-banner-month" aria-hidden="true">Tháng {{ currentMonth }}</span>
      </div>
      <div class="scroll-row" role="region" aria-label="Đặc sản đang mùa" tabindex="0">
        <EntityCard v-for="e in seasonalHighlights" :key="e.id" :entity="e" :season-filter="String(currentMonth)" class="market-card" />
      </div>
    </section>

    <!-- OCOP teaser — slim signpost outward to /ocop, not a competing deep-dive -->
    <section v-if="ocopCount" class="block reveal ocop-teaser-strip">
      <NuxtLink to="/ocop" class="ocop-teaser-link">
        <span class="ocop-teaser-icon" aria-hidden="true">⭐</span>
        <span class="ocop-teaser-copy">
          Trong {{ allEntities.length }} đặc sản này, <strong>{{ ocopCount }} món</strong> đã có sao OCOP — xem sổ vàng
        </span>
        <span class="ocop-teaser-arrow" aria-hidden="true">→</span>
      </NuxtLink>
    </section>

    <!-- Editorial — drop-cap (auto via .page-article) + pull-quote (concept §4).
         declutter-2 A2 (pilot): interstitial thôi đứng section riêng — inline vào giữa
         mạch editorial làm callout (props tĩnh, an toàn dưới v-once). -->
    <section v-once class="page-article editorial-body reveal">
      <h2 class="sediment-head">Đặc sản vùng sông nước</h2>
      <p>Đồng bằng sông Cửu Long là vựa trái cây và nông sản lớn nhất cả nước. Riêng Vĩnh Long, Bến Tre và Trà Vinh đóng góp hàng chục loại đặc sản mang đậm bản sắc vùng miệt vườn: bưởi Năm Roi vỏ mỏng ruột ngọt, kẹo dừa Bến Tre dẻo thơm, dừa sáp Cầu Kè béo quánh hiếm có, hay bánh tráng Mỹ Lồng giòn rụm nướng than.</p>
      <blockquote class="pull-quote">Mỗi sản phẩm gắn liền với một vùng đất, một mùa vụ và một câu chuyện sản xuất riêng.</blockquote>
      <p>Nhiều sản phẩm đã được chứng nhận OCOP (Mỗi xã Một sản phẩm) — đạt tiêu chuẩn chất lượng quốc gia từ 3 đến 5 sao.</p>

      <CatalogInterstitial
        fact="Ba tỉnh Vĩnh Long, Bến Tre, Trà Vinh là vựa trái cây lớn nhất ĐBSCL — mỗi mùa mang đến hương vị đặc trưng riêng."
        icon="🍊"
        variant="accent"
        :links="[{ to: '/theo-mua', label: 'Xem theo mùa' }, { to: '/ocop', label: 'Sản phẩm OCOP' }]"
      />

      <h2 class="sediment-head">Mua gì, tháng nào?</h2>
      <p>Trái cây miền Tây có tính mùa vụ rõ rệt. <strong>Tháng 5–7</strong> là mùa sầu riêng, măng cụt, chôm chôm — thời điểm trái ngon nhất và giá tốt nhất. <strong>Tháng 8–10</strong> là mùa bưởi và cam, cũng là lúc mùa nước nổi mang về cá linh, bông điên điển. <strong>Tháng 12–2</strong> là mùa dưa hấu, dưa lê phục vụ Tết Nguyên đán. Dừa và các sản phẩm từ dừa (kẹo, dầu, nước cốt) có quanh năm.</p>

      <h2 class="sediment-head">Sản phẩm OCOP</h2>
      <p>Chương trình OCOP đánh giá và xếp hạng sản phẩm địa phương theo 5 bậc sao. Sản phẩm 3 sao đạt tiêu chuẩn cơ bản, 4 sao có chất lượng cao với bao bì chuyên nghiệp, và 5 sao là cấp quốc gia — hiếm và rất uy tín. Khi mua sản phẩm OCOP, bạn biết chắc sản phẩm đã qua kiểm định chất lượng, có truy xuất nguồn gốc và hỗ trợ sinh kế cho nông dân bản địa.</p>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block reveal" aria-label="Duyệt tất cả sản phẩm">
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
        <div class="control-label-row">
          <p class="control-label">Theo tháng</p>
          <button
            v-if="seasonFilter !== String(currentMonth)"
            type="button"
            class="season-reset-chip"
            @click="seasonFilter = String(currentMonth)"
          >⟲ tháng này</button>
        </div>
        <FilterChips
          :filters="seasonFilterOptions"
          :model-value="[seasonFilter]"
          single-select
          aria-label="Lọc theo tháng"
          @update:model-value="v => seasonFilter = v[0] || 'all'"
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
        <EntityCard v-for="e in visible" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🍊" title="Không tìm thấy sản phẩm" message="Thử chọn tháng khác hoặc bỏ bộ lọc OCOP.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/ocop" class="btn btn-outline">⭐ OCOP</NuxtLink>
          <NuxtLink to="/du-lich" class="btn btn-outline">🌿 Du lịch</NuxtLink>
          <NuxtLink to="/theo-mua" class="btn btn-outline">🗓️ Theo mùa</NuxtLink>
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

    <!-- Cross-links (declutter-2 A1: 4→3 script-driven; bỏ OCOP — trùng teaser-strip trên trang) -->
    <section class="block band catalog-cross reveal" aria-label="Khám phá thêm">
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

useFilterUrl({ q, mua: seasonFilter, sort: sortBy }, { q: '', mua: String(currentMonth), sort: 'relevant' })
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

// declutter-2 A1: cross-links 3 card script-driven (bỏ OCOP — teaser-strip trên trang
// đã là tham chiếu OCOP nổi bật hơn).
const relatedCatalogs = [
  { to: '/theo-mua', icon: '📅', label: 'Theo mùa', desc: 'Lịch mùa vụ' },
  { to: '/du-lich', icon: '🌿', label: 'Du lịch', desc: 'Trải nghiệm miệt vườn' },
  { to: '/kham-pha/am-thuc', icon: '🍲', label: 'Ẩm thực', desc: 'Món ngon Vĩnh Long' },
]
const inSeasonCount = computed(() => allEntities.value.filter((e: Entity) => inSeason(e, String(currentMonth))).length)

const seasonalHighlights = computed(() => {
  return allEntities.value
    .filter((e: Entity) => inSeason(e, String(currentMonth)))
    .sort((a: Entity, b: Entity) => (relevanceScore(b, String(currentMonth)) || 0) - (relevanceScore(a, String(currentMonth)) || 0))
    // declutter-3 T10: 8→4 — shelf là khối tease duy nhất, không phải catalog thứ hai
    .slice(0, 4)
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

// Client-side pagination: bound hydration cost on the full filtered grid
// (perf audit P2). First PAGE_SIZE render on the server for SEO/first-paint;
// "Xem thêm" reveals more without a refetch. Resets whenever a filter/search/
// sort input changes so the visible window always starts from the top.
const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const visible = computed(() => filtered.value.slice(0, visibleCount.value))
watch([q, seasonFilter, ocopOnly, sortBy], () => { visibleCount.value = PAGE_SIZE })

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
/* .filter-status/.result-bar/.view-toggle/.vt-btn/.list-view moved to
   assets/css/catalog.css (was identical across du-lich/ocop/san-pham). */

/* ══════════════════════════════════════════════════════════════════════
   "Chợ phiên miệt vườn" — signature moment: month-alive hero + woven-basket
   market texture. Scoped to this page only; kills the "twin collision" with
   ocop.vue's calmer ledger register (concept 06-products.md §2/§10).
   ══════════════════════════════════════════════════════════════════════ */

/* Woven cần xé/thúng basket motif — culturally specific hexagonal reed-weave,
   NOT generic wicker clipart. Inline SVG tile, ~4% opacity, amber/leaf tones. */
.market-hero { position: relative; }
.woven-texture {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: .05;
  background-repeat: repeat;
  background-size: 46px 40px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='46' height='40' viewBox='0 0 46 40'%3E%3Cg fill='none' stroke='%23C4872A' stroke-width='1.4'%3E%3Cpath d='M0 10 L11.5 3 L23 10 L23 24 L11.5 31 L0 24 Z'/%3E%3Cpath d='M23 10 L34.5 3 L46 10 L46 24 L34.5 31 L23 24 Z'/%3E%3Cpath d='M11.5 31 L23 38 L34.5 31'/%3E%3Cpath d='M11.5 -9 L23 -2 L34.5 -9'/%3E%3C/g%3E%3C/svg%3E");
}
.dark .woven-texture { opacity: .07; }

/* Kicker / dek — editorial dateline voice, ties hero to the real calendar month */
.catalog-hero-inner p.market-kicker {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--accent-dark, var(--amber-600));
  margin: 0 0 var(--space-2);
}
.dark .catalog-hero-inner p.market-kicker { color: var(--amber-500); }
.catalog-hero-inner p.market-dek {
  font-family: var(--font-editorial);
  font-size: clamp(1rem, .94rem + .3vw, 1.1rem);
  line-height: var(--leading-snug);
  color: var(--ink);
  max-width: 56ch;
  margin: var(--space-2) 0 0;
}
.catalog-hero-inner p.market-subtitle { color: var(--muted); margin-top: var(--space-1); }

/* Stats row restyled onto the sediment-tick section-head visual language
   (river→amber→clay tick) — echoes .sediment-head without misapplying that
   class to non-<h2> markup. */
.market-stats { position: relative; padding-left: var(--space-4); }
.market-stats::before {
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
.dark .market-stats::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }

/* Seasonal rail restyled as a "chợ phiên" horizontal shelf — subtle warm
   market-stall backdrop band, CSS gradient only, not an image. */
.market-shelf {
  background-image:
    linear-gradient(180deg, rgba(var(--accent-rgb), .05) 0%, transparent 60%),
    var(--season-hero-gradient);
}

/* Droplet-shadow hover ripple on seasonal-rail cards only (scoped class, not
   global) — evokes sông nước without literal water GIFs. Colour-only under RM. */
.market-card :deep(.card) { transition: box-shadow .4s var(--ease-out-expo); }
.market-card:hover :deep(.card) {
  box-shadow: var(--shadow-md), 0 0 0 1px rgba(var(--river-rgb), .18), 0 14px 28px -16px rgba(var(--river-rgb), .3);
}

/* Month-filter quick-reset chip — turns the filter UI into a curiosity loop:
   explore other months, always one tap back to "what's fresh now". */
.control-label-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.control-label-row .control-label { margin: var(--space-4) 0 var(--space-2); }
.season-reset-chip {
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  color: var(--accent-dark, var(--amber-600));
  background: rgba(var(--accent-rgb), .1);
  border: 1px solid rgba(var(--accent-rgb), .4);
  border-radius: var(--radius-full);
  padding: var(--space-05) var(--space-3);
  cursor: pointer;
  transition: background .2s var(--ease-out), transform .2s var(--ease-spring);
}
.season-reset-chip:hover { background: rgba(var(--accent-rgb), .18); }
.season-reset-chip:active { transform: scale(.94); }
.dark .season-reset-chip { color: var(--amber-500); background: rgba(var(--accent-rgb), .14); border-color: rgba(var(--accent-rgb), .5); }

/* OCOP teaser strip — slim signpost outward to /ocop (not a competing
   deep-dive rail); information-scent card, contact-only site, no CTA verb. */
.ocop-teaser-strip { padding-block: 0; }
.ocop-teaser-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border: .5px solid var(--line);
  border-radius: var(--radius-lg);
  background: linear-gradient(90deg, rgba(var(--secondary-rgb), .06), transparent);
  text-decoration: none;
  color: var(--ink);
  transition: border-color .25s var(--ease-out), box-shadow .25s var(--ease-out), transform .2s var(--ease-spring-gentle);
}
.ocop-teaser-link:hover {
  border-color: rgba(var(--secondary-rgb), .5);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}
.ocop-teaser-icon { font-size: 1.3rem; flex-shrink: 0; }
.ocop-teaser-copy { flex: 1; font-size: var(--text-sm); color: var(--muted); }
.ocop-teaser-copy strong { color: var(--ink); font-weight: var(--weight-semibold); }
.ocop-teaser-arrow { color: var(--secondary-fg, var(--secondary)); font-weight: var(--weight-semibold); flex-shrink: 0; }
.dark .ocop-teaser-link { background: linear-gradient(90deg, rgba(var(--secondary-rgb), .1), transparent); }

@media (prefers-reduced-motion: reduce) {
  .season-reset-chip:active { transform: none; }
  .ocop-teaser-link:hover { transform: none; }
}

@media (max-width: 640px) {
  .ocop-teaser-link { padding: var(--space-3) var(--space-4); }
}
</style>
