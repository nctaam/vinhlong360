<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🗓️</span>
        <div>
          <span class="itin-eyebrow">Lịch trình gợi ý · 3 khu vực</span>
          <h1 class="day-arc-title">Chọn một ngày ở Vĩnh Long</h1>
          <p>Có ngày chỉ cần nửa buổi ở miệt vườn, có ngày cần trọn ba hôm để đi hết một khúc sông. Chọn nhịp ngày phù hợp — phần còn lại, tụi mình đã sắp sẵn.</p>
        </div>
      </div>
      <div v-if="itineraries?.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="itineraries.length" class="stat-num" />
          <span class="stat-label">lịch trình</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>

      <!-- Signature: day-arc strip — dawn→noon→dusk gradient with 4 fixed
           time-of-day marks. Thesis visual: "chọn một hình dạng ngày phù hợp
           với bạn" made literal before a single word of copy is read.
           Horizontal + time-of-day axis — distinct from tuyen-duong's vertical
           per-card .route-rail (which plots a path, not a day's rhythm). -->
      <div class="day-arc day-arc-strip" role="img" aria-label="Dải màu tượng trưng nhịp một ngày: sáng sớm, trưa, chiều, hoàng hôn">
        <span class="day-arc-track" aria-hidden="true"></span>
        <span v-for="m in DAY_MARKS" :key="m.key" class="day-arc-mark" :style="{ left: m.pct + '%' }">
          <span class="day-arc-glyph" aria-hidden="true">{{ m.glyph }}</span>
          <span class="day-arc-label">{{ m.label }}</span>
        </span>
      </div>
    </section>

    <!-- Đã lưu (client-only, từ localStorage) -->
    <ClientOnly>
      <section v-if="count > 0" class="block saved-section reveal">
        <div class="section-head">
          <h2>❤️ Đã lưu <span class="saved-count">({{ count }})</span></h2>
          <button type="button" class="btn btn-sm btn-ghost danger" @click="clearAll">Xóa tất cả</button>
        </div>
        <div class="journey-stats">
          <div v-for="(items, type) in byType" :key="type" class="js-item">
            <IconLine :name="getTypeMeta(type).icon" class="js-emoji" />
            <strong>{{ items.length }}</strong>
            <span>{{ getTypeMeta(type).label }}</span>
          </div>
        </div>
        <div class="scroll-row saved-row" role="region" tabindex="0" aria-label="Mục đã lưu">
          <SavedEntityCard v-for="fav in recentSaved" :key="fav.id" :item="fav" />
        </div>
        <div class="saved-cta">
          <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">📋 Tạo lịch trình từ danh sách đã lưu</NuxtLink>
        </div>
      </section>
    </ClientOnly>

    <!-- NEW: pace picker — "how much time do you have" before "which province" -->
    <section class="block band reveal">
      <div class="section-head">
        <h2 class="sediment-head">Chọn theo nhịp ngày</h2>
      </div>
      <div class="pace-chips" role="group" aria-label="Lọc theo nhịp ngày">
        <button type="button" :class="['pace-chip', { active: paceFilter === 'all' }]" :aria-pressed="paceFilter === 'all'" @click="paceFilter = 'all'">Tất cả nhịp</button>
        <button type="button"
          v-for="p in PACE_DEFS" :key="p.key"
          :class="['pace-chip', { active: paceFilter === p.key }]"
          :aria-pressed="paceFilter === p.key"
          @click="paceFilter = paceFilter === p.key ? 'all' : p.key"
        >
          <span class="pace-chip-glyph" aria-hidden="true">{{ p.glyph }}</span>
          <span class="pace-chip-label">{{ p.label }}</span>
          <span class="pace-chip-count">{{ countByPace(p.key) }}</span>
        </button>
      </div>
    </section>

    <!-- declutter-2 A5 (chiều ngược): quick-picks khu-vực đã bỏ — trang này trục chính
         là NHỊP NGÀY (pace-chips); chip-row khu vực trong controls là 1 đường filter
         khu vực duy nhất. countByArea giữ (hero areaCounts dùng). -->

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2 class="sediment-head">Lịch trình có sẵn — đi ngay không cần lên kế hoạch</h2>
      <p>Mỗi lịch trình được thiết kế dựa trên kinh nghiệm thực tế, sắp xếp các điểm đến theo thứ tự hợp lý về khoảng cách và thời gian. Bạn chỉ cần chọn lịch trình phù hợp với số ngày đi, sở thích (văn hoá, ẩm thực, thiên nhiên) và phương tiện (xe máy, ô tô, xuồng). Mỗi điểm dừng đều có thông tin thực tế: giờ mở cửa, giá tham khảo, mẹo di chuyển.</p>
      <p>Có thể kết hợp nhiều lịch trình hoặc tuỳ chỉnh — bỏ bớt điểm dừng, thêm điểm mới, thay đổi thứ tự. Tất cả lịch trình đều miễn phí và có thể lưu vào tài khoản để xem lại khi đi.</p>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      v-if="itineraries?.length"
      fact="Mỗi lịch trình được thiết kế dựa trên kinh nghiệm thực tế — lưu vào tài khoản để xem lại khi đi."
      icon="💡"
      :links="[
        { to: '/tao-lich-trinh', label: 'Tự tạo lịch trình' },
        { to: '/du-lich', label: 'Khám phá du lịch' },
      ]"
    />

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Lịch trình gợi ý</span>
    </div>

    <!-- Suggested itineraries -->
    <section ref="gridSection" class="block reveal">
      <div class="controls">
        <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
          <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
          <button type="button"
            v-for="(meta, key) in AREA_META" :key="key"
            :class="['chip', { active: areaFilter === key }]"
            :aria-pressed="areaFilter === key"
            @click="areaFilter = key as string"
          ><IconLine :name="meta.icon" /> {{ meta.name }}</button>
        </div>
      </div>

      <p class="result-meta" aria-live="polite">{{ filtered.length }} lịch trình</p>

      <EmptyState v-if="fetchError" icon="⚠️" title="Không tải được lịch trình" message="Có thể mạng đang chập chờn. Thử lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('itineraries')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!itineraries" :count="4" />
      <!-- "Shelves of days" — grouped by pace when browsing everything, so
           scanning feels like a shelf of curated days rather than a database
           table. A single-pace filter already narrows the list, so it stays
           one flat grid there (no redundant single-shelf header). -->
      <template v-else-if="filtered.length">
        <div v-if="paceFilter === 'all'" class="pace-shelves">
          <div v-for="shelf in paceShelves" :key="shelf.key" class="pace-shelf">
            <p class="pace-shelf-kicker">{{ shelf.glyph }} {{ shelf.label }}</p>
            <div class="grid itin">
              <ItineraryCard v-for="it in shelf.items" :key="it.id" :itinerary="it" />
            </div>
          </div>
        </div>
        <div v-else class="grid itin">
          <ItineraryCard v-for="it in filtered" :key="it.id" :itinerary="it" />
        </div>
      </template>
      <div v-else class="block empty-state itin-empty">
        <EmptyState icon="🗺️" title="Khám phá từ vùng khác" :message="emptyMessage">
          <template #actions>
            <button type="button" class="btn btn-outline" @click="areaFilter = 'all'">Xem tất cả khu vực</button>
            <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">Tạo lịch trình</NuxtLink>
          </template>
        </EmptyState>
      </div>

      <div class="block-cta">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">+ Tự tạo lịch trình</NuxtLink>
      </div>
    </section>

    <!-- Cross-links -->
    <section class="block band reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🍊</span>
          <div><strong>Đặc sản</strong><p>Mua quà Vĩnh Long</p></div>
        </NuxtLink>
      </div>
    </section>
    <!-- declutter-3 T14 (A3c): JourneyBar page-level — trang thuộc luồng lập-kế-hoạch -->
    <ClientOnly><LazyJourneyBar /></ClientOnly>
  </div>
