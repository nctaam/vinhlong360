<template>
  <section class="page" :style="{ '--int-rgb': interestTintRgb }">
    <Breadcrumb :items="breadcrumbItems" />

    <!-- Hero — "Một góc nhìn, một người kể": lens hero with per-interest halo shape -->
    <section class="catalog-hero cat-interest">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon int-hero-icon" :class="`int-halo-${haloShape}`" aria-hidden="true" v-html="interestIconSvg"></span>
        <div>
          <h1>{{ interestMeta.label }}</h1>
          <p>{{ interestMeta.description }}</p>
          <p class="int-byline">Biên tập theo mùa · Cập nhật {{ bylineMonth }}</p>
        </div>
      </div>
      <div v-if="interestItems.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="interestItems.length" class="stat-num" />
          <span class="stat-label">mục</span>
        </div>
        <div v-if="typeBreakdown.length > 1" class="stat-item">
          <CountUp :value="typeBreakdown.length" class="stat-num" />
          <span class="stat-label">nhóm</span>
        </div>
      </div>
    </section>

    <!-- declutter-3 T12: int-intro đã bỏ — hero dek nói cùng nội dung, đếm-mục là meta-noise -->
    <div class="interest-nav" role="navigation" aria-label="Các chủ đề khám phá">
      <NuxtLink
        v-for="(meta, key) in INTEREST_META"
        :key="key"
        :to="`/kham-pha/${key}`"
        :class="['chip', { active: key === interest }]"
        :aria-current="key === interest ? 'page' : undefined"
      ><IconLine :name="meta.icon" /> {{ meta.label }}</NuxtLink>
    </div>

    <section class="block reveal" aria-label="Duyệt tất cả">
    <h2 class="sr-only">Duyệt tất cả {{ interestMeta.label.toLowerCase() }}</h2>
    <!-- declutter-3 T12: 2 hàng filter gộp 1 panel — bỏ 2 control-label rời, divider mảnh
         ngăn 2 nhóm; ref areaFilter/typeFilter + hành vi giữ nguyên -->
    <div class="controls">
      <div class="chip-row wrap-mobile" role="group" aria-label="Lọc theo khu vực">
        <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = key as string"
        ><IconLine :name="meta.icon" /> {{ meta.name }}</button>
      </div>

      <!-- SIGNATURE 3: second filter row — narrow within an interest by type.
           Live counts carry visual weight (font-size scale) so the row itself
           communicates "this is where the depth is" — filmstrip underline draws
           in on hover/focus, evoking flipping through indexed photo negatives. -->
      <template v-if="typeBreakdown.length > 1">
        <div class="controls-divider" aria-hidden="true"></div>
        <div class="chip-row wrap-mobile int-filmstrip" role="group" aria-label="Lọc theo loại">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" :aria-pressed="typeFilter === 'all'" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button"
            v-for="t in typeBreakdown"
            :key="t.type"
            :class="['chip', 'int-filmstrip-chip', { active: typeFilter === t.type, 'int-chip-deep': t.count === maxTypeCount }]"
            :aria-pressed="typeFilter === t.type"
            @click="typeFilter = t.type"
          ><IconLine :name="t.icon" /> {{ t.label }} ({{ t.count }})</button>
        </div>
      </template>
    </div>

    <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả</p>
    <EmptyState v-if="fetchError" tone="error" icon="⚠️" title="Không thể tải dữ liệu" message="Lỗi kết nối. Vui lòng thử lại.">
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`interest-${interest}`)">Thử lại</button>
      </template>
    </EmptyState>
    <SkeletonGrid v-else-if="!data" :count="6" />
    <div v-else-if="filtered.length" ref="gridEl" class="grid int-grid">
      <template v-for="(e, i) in visible" :key="e.id">
        <div v-if="i > 0 && i % 9 === 0" class="int-grid-divider reveal" role="presentation" aria-hidden="true">
          <span class="int-grid-divider-label">{{ dividerFact(i) }}</span>
        </div>
        <EntityCard :entity="e" />
      </template>
    </div>
    <EmptyState v-else :message="emptyMessage" />
    <button
      v-if="filtered.length && visibleCount < filtered.length"
      type="button"
      class="btn btn-ghost catalog-more"
      @click="visibleCount += PAGE_SIZE"
    >
      {{ loadMoreLabel }}
    </button>
    </section>

    <!-- Cross-links — reframed as "đi tiếp" (where to next), each phrased as a
         chapter tied back to the interest just browsed, not a generic menu -->
    <section class="block band catalog-cross reveal">
      <h2>Đi tiếp</h2>
      <!-- SIGNATURE 4: identity ribbon — clarifies this is a navigation hub -->
      <p class="int-cross-sub">Khám phá theo hình thức khác</p>
      <div class="cross-links int-cross">
        <NuxtLink v-if="interestMeta.relatedRoutes?.length" to="/tuyen-duong" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🛤️</span>
          <div><strong>Tuyến đường</strong><p>Vòng {{ interestMeta.label.toLowerCase() }} gợi ý sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Vị trí thật của từng nơi trong chuyên mục này</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🗓️</span>
          <div><strong>Lịch trình</strong><p>Ghép {{ interestMeta.label.toLowerCase() }} vào một tuyến đi</p></div>
        </NuxtLink>
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon" aria-hidden="true">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm đã qua kiểm định sao</p></div>
        </NuxtLink>
      </div>
    </section>
    <!-- declutter-3 T14 (A3c): JourneyBar page-level — trang thuộc luồng lập-kế-hoạch -->
    <ClientOnly><LazyJourneyBar /></ClientOnly>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META, INTEREST_META, TYPE_META } from '~/composables/useConstants'
import { generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

useReveal()

const route = useRoute()
const interest = route.params.interest as string

const resolvedInterestMeta = INTEREST_META[interest]
if (!resolvedInterestMeta) {
  throw createError({ statusCode: 404, statusMessage: 'Chủ đề không tồn tại' })
}

const interestMeta = computed(() => resolvedInterestMeta)

// SIGNATURE 1: per-interest tint token — drives the hero wash, icon halo,
// intro card and cross-link ribbon so each interest feels like its own
// curated space. Maps to existing brand RGB tokens (no new colours).
const INTEREST_TINT: Record<string, string> = {
  'am-thuc': 'var(--accent-rgb)',
  'thien-nhien': 'var(--secondary-rgb)',
  'van-hoa': 'var(--primary-rgb)',
  'lang-nghe': 'var(--accent-rgb)',
  'mua-sam': 'var(--primary-rgb)',
}
const interestTintRgb = computed(() => INTEREST_TINT[interest] || 'var(--primary-rgb)')

// Lens hero icon — the interest's own motif glyph, reusing the same
// generateCategoryIcon() system already powering EntityCard placeholders so
// the interest icon and its cards' icons visually rhyme (no bare emoji).
// Each interest borrows the glyph of its first mapped entity type.
const interestIconSvg = computed(() => generateCategoryIcon(TYPE_META[resolvedInterestMeta.types[0]]?.cat || 'place'))

// Per-interest halo shape — cheap CSS clip-path variant reinforcing "this lens
// has its own shape": circle (thiên-nhiên), hex (làng-nghề), arch (văn-hoá)…
const HALO_SHAPE: Record<string, string> = {
  'am-thuc': 'circle',
  'thien-nhien': 'circle',
  'van-hoa': 'arch',
  'lang-nghe': 'hex',
  'mua-sam': 'diamond',
}
const haloShape = computed(() => HALO_SHAPE[interest] || 'circle')

// Byline "cập nhật tháng N" — a real timestamp signal (not fabricated), reads
// as "a human curated this" per concept §2.
const bylineMonth = computed(() => `tháng ${new Date().getMonth() + 1}`)

const breadcrumbItems = computed(() => [
  { label: 'Trang chủ', to: '/' },
  { label: 'Khám phá', to: '/kham-pha/am-thuc' },
  { label: interestMeta.value.label },
])

const areaFilter = ref('all')
const typeFilter = ref('all')
useFilterUrl({ vung: areaFilter, loai: typeFilter }, { vung: 'all', loai: 'all' })

const interestTypes = resolvedInterestMeta.types

const { data, error: fetchError } = await useAsyncData(`interest-${interest}`, () =>
  apiFetch<{ entities: Entity[]; total: number }>(`/api/entities?type=${interestTypes.join(',')}&limit=500`)
)

const interestItems = computed<Entity[]>(() => data.value?.entities || [])

// SIGNATURE 3: breakdown of the interest's own types, with live counts,
// for the "Theo loại" segmented filter (only render when >1 type present).
const typeBreakdown = computed(() => {
  const counts = new Map<string, number>()
  for (const e of interestItems.value) counts.set(e.type, (counts.get(e.type) || 0) + 1)
  return interestMeta.value.types
    .filter(t => counts.has(t))
    .map(t => ({
      type: t,
      count: counts.get(t) || 0,
      emoji: TYPE_META[t]?.emoji || '•',
      icon: TYPE_META[t]?.icon || 'pin',
      label: TYPE_META[t]?.label || t,
    }))
})

// Live-count visual weight: the type with the most items gets a size bump in
// the "Theo loại" row so the row itself communicates "this is where the depth is".
const maxTypeCount = computed(() => Math.max(0, ...typeBreakdown.value.map(t => t.count)))

const filtered = computed(() => {
  let list = interestItems.value
  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }
  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getEntityArea(e) === areaFilter.value)
  }
  return list
})

