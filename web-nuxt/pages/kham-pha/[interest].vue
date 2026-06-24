<template>
  <section class="page" :style="{ '--int-rgb': interestTintRgb }">
    <Breadcrumb :items="breadcrumbItems" />

    <!-- Hero -->
    <section class="catalog-hero cat-interest">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon int-hero-icon" aria-hidden="true">{{ interestMeta.emoji }}</span>
        <div>
          <h1>{{ interestMeta.label }}</h1>
          <p>{{ interestMeta.description }}</p>
        </div>
      </div>
      <div v-if="filtered.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ filtered.length }}</span>
          <span class="stat-label">mục</span>
        </div>
        <div v-if="typeBreakdown.length > 1" class="stat-item">
          <span class="stat-num">{{ typeBreakdown.length }}</span>
          <span class="stat-label">nhóm</span>
        </div>
      </div>
    </section>

    <!-- SIGNATURE 2: Curated collection intro — "Trong chuyên mục này" -->
    <div v-if="data && filtered.length" class="int-intro reveal">
      <p class="int-intro-text">
        <span class="int-intro-emoji" aria-hidden="true">✨</span>
        <span>Trong chuyên mục này: {{ collectionNarrative }}</span>
      </p>
    </div>

    <div class="interest-nav" role="navigation" aria-label="Các chủ đề khám phá">
      <NuxtLink
        v-for="(meta, key) in INTEREST_META"
        :key="key"
        :to="`/kham-pha/${key}`"
        :class="['chip', { active: key === interest }]"
        :aria-current="key === interest ? 'page' : undefined"
      >{{ meta.emoji }} {{ meta.label }}</NuxtLink>
    </div>

    <div class="controls">
      <p class="control-label">Khu vực</p>
      <div class="chip-row wrap-mobile" role="group" aria-label="Lọc theo khu vực">
        <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = key as string"
        >{{ meta.emoji }} {{ meta.name }}</button>
      </div>

      <!-- SIGNATURE 3: second filter row — narrow within an interest by type -->
      <template v-if="typeBreakdown.length > 1">
        <p class="control-label">Theo loại</p>
        <div class="chip-row wrap-mobile" role="group" aria-label="Lọc theo loại">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" :aria-pressed="typeFilter === 'all'" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button"
            v-for="t in typeBreakdown"
            :key="t.type"
            :class="['chip', { active: typeFilter === t.type }]"
            :aria-pressed="typeFilter === t.type"
            @click="typeFilter = t.type"
          >{{ t.emoji }} {{ t.label }} ({{ t.count }})</button>
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
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
    </div>
    <EmptyState v-else message="Không tìm thấy kết quả phù hợp." />

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <!-- SIGNATURE 4: identity ribbon — clarifies this is a navigation hub -->
      <p class="int-cross-sub">Khám phá theo hình thức khác</p>
      <div class="cross-links int-cross">
        <NuxtLink v-if="interestMeta.relatedRoutes?.length" to="/tuyen-duong" class="cross-card">
          <span class="cross-icon">🛤️</span>
          <div><strong>Tuyến đường</strong><p>Vòng khám phá gợi ý</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm sao</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META, INTEREST_META, TYPE_META } from '~/composables/useConstants'

useReveal()

const route = useRoute()
const interest = route.params.interest as string

if (!INTEREST_META[interest]) {
  throw createError({ statusCode: 404, statusMessage: 'Chủ đề không tồn tại' })
}

const interestMeta = computed(() => INTEREST_META[interest])

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

const breadcrumbItems = computed(() => [
  { label: 'Trang chủ', to: '/' },
  { label: 'Khám phá', to: '/kham-pha/am-thuc' },
  { label: interestMeta.value.label },
])

const areaFilter = ref('all')
const typeFilter = ref('all')
useFilterUrl({ vung: areaFilter, loai: typeFilter }, { vung: 'all', loai: 'all' })

const { data, error: fetchError } = await useAsyncData(`interest-${interest}`, () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?limit=200')
)

// Items matching this interest, before the area/type filters are applied.
const interestItems = computed<Entity[]>(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => interestMeta.value.types.includes(e.type))
})

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
      label: TYPE_META[t]?.label || t,
    }))
})

const filtered = computed(() => {
  let list = interestItems.value
  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }
  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => (e.place_area || e.area) === areaFilter.value)
  }
  return list
})

// SIGNATURE 2: a short, data-driven narrative of what this collection holds —
// built only from real counts (no fabricated facts; Track-H safe).
const collectionNarrative = computed(() => {
  const parts = typeBreakdown.value.map(t => `${t.count} ${t.label.toLowerCase()}`)
  if (!parts.length) return interestMeta.value.description
  if (parts.length === 1) return `${parts[0]} đang được tổng hợp ở khắp Vĩnh Long, Bến Tre và Trà Vinh.`
  const last = parts.pop()
  return `từ ${parts.join(', ')} đến ${last} — trải khắp Vĩnh Long, Bến Tre và Trà Vinh.`
})

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
  // skip the initial URL-sync run; only react to genuine user changes
  if (!_filtersTouched) { _filtersTouched = true; return }
  nextTick(scrollToResults)
})

useSeoMeta({
  title: `${interestMeta.value.emoji} ${interestMeta.value.label} — Khám phá miền Tây — vinhlong360`,
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
      `${interestMeta.value.label} — Khám phá miền Tây`,
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

/* ============================================================
   SIGNATURE 2 — curated collection intro card
   ============================================================ */
.int-intro {
  margin: 0 0 var(--space-4);
  padding: var(--space-4) var(--space-5);
  border: .5px solid rgba(var(--int-rgb, var(--primary-rgb)), .2);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(var(--int-rgb, var(--primary-rgb)), .07), transparent 65%),
    var(--card);
  box-shadow: var(--shadow-xs);
}
.int-intro-text {
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--ink);
}
.int-intro-emoji { font-size: 1.2rem; line-height: 1.3; flex-shrink: 0; }

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
.dark .int-intro {
  border-color: rgba(var(--int-rgb, var(--primary-rgb)), .26);
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(var(--int-rgb, var(--primary-rgb)), .1), transparent 65%),
    var(--card);
}
.dark .int-intro-text { color: var(--ink); }
.dark .interest-nav .chip { background: var(--bg-alt); border-color: var(--line); }
.dark .interest-nav .chip:hover { border-color: rgba(255,255,255,.15); }
.dark .interest-nav .chip.active { background: rgba(var(--primary-rgb), .12); border-color: var(--primary-fg); }
.dark .result-meta { color: var(--ink-tertiary); }

/* Reduced motion — drop every page-local transform/animation */
@media (prefers-reduced-motion: reduce) {
  .interest-nav .chip:hover { transform: none; }
  .interest-nav .chip:active { transform: none; }
  .int-hero-icon { animation: none; }
}
</style>