</template>

<script setup lang="ts">
import type { Itinerary } from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'

useReveal()

const { favorites, byType, count, clear } = useFavorites()
const { confirmDialog } = useConfirm()
const recentSaved = computed(() => favorites.value.slice(0, 8))

async function clearAll() {
  if (await confirmDialog('Xóa tất cả mục đã lưu?', { danger: true, confirmText: 'Xóa' })) clear()
}

const areaFilter = ref('all')
const paceFilter = ref('all')
const gridSection = ref<HTMLElement | null>(null)

watch(areaFilter, () => {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
})

useFilterUrl({ vung: areaFilter, nhip: paceFilter }, { vung: 'all', nhip: 'all' })

// ── Day-arc strip (signature ambient device, §10) — 4 fixed time-of-day
// marks, no per-stop data on the list page (that's the detail page's job).
const DAY_MARKS = [
  { key: 'dawn', glyph: '🌅', label: 'Sáng sớm', pct: 6 },
  { key: 'noon', glyph: '☀️', label: 'Trưa', pct: 37 },
  { key: 'afternoon', glyph: '🌤️', label: 'Chiều', pct: 68 },
  { key: 'dusk', glyph: '🌇', label: 'Hoàng hôn', pct: 94 },
]

// ── Pace chips — "how much time do you have" as the first filter axis,
// computed client-side from itinerary.duration string heuristics (no schema
// change, per B2/additive-first).
const PACE_DEFS = [
  { key: 'half', glyph: '🌤️', label: 'Nửa ngày' },
  { key: 'full', glyph: '☀️', label: 'Trọn ngày' },
  { key: 'multi', glyph: '🌅', label: 'Nhiều ngày' },
] as const
type PaceKey = typeof PACE_DEFS[number]['key']