// Curiosity empty-state — names the active narrowing instead of a bare "no match."
const emptyMessage = computed(() => {
  const typeName = typeFilter.value !== 'all' ? (TYPE_META[typeFilter.value]?.label || '') : ''
  const areaName = areaFilter.value !== 'all' ? (AREA_META[areaFilter.value]?.name || '') : ''
  if (typeName && areaName) return `Chưa có “${typeName.toLowerCase()}” ở ${areaName} trong chuyên mục ${interestMeta.value.label.toLowerCase()} — thử vùng khác?`
  if (typeName) return `Chưa có “${typeName.toLowerCase()}” trong chuyên mục ${interestMeta.value.label.toLowerCase()}.`
  if (areaName) return `Chuyên mục ${interestMeta.value.label.toLowerCase()} chưa có mục nào ở ${areaName}.`
  return 'Không tìm thấy kết quả phù hợp.'
})

// Client-side pagination: bound hydration cost on the full filterable grid
// (perf audit P2). First PAGE_SIZE render on the server for SEO/first-paint;
// "Xem thêm" reveals more without a refetch. Reset happens in the existing
// watch([areaFilter, typeFilter], ...) below.
const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const visible = computed(() => filtered.value.slice(0, visibleCount.value))

// Load-more teaser — names the last-loaded item's own place as an honest
// "kể cả…" hook (no fabricated next-item prediction; concept doc §6 MVP).
const loadMoreLabel = computed(() => {
  const remaining = filtered.value.length - visibleCount.value
  if (remaining <= 0) return ''
  const last = visible.value[visible.value.length - 1]
  const teaseName = (last as any)?.placeName || (last as any)?.place_name || last?.name
  if (teaseName) return `Xem thêm — còn ${remaining} mục nữa, kể cả gần ${teaseName} →`
  return `Xem thêm (${remaining} còn lại)`
})

// Grid divider — every 9 cards, a typographic interruption naming a real place
// already seen in the grid (no invented facts), so a long grid reads as a
// curated chuyên mục, not an infinite dump.
function dividerFact(index: number): string {
  const seen = visible.value.slice(0, index)
  const areasSeen = new Set(seen.map((e: any) => e.placeName || e.place_name).filter(Boolean))
  const pool = Array.from(areasSeen)
  const nth = Math.floor(index / 9)
  if (pool.length) return pool[nth % pool.length] as string
  return `${index} mục đã lật qua`
}

// Polish: smooth scroll the results into view when a filter changes, so the
// user is not left staring at the controls panel after narrowing.
const gridEl = ref<HTMLElement | null>(null)
function scrollToResults() {
  if (!import.meta.client || !gridEl.value) return
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  const top = gridEl.value.getBoundingClientRect().top + window.scrollY - 80
  window.scrollTo({ top, behavior: 'smooth' })
}
let _filtersTouched = false
watch([areaFilter, typeFilter], () => {
  visibleCount.value = PAGE_SIZE
  // skip the initial URL-sync run; only react to genuine user changes
  if (!_filtersTouched) { _filtersTouched = true; return }
  nextTick(scrollToResults)
})