function paceOf(it: Itinerary): PaceKey {
  const d = (it.duration || '').toLowerCase()
  if (d.includes('nửa')) return 'half'
  const numbers = d.match(/\d+/g)?.map(Number) || []
  const maxDays = numbers.length ? Math.max(...numbers) : 1
  if (maxDays >= 2 || d.includes('đêm')) return 'multi'
  if (!d) {
    // No duration text at all — fall back to stop count as a proxy.
    const stopCount = it.stops?.length || 0
    return stopCount > 6 ? 'multi' : 'full'
  }
  return 'full'
}

function countByPace(key: PaceKey) {
  return (itineraries.value || []).filter((it: Itinerary) => paceOf(it) === key).length
}

const { data: itineraries, error: fetchError } = await useAsyncData('itineraries', () =>
  apiFetch<any[]>('/api/itineraries')
)

const areaCounts = computed(() => {
  return Object.entries(AREA_META)
    .map(([key, meta]) => ({ key, name: meta.name, count: countByArea(key) }))
    .filter(item => item.count > 0)
})

function itineraryMatchesArea(it: Itinerary, key: string) {
  if (it.area === key) return true
  const areas = Array.isArray(it.areas) ? it.areas : []
  return areas.includes(key)
}

function countByArea(key: string) {
  return (itineraries.value || []).filter((it: Itinerary) => itineraryMatchesArea(it, key)).length
}

const filtered = computed(() => {
  let list = itineraries.value || []
  if (areaFilter.value !== 'all') list = list.filter((it: Itinerary) => itineraryMatchesArea(it, areaFilter.value))
  if (paceFilter.value !== 'all') list = list.filter((it: Itinerary) => paceOf(it) === (paceFilter.value as PaceKey))
  return list
})

// Grouped "shelves of days" for the all-pace browse view (§3 list-page layout).
const paceShelves = computed(() => {
  return PACE_DEFS
    .map(p => ({ ...p, items: filtered.value.filter((it: Itinerary) => paceOf(it) === p.key) }))
    .filter(shelf => shelf.items.length > 0)
})

const emptyMessage = computed(() => {
  const meta = AREA_META[areaFilter.value as keyof typeof AREA_META]
  const regionName = meta?.name || 'Khu vực này'
  return `${regionName} chưa có lịch trình gợi ý, nhưng các vùng khác đang chờ bạn khám phá — hoặc tự tạo một lịch trình riêng theo sở thích.`
})

useSeoMeta({
  title: 'Lịch trình — vinhlong360',
  description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn — chỉ cần chọn và đi. Hoặc tự tạo lịch trình cá nhân theo sở thích.',
  ogTitle: 'Lịch trình — vinhlong360',
  ogDescription: 'Tuyến tham quan Vĩnh Long được thiết kế sẵn — chỉ cần chọn và đi.',
  ogImage: '/icons/icon-512.png',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/lich-trinh') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Lịch trình gợi ý',
        description: 'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn.',
        url: 'https://vinhlong360.vn/lich-trinh',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Lịch trình' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itineraryItemListJsonLd(
      'Lịch trình gợi ý',
      'Tuyến tham quan Vĩnh Long, Bến Tre, Trà Vinh được thiết kế sẵn.',
      '/lich-trinh',
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
/* ══════════════════════════════════════════════════════════════════════
   Day-arc strip — signature moment (§10). Dawn→noon→dusk gradient with 4
   fixed time-of-day marks, sitting under the masthead as an ambient thesis
   visual: "chọn một hình dạng ngày phù hợp với bạn" made literal. Horizontal
   axis reads time-of-day, distinct from tuyen-duong's vertical per-card
   .route-rail (which plots a route path). Reused populated on the detail
   page's hero as .day-arc-hero (real per-stop dots).
   ══════════════════════════════════════════════════════════════════════ */
/* Local eyebrow — events.css's shared .dateline-eyebrow is page-scoped to
   le-hoi/su-kien only (not global), so this page carries its own copy of the
   same recipe rather than importing shared CSS out of scope. */
.itin-eyebrow {
  display: block; font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--muted);
  margin: 0 0 var(--space-2);
}
.day-arc-title { font-family: var(--font-editorial); }
.day-arc { position: relative; margin-top: var(--space-6); height: 56px; }
.day-arc-track {
  position: absolute; left: 0; right: 0; top: 18px; height: 3px; border-radius: var(--radius-full);
  background: linear-gradient(90deg,
    var(--river-600) 0%,
    color-mix(in srgb, var(--river-600) 40%, var(--amber-600) 60%) 30%,
    var(--amber-600) 50%,
    color-mix(in srgb, var(--amber-600) 45%, var(--clay-600) 55%) 72%,
    var(--clay-600) 100%);
  /* one-time left-to-right draw-on, "a day unfolding" (§5) */
  transform-origin: left center;
  animation: dayArcDraw .6s var(--ease-out-expo) both;
  animation-delay: .1s;
}
@keyframes dayArcDraw { from { transform: scaleX(0); } }
.day-arc-mark { position: absolute; top: 0; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; gap: 2px; }
.day-arc-glyph {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; font-size: .78rem; line-height: 1;
  background: var(--card); border-radius: 50%; box-shadow: var(--shadow-xs);
}
.day-arc-label { font-size: var(--text-2xs); color: var(--muted); text-transform: uppercase; letter-spacing: var(--tracking-caps); font-weight: var(--weight-semibold); white-space: nowrap; }
.dark .day-arc-glyph { background: var(--card); box-shadow: 0 1px 3px rgba(var(--black-rgb),.4); }

/* ── Pace chips — "how much time do you have," the first filter axis ── */
.pace-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.pace-chip {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-4); border-radius: var(--radius-full);
  border: .5px solid var(--line); background: var(--card); color: var(--ink);
  font-size: var(--text-sm); font-weight: var(--weight-medium); cursor: pointer;
  transition: transform .3s var(--ease-spring-gentle), background .25s var(--ease-out), border-color .25s var(--ease-out), box-shadow .25s var(--ease-out);
}
.pace-chip-glyph { font-size: var(--text-base); line-height: 1; }
.pace-chip-count { font-size: var(--text-2xs); color: var(--muted); font-variant-numeric: tabular-nums; }
.pace-chip:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); border-color: var(--border); }
.pace-chip:active { transform: scale(.96); transition-duration: .08s; }
.pace-chip.active { background: var(--secondary); border-color: var(--secondary); color: var(--text-on-dark, var(--white)); }
.pace-chip.active .pace-chip-count { color: rgba(var(--white-rgb),.85); }
.dark .pace-chip { background: var(--card); border-color: var(--line); }
.dark .pace-chip.active { background: var(--secondary); border-color: var(--secondary); }