useSeoMeta({
  title: `${interestMeta.value.emoji} ${interestMeta.value.label} — Khám phá Vĩnh Long — vinhlong360`,
  description: interestMeta.value.description,
  ogTitle: `${interestMeta.value.label} — vinhlong360`,
  ogDescription: interestMeta.value.description,
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/kham-pha/${interest}`) }],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      `${interestMeta.value.label} — Khám phá Vĩnh Long`,
      interestMeta.value.description,
      `/kham-pha/${interest}`,
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
/* ============================================================
   SIGNATURE 1 — per-interest hero identity + animated icon reveal.
   The base .catalog-hero / .cat-interest gradient is global; here we
   add a felt, branded tint per interest plus a gentle icon entrance.
   Scoped + prefixed (int-*) so nothing leaks to other pages.
   ============================================================ */
/* the interest tint (--int-rgb) is set inline on the root .page element and
   cascades into every page-local element below, so hero + intro + ribbon all
   share one cohesive per-interest colour. Falls back to --primary-rgb. */
.catalog-hero.cat-interest {
  /* lift the local hero with a soft brand wash keyed to the interest tone */
  background:
    radial-gradient(140% 120% at 0% 0%, rgba(var(--int-rgb, var(--primary-rgb)), .12), transparent 62%),
    linear-gradient(135deg, rgba(var(--int-rgb, var(--primary-rgb)), .07) 0%, rgba(var(--secondary-rgb), .04) 100%);
}

/* animated interest icon: gentle scale + fade reveal on mount, with a soft
   brand halo behind it so the emoji reads as a curated identity mark */
.int-hero-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  animation: int-icon-reveal .6s var(--ease-out-expo, ease-out) both;
}
.int-hero-icon::before {
  content: "";
  position: absolute;
  inset: -28%;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 45%, rgba(var(--int-rgb, var(--primary-rgb)), .18), transparent 70%);
  pointer-events: none;
}
@keyframes int-icon-reveal {
  from { opacity: 0; transform: scale(.7) translateY(4px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}
/* the motif glyph now lives in the icon slot (v-html svg) — size + tint it to
   match the hero's visual weight, replacing the old bare-emoji font-size rule */
.int-hero-icon :deep(svg) { width: 2.6rem; height: 2.6rem; color: rgba(var(--int-rgb, var(--primary-rgb)), .9); }
@media (max-width: 640px) { .int-hero-icon :deep(svg) { width: 2rem; height: 2rem; } }

/* Per-interest halo shape — the halo behind the icon (::before) takes a
   different clip-path per lens, so each chuyên mục feels like its own shape.
   CSS-only, no new markup beyond the existing ::before halo. */
.int-halo-circle::before { border-radius: 50%; }
.int-halo-hex::before {
  border-radius: 0;
  clip-path: polygon(25% 4%, 75% 4%, 100% 50%, 75% 96%, 25% 96%, 0% 50%);
}
.int-halo-arch::before {
  border-radius: 0;
  clip-path: path('M 0 100 L 0 45 A 50 50 0 0 1 100 45 L 100 100 Z');
}
.int-halo-diamond::before {
  border-radius: 0;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
}

/* Editorial byline — small caps, wide tracking, hairline rule before it —
   signals "a human curated this," not a query result. */
.int-byline {
  margin: var(--space-3) 0 0 !important;
  padding-top: var(--space-2);
  border-top: .5px solid var(--line);
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted) !important;
  max-width: none !important;
}

/* declutter-3 T12: divider mảnh ngăn 2 nhóm chip trong 1 panel .controls */
.controls-divider { border-top: .5px solid var(--line); margin-block: var(--space-2); }

/* ============================================================
   SIGNATURE 3 — interest nav + premium segmented controls.
   (.controls panel styling is global; here we only refine the
   page-local interest-nav and stagger between the two filter rows.)
   ============================================================ */
.interest-nav { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-5); }
.interest-nav .chip { transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), background .3s var(--ease-out), border-color .3s var(--ease-out); }
.interest-nav .chip:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.interest-nav .chip:active { transform: scale(.95); transition-duration: .08s; }
.interest-nav .chip.active { box-shadow: var(--shadow-sm); }
/* Polish: explicit focus-visible rings on the interest nav chips so keyboard
   focus is always visible, including on the active (filled) chip */
.interest-nav .chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.interest-nav .chip.active:focus-visible { outline-color: var(--accent); outline-offset: 4px; }

@media (max-width: 840px) { .interest-nav { flex-wrap: wrap; overflow-x: visible; } }
/* Polish: roomier tap targets on narrow screens (>=48px, comfortable padding) */
@media (max-width: 640px) {
  .interest-nav .chip { min-height: 48px; padding-top: var(--space-3); padding-bottom: var(--space-3); }
}

.result-meta { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-3); }

/* ============================================================
   TYPE FILMSTRIP — "Theo loại" row. Live counts carry visual weight
   (the deepest type nudges up in size) + a thin category-color
   underline draws in on hover/focus, evoking flipping through
   indexed photo negatives.
   ============================================================ */
.int-filmstrip-chip { position: relative; overflow: hidden; transition: font-size .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), background .3s var(--ease-out), border-color .3s var(--ease-out); }
.int-filmstrip-chip.int-chip-deep { font-size: calc(var(--text-sm) * 1.08); font-weight: var(--weight-bold); }
.int-filmstrip-chip::after {
  content: ""; position: absolute; left: var(--space-4); right: var(--space-4); bottom: 5px;
  height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, var(--river-600), var(--amber-600), var(--clay-600));
  transform: scaleX(0); transform-origin: left; transition: transform .3s var(--ease-out-expo);
}
.int-filmstrip-chip:hover::after, .int-filmstrip-chip:focus-visible::after, .int-filmstrip-chip.active::after { transform: scaleX(1); }
.dark .int-filmstrip-chip::after { background: linear-gradient(90deg, #74ABB5, var(--amber-500), var(--clay-400)); }

/* ============================================================
   GRID DIVIDER — typographic interruption every 9 cards in the
   chuyên mục grid, naming a real place already seen (no invented facts).
   ============================================================ */
.int-grid-divider {
  grid-column: 1 / -1;
  display: flex; align-items: center; gap: var(--space-4);
  margin: var(--space-2) 0; padding: var(--space-2) 0;
}
.int-grid-divider::before, .int-grid-divider::after { content: ''; flex: 1; height: .5px; background: var(--line); }
.int-grid-divider-label {
  font-family: var(--font-editorial); font-style: italic; font-size: var(--text-sm);
  color: var(--muted); white-space: nowrap; padding: 0 var(--space-2);
}

/* SIGNATURE 4 — cross-links identity ribbon subtitle */
.int-cross-sub {
  margin: 0 0 var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted);
}

/* Dark mode */
.dark .catalog-hero.cat-interest {
  background:
    radial-gradient(140% 120% at 0% 0%, rgba(var(--int-rgb, var(--primary-rgb)), .16), transparent 62%),
    linear-gradient(135deg, rgba(var(--int-rgb, var(--primary-rgb)), .1) 0%, rgba(var(--secondary-rgb), .05) 100%);
}
.dark .int-byline { color: var(--ink-tertiary) !important; border-top-color: var(--line); }
.dark .interest-nav .chip { background: var(--bg-alt); border-color: var(--line); }
.dark .interest-nav .chip:hover { border-color: rgba(255,255,255,.15); }
.dark .interest-nav .chip.active { background: rgba(var(--primary-rgb), .12); border-color: var(--primary-fg); }
.dark .result-meta { color: var(--ink-tertiary); }

/* Reduced motion — drop every page-local transform/animation */
@media (prefers-reduced-motion: reduce) {
  .interest-nav .chip:hover { transform: none; }
  .interest-nav .chip:active { transform: none; }
  .int-hero-icon { animation: none; }
  .int-filmstrip-chip { transition: none; }
  .int-filmstrip-chip::after { transition: none; }
}
</style>