/* ── Pace shelves — "shelves of days" grouping when browsing all paces ── */
.pace-shelves { display: flex; flex-direction: column; gap: var(--space-8); }
.pace-shelf-kicker {
  font-family: var(--font-editorial); font-size: var(--text-lg); font-weight: 600;
  margin: 0 0 var(--space-4); position: relative; padding-left: var(--space-4);
}
.pace-shelf-kicker::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 4px; height: 1.05em; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .pace-shelf-kicker::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }

.saved-section { margin-bottom: var(--space-4); padding-bottom: var(--space-6); border-bottom: .5px solid var(--line); }
.saved-count { font-weight: var(--weight-normal); color: var(--muted); font-size: var(--text-base); }
.saved-cta { text-align: center; margin-top: var(--space-4); }
.saved-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.saved-row { margin-top: var(--space-3); }
.saved-row .card { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.saved-row .card:hover { transform: translateY(-5px); box-shadow: var(--shadow-lg); }
.saved-row .card:active { transform: translateY(-1px) scale(.98); transition-duration: .08s; }

.journey-stats { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
.js-item { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: var(--bg-alt); border-radius: var(--radius-md); font-size: var(--text-sm); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.js-item:hover { background: var(--card); transform: translateY(-2px); box-shadow: var(--shadow-xs); }
.js-item:active { transform: scale(.97); transition-duration: .08s; }
.js-emoji { font-size: var(--text-lg); }

/* Premium hero stat-items: brand-tinted surface + accent border */
.catalog-hero .stat-item {
  background: rgba(var(--secondary-rgb), .04);
  border-left: 3px solid var(--secondary);
  border-radius: var(--radius-sm);
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.catalog-hero .stat-item:hover {
  background: rgba(var(--secondary-rgb), .08);
  transform: translateY(-2px);
}
.catalog-hero .stat-item:hover .stat-num { letter-spacing: .02em; }
.dark .catalog-hero .stat-item { background: rgba(var(--secondary-rgb), .08); }
.dark .catalog-hero .stat-item:hover { background: rgba(var(--secondary-rgb), .14); }

/* Itinerary empty-state wrapper rhythm */
.itin-empty { margin-top: var(--space-2); }

.block-cta { margin-top: var(--space-6); text-align: center; }
.block-cta .btn:active { transform: scale(.97); transition-duration: .08s; }
.danger { color: var(--error); }

/* Dark mode */
.dark .saved-section { border-bottom-color: var(--line); }
.dark .js-item { background: rgba(var(--white-rgb),.04); }
.dark .js-item:hover { background: rgba(var(--white-rgb),.07); }
.dark .saved-row .card { background: var(--bg-alt); border-color: var(--line); }
.dark .saved-row .card:hover { box-shadow: var(--shadow-lg); border-color: rgba(var(--white-rgb),.1); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .saved-row .card:hover { transform: none; }
  .saved-row .card:active { transform: none; }
  .js-item:hover { transform: none; }
  .js-item:active { transform: none; }
  .saved-cta .btn:active { transform: none; }
  .block-cta .btn:active { transform: none; }
  .catalog-hero .stat-item:hover { transform: none; }
  .day-arc-track { animation: none; transform: none; }
  .pace-chip:hover { transform: none; }
  .pace-chip:active { transform: none; }
}

@media (max-width: 640px) {
  .day-arc-label { display: none; }
  .day-arc { height: 40px; }
}
</style>
