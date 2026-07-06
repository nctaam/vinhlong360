<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lưu trú' }]" :json-ld="true" />

    <!-- Hero — "wake-up" thesis: sell the morning, not the mattress -->
    <section class="wake-hero cat-accommodation">
      <span class="wake-hero-sweep" aria-hidden="true"></span>
      <span class="wake-hero-grain" aria-hidden="true"></span>
      <div class="wake-hero-inner">
        <p class="wake-hero-eyebrow">ĐỒNG BẰNG SÔNG CỬU LONG · VĨNH LONG — BẾN TRE — TRÀ VINH</p>
        <h1 class="wake-hero-title">{{ pc('hero_title', 'Thức dậy giữa vườn, nghe chim trước khi nghe chuông báo thức.') }}</h1>
        <p class="wake-hero-sub">{{ pc('hero_subtitle', 'Homestay nhà vườn, resort ven sông, khách sạn phố — chọn nơi bạn muốn mở mắt vào buổi sáng ở miền Tây.') }}</p>
      </div>
      <div v-if="allEntities.length" class="wake-hero-stats">
        <div class="stat-item">
          <CountUp :value="allEntities.length" class="stat-num" />
          <span class="stat-label">nơi lưu trú</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
      <ul v-if="typeCounts.length" class="catalog-type-breakdown" aria-label="Phân loại nơi lưu trú">
        <li v-for="t in typeCounts" :key="t.label" class="type-pill">
          <span class="type-count">{{ t.count }}</span>
          <span class="type-name">{{ t.label }}</span>
        </li>
      </ul>
    </section>

    <!-- Spotlight nổi bật -->
    <CatalogSpotlight :items="allEntities" />

    <!-- Ba kiểu qua đêm — the decision tree made visible, replaces prose-only "loại hình lưu trú" -->
    <section class="block band reveal">
      <div class="sediment-head">
        <h2>Ba kiểu qua đêm</h2>
      </div>
      <p class="section-desc">Mỗi kiểu ở là một nhịp sống khác nhau — chọn theo cách bạn muốn mở mắt buổi sáng, không phải theo hạng sao.</p>
      <div class="stay-triad">
        <article v-for="s in stayTypes" :key="s.key" class="stay-tile" :class="`stay-${s.key}`">
          <span class="stay-tile-motif" aria-hidden="true" v-html="s.motif"></span>
          <p class="stay-tile-kicker">{{ s.kicker }}</p>
          <h3 class="stay-tile-title">{{ s.title }}</h3>
          <p class="stay-tile-body">{{ s.body }}</p>
          <p class="stay-tile-persona">Phù hợp nếu bạn muốn {{ s.persona }}</p>
          <p class="stay-tile-price">{{ s.price }}</p>
        </article>
      </div>
    </section>

    <!-- Region windows — geography + morning-experience quick nav (replaces plain quick-picks) -->
    <section class="block band reveal">
      <div class="sediment-head">
        <h2>Chọn thức dậy ở đâu</h2>
      </div>
      <div class="region-windows" role="group" aria-label="Chọn nhanh theo khu vực">
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['region-window', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="toggleAreaAndScroll(key as string)"
        >
          <span class="rw-motif" :class="`rw-${key}`" aria-hidden="true">{{ meta.emoji }}</span>
          <span class="rw-name">{{ meta.name }}</span>
          <span class="rw-count">{{ countByArea(key as string) }} chỗ ở</span>
          <span class="rw-blurb">{{ meta.blurb }}</span>
        </button>
      </div>
    </section>

    <!-- Featured -->
    <section v-if="featured.length" class="block band reveal">
      <div class="sediment-head">
        <h2>Nơi ở được yêu thích</h2>
      </div>
      <div class="scroll-row" role="region" tabindex="0" aria-label="Nơi ở được yêu thích">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      fact="Homestay nhà vườn miền Tây là trải nghiệm đặc trưng — ngủ giữa vườn trái cây, thức dậy với tiếng chim và hương bưởi."
      icon="🏡"
      :links="[{ to: '/lich-trinh', label: 'Ghép lịch trình' }, { to: '/du-lich', label: 'Điểm du lịch gần' }]"
    />

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <div class="sediment-head"><h2>Ở đâu khi đi miền Tây?</h2></div>
      <div class="editorial-body drop-cap">
        <p>Lưu trú ở Vĩnh Long, Bến Tre và Trà Vinh mang đến những trải nghiệm rất khác so với khách sạn thành phố. Đây là vùng đất của homestay nhà vườn — nơi bạn ngủ trong căn nhà gỗ giữa vườn trái cây, thức dậy với tiếng chim hót và hương hoa bưởi. Nhiều chỗ ở nằm trên cù lao, phải đi đò hoặc xuồng mới tới — chính sự cách biệt ấy tạo nên sự yên tĩnh đặc trưng.</p>
      </div>

      <aside class="booking-note">
        <p class="booking-note-kicker">Sổ tay đặt phòng</p>
        <p>Tết Nguyên đán, lễ 30/4–1/5 và hè (tháng 6–8) là mùa cao điểm — đặt trước 1–2 tuần. Ngày thường hầu như luôn còn phòng. Liên hệ trực tiếp qua điện thoại hoặc Zalo của chủ nhà thường được giá tốt hơn qua trung gian. Đi nhóm đông, nhiều homestay có giá ưu đãi hoặc bao trọn gói ăn ở + tour vườn.</p>
      </aside>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block reveal">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm nơi lưu trú…" aria-label="Tìm nơi lưu trú" />
        </div>
        <p class="control-label">Khu vực</p>
        <FilterChips
          :filters="areaFilterOptions"
          :model-value="[areaFilter]"
          single-select
          aria-label="Lọc theo khu vực"
          @update:model-value="v => areaFilter = v[0] || 'all'"
        />
      </div>

      <p class="result-meta" aria-live="polite">{{ filtered.length }} nơi lưu trú</p>
      <EmptyState v-if="fetchError" tone="error" icon="🌊" title="Rất tiếc, chưa tải được" message="Kết nối mạng đang chập chờn. Bạn thử tải lại một lần nữa nhé." hint="Nếu vẫn chưa được, thử lại sau ít phút giúp mình.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-accommodation')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
      </div>
      <EmptyState v-else icon="🏡" title="Chưa thấy nơi ở phù hợp" message="Thử đổi khu vực hoặc từ khóa khác xem sao nhé." hint="Bạn có thể khám phá thêm các nơi ở ở Vĩnh Long, Bến Tre và Trà Vinh.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="areaFilter = 'all'; q = ''; scrollToGrid()">Xóa bộ lọc</button>
          <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block band reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🗓️</span>
          <div><strong>Lịch trình</strong><p>Ghép lưu trú vào kế hoạch đi</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm bản địa</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🍊</span>
          <div><strong>Đặc sản</strong><p>Mua quà miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'
import { generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

useReveal()
const { f: pc } = usePageContent('luu_tru')

const q = ref('')
const areaFilter = ref('all')
const gridSection = ref<HTMLElement | null>(null)
useFilterUrl({ vung: areaFilter }, { vung: 'all' })

function toggleAreaAndScroll(key: string) {
  areaFilter.value = areaFilter.value === key ? 'all' : key
  scrollToGrid()
}

// "Ba kiểu qua đêm" — the decision tree visitors actually carry in their head,
// made visible as story tiles instead of buried in prose (concept §3/§11).
// Copy extracted from the page's own existing editorial paragraphs — no new
// research, just re-formatted from paragraph to card, per concept feasibility note.
const nhaMotif = generateCategoryIcon('accommodation')
const natureMotif = generateCategoryIcon('nature')
const attractionMotif = generateCategoryIcon('attraction')
const stayTypes = [
  {
    key: 'homestay',
    kicker: 'HOMESTAY NHÀ VƯỜN',
    title: 'Ngủ giữa cây trái',
    body: 'Chủ nhà là nông dân, đưa bạn đi thăm vườn, chèo xuồng, nấu ăn cùng. Nhiều nơi phải đi thêm một đoạn đò hoặc xuồng mới tới.',
    persona: 'ngủ giữa vườn, ăn cơm chủ nhà nấu, không phiền đường xa',
    price: 'Thường 200.000–500.000đ/đêm, có bữa sáng',
    motif: nhaMotif,
  },
  {
    key: 'resort',
    kicker: 'RESORT SINH THÁI',
    title: 'Sông nước, đủ tiện nghi',
    body: 'Hồ bơi, spa, nhà hàng — nhưng vẫn giữ bungalow trên cầu gỗ, mái lá, nhìn ra kênh rạch.',
    persona: 'nghỉ dưỡng thong thả mà vẫn thấy sông',
    price: 'Thường 800.000–2.000.000đ/đêm',
    motif: natureMotif,
  },
  {
    key: 'hotel',
    kicker: 'KHÁCH SẠN PHỐ',
    title: 'Tiện di chuyển',
    body: 'Tập trung ở trung tâm thành phố Vĩnh Long, Bến Tre, Trà Vinh — gần chợ, gần bến xe, ít trải nghiệm bản địa hơn.',
    persona: 'đi công việc hoặc chỉ ghé qua một đêm',
    price: 'Thường 150.000–600.000đ/đêm',
    motif: attractionMotif,
  },
]

const { data, error: fetchError } = await useAsyncData('catalog-accommodation', () =>
  apiFetch<{ entities: Entity[] }>('/api/entities?type=accommodation&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const areaCountMap = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) {
    const area = getEntityArea(e)
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return counts
})

const areaCounts = computed(() =>
  Object.entries(AREA_META)
    .filter(([key]) => areaCountMap.value[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: areaCountMap.value[key] || 0 }))
)

function countByArea(key: string) {
  return areaCountMap.value[key] || 0
}

// FilterChips options for the grid's area filter (single-select, mirrors du-lich.vue's typeFilterOptions pattern)
const areaFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Object.entries(AREA_META).map(([key, meta]) => ({ key, label: `${meta.emoji} ${meta.name}` })),
])

// Data-driven accommodation type breakdown for hero confidence (no fabricated values):
// prefer the accommodation_type attribute, fall back to inferring from the name.
const TYPE_LABELS: Record<string, string> = {
  'khách sạn': 'Khách sạn',
  homestay: 'Homestay',
  'nhà vườn': 'Nhà vườn',
  resort: 'Resort',
  'nhà nghỉ': 'Nhà nghỉ',
}
function entityTypeKey(e: Entity): string {
  const raw = (e.attributes?.accommodation_type as string | undefined)?.toString().toLowerCase().trim()
  if (raw && TYPE_LABELS[raw]) return raw
  const n = (e.name || '').toLowerCase()
  if (n.includes('homestay')) return 'homestay'
  if (n.includes('khách sạn') || n.includes('hotel')) return 'khách sạn'
  if (n.includes('nhà vườn')) return 'nhà vườn'
  if (n.includes('resort')) return 'resort'
  if (n.includes('nhà nghỉ')) return 'nhà nghỉ'
  return ''
}
const typeCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) {
    const key = entityTypeKey(e)
    if (key) counts[key] = (counts[key] || 0) + 1
  }
  return Object.entries(counts)
    .map(([key, count]) => ({ label: TYPE_LABELS[key] || key, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

const featured = computed(() => {
  return allEntities.value
    .filter((e: Entity) => e.images?.length)
    .slice(0, 6)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const filtered = computed(() => {
  let list = allEntities.value

  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getEntityArea(e) === areaFilter.value)
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query) ||
      (e.place_name || '').toLowerCase().includes(query)
    )
  }

  return list
})

useSeoMeta({
  ogType: 'website',
  title: () => pc('seo_title') || 'Lưu trú Vĩnh Long, Bến Tre, Trà Vinh — vinhlong360',
  description: () => pc('seo_description') || 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở miền Tây.',
  ogTitle: () => pc('og_title') || 'Lưu trú — vinhlong360',
  ogDescription: () => pc('og_description') || 'Tìm chỗ ở phù hợp cho chuyến đi miền Tây.',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/luu-tru') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd(itemListJsonLd(
      'Lưu trú Vĩnh Long, Bến Tre, Trà Vinh',
      'Homestay, nhà vườn, khách sạn và nơi nghỉ ở miền Tây.',
      '/luu-tru',
      allEntities.value,
    )),
  }],
}))
</script>

<style scoped>
/* Hero accommodation type breakdown — supply-by-category trust cue.
   Data-driven from typeCounts; only renders when data is present. */
.catalog-type-breakdown {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}
.type-pill {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: rgba(var(--river-rgb, var(--primary-rgb)), .1);
  border: .5px solid rgba(var(--river-rgb, var(--primary-rgb)), .2);
  font-size: var(--text-xs);
  transition: background .3s var(--ease-out), transform .3s var(--ease-spring-gentle);
}
.type-pill:hover { transform: translateY(-1px); background: rgba(var(--river-rgb, var(--primary-rgb)), .16); }
.type-count { font-weight: var(--weight-bold); color: var(--tertiary, var(--primary-fg)); }
.type-name { color: var(--muted); font-weight: var(--weight-medium); }
/* dark overrides for .type-pill in dark-overrides.css */

@media (prefers-reduced-motion: reduce) {
  .type-pill { transition: none; }
  .type-pill:hover { transform: none; }
}

/* ══════════════════════════════════════════════════════════════════════
   WAKE-UP HERO — the flagship moment. Cool dawn-blue register (accommodation
   = rest/calm), single moving element: a horizon sweep that shifts the scrim
   from night-blue to dawn-amber to day-sand once on load, then settles.
   ══════════════════════════════════════════════════════════════════════ */
.wake-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  border-radius: var(--radius-xl);
  padding: clamp(var(--space-8), 4vw + var(--space-6), 4.5rem) var(--space-6) var(--space-6);
  margin-bottom: var(--space-6);
  border: .5px solid var(--line);
  /* dawn-blue register — deliberately cooler than the site's clay/amber warmth
     (lodging = rest/calm, per concept §2); no matching token exists yet, so
     expressed as neutral rgb() rather than a hardcoded brand hex substitute. */
  background: linear-gradient(160deg, rgb(28 42 61) 0%, rgb(42 63 86) 55%, rgb(217 199 163) 130%);
}
.dark .wake-hero { background: linear-gradient(160deg, rgb(13 20 32) 0%, rgb(22 34 47) 55%, rgb(46 40 24) 130%); border-color: var(--line); }

/* Grain overlay — antidote to the flat gradient (anti-slop §7) */
.wake-hero-grain {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 140px 140px; opacity: .05;
  mix-blend-mode: overlay;
}
.dark .wake-hero-grain { opacity: .08; }

/* Signature moment: the sunrise sweep — a hairline horizon band shifting
   night-blue → dawn-amber → day-sand once, then settling on day-state.
   Pure CSS, respects reduced-motion (freezes on the day-state immediately). */
.wake-hero-sweep {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background: linear-gradient(180deg,
    rgba(28, 42, 61, .6) 0%,
    rgba(51, 100, 110, .42) 38%,
    rgba(232, 163, 61, .34) 66%,
    rgba(217, 199, 163, .26) 100%);
  animation: wake-sunrise 18s var(--ease-cinematic) 1 both;
}
/* Night-blue → dawn-amber → day-sand: the band's own colour temperature shifts
   via a filter hue/brightness ramp (cheap, no layout, single moving element). */
@keyframes wake-sunrise {
  0%   { opacity: .35; filter: brightness(.7) saturate(.7); }
  50%  { opacity: .85; filter: brightness(1) saturate(1.15); }
  100% { opacity: .6;  filter: brightness(.92) saturate(1); }
}
.dark .wake-hero-sweep {
  background: linear-gradient(180deg,
    rgba(8, 12, 20, .65) 0%,
    rgba(51, 100, 110, .36) 38%,
    rgba(200, 140, 50, .26) 66%,
    rgba(160, 140, 100, .18) 100%);
}
@media (prefers-reduced-motion: reduce) {
  .wake-hero-sweep { animation: none; opacity: .6; filter: none; }
}

.wake-hero-inner { position: relative; z-index: 1; max-width: 62ch; }
.wake-hero-eyebrow {
  margin: 0 0 var(--space-4);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: rgba(255,255,255,.8);
}
.wake-hero-title {
  margin: 0 0 var(--space-4);
  font-family: var(--font-editorial); font-weight: 600;
  font-size: clamp(1.9rem, 1.5rem + 2.4vw, var(--text-4xl));
  line-height: 1.2; letter-spacing: var(--tracking-tight);
  color: var(--text-on-dark, #fff); text-wrap: balance;
  text-shadow: 0 2px 20px rgba(0,0,0,.3);
}
.wake-hero-sub {
  margin: 0; color: rgba(255,255,255,.86);
  font-size: var(--text-base); line-height: var(--leading-relaxed);
  max-width: 56ch;
}
.wake-hero-stats {
  position: relative; z-index: 1;
  display: flex; gap: var(--space-6); margin-top: var(--space-6); padding-top: var(--space-4);
  border-top: .5px solid rgba(255,255,255,.22); flex-wrap: wrap;
}
.wake-hero-stats .stat-item { padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); }
.wake-hero-stats .stat-item:hover { background: rgba(255,255,255,.08); }
.wake-hero-stats .stat-num { color: var(--text-on-dark, #fff); }
.wake-hero-stats .stat-label { color: rgba(255,255,255,.72); }
.wake-hero .catalog-type-breakdown { position: relative; z-index: 1; }
.wake-hero .type-pill {
  background: rgba(255,255,255,.1); border-color: rgba(255,255,255,.2);
}
.wake-hero .type-pill:hover { background: rgba(255,255,255,.16); }
.wake-hero .type-count { color: var(--text-on-dark, #fff); }
.wake-hero .type-name { color: rgba(255,255,255,.72); }

@media (max-width: 640px) {
  .wake-hero { padding: var(--space-6) var(--space-4); }
  .wake-hero-title { font-size: var(--text-xl); }
}

/* ══════════════════════════════════════════════════════════════════════
   BA KIỂU QUA ĐÊM — editorial triad (decision tree made visible)
   ══════════════════════════════════════════════════════════════════════ */
.stay-triad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-5);
}
.stay-tile {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  padding: var(--space-6) var(--space-5) var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--card);
  border: .5px solid var(--line);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out-expo), border-color .2s var(--ease-out);
}
.stay-tile:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: var(--border); }
.stay-tile-motif {
  position: absolute; right: -10%; bottom: -12%; z-index: 0;
  width: 96px; height: 96px; opacity: .1; color: var(--primary);
  pointer-events: none;
}
.stay-tile.stay-resort .stay-tile-motif { color: var(--secondary); }
.stay-tile.stay-hotel .stay-tile-motif { color: var(--tertiary); }
.stay-tile-motif :deep(svg) { width: 100%; height: 100%; display: block; }
.stay-tile-kicker {
  position: relative; z-index: 1; margin: 0 0 var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
.stay-tile-title {
  position: relative; z-index: 1; margin: 0 0 var(--space-3);
  font-family: var(--font-editorial); font-weight: 600;
  font-size: var(--text-xl); line-height: var(--leading-tight);
  color: var(--ink);
}
.stay-tile-body {
  position: relative; z-index: 1; margin: 0 0 var(--space-3);
  color: var(--ink); font-size: var(--text-sm); line-height: var(--leading-relaxed);
}
.stay-tile-persona {
  position: relative; z-index: 1; margin: 0 0 var(--space-3);
  padding-top: var(--space-3); border-top: .5px solid var(--line);
  color: var(--muted); font-size: var(--text-sm); font-style: italic;
}
.stay-tile-price {
  position: relative; z-index: 1; margin: 0;
  color: var(--muted); font-size: var(--text-xs); font-variant-numeric: tabular-nums;
}
.dark .stay-tile { background: var(--card); border-color: var(--line); }
.dark .stay-tile:hover { border-color: rgba(255,255,255,.1); }

@media (max-width: 900px) and (min-width: 601px) {
  .stay-triad { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .stay-triad { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .stay-tile:hover { transform: none; }
}

/* ══════════════════════════════════════════════════════════════════════
   REGION WINDOWS — geography + morning-experience micro-nav
   (upgrades the plain quick-pick button row into typographic tiles:
   kicker + serif name + blurb, reads as magazine not app-chips)
   ══════════════════════════════════════════════════════════════════════ */
.region-windows {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}
.region-window {
  position: relative;
  display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-1);
  text-align: left;
  padding: var(--space-5); border-radius: var(--radius-lg);
  background: var(--card); border: .5px solid var(--line);
  cursor: pointer; min-height: 44px;
  transition: transform .3s var(--ease-spring-gentle), box-shadow .3s var(--ease-out-expo), border-color .2s var(--ease-out);
}
.region-window:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: rgba(var(--river-rgb, var(--primary-rgb)), .4); }
.region-window:active { transform: scale(.98); transition-duration: .08s; }
.region-window:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
/* Active state = tri-province gradient underline (river→amber→clay), matching
   FilterChips.vue's ::after treatment, instead of a flat single-tone border. */
.region-window.active { border-color: transparent; background: rgba(var(--river-rgb, var(--primary-rgb)), .06); }
.region-window.active::after {
  content: "";
  position: absolute; left: var(--space-5); right: var(--space-5); bottom: 0;
  height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .region-window.active::after {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
.rw-motif { font-size: 1.6rem; transition: transform .35s var(--ease-spring-gentle); }
.region-window:hover .rw-motif { transform: scale(1.12); }
.rw-name {
  font-family: var(--font-editorial); font-weight: 600;
  font-size: var(--text-lg); color: var(--ink);
}
.rw-count {
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  color: var(--tertiary, var(--primary-fg));
  font-variant-numeric: tabular-nums;
}
.rw-blurb {
  margin-top: var(--space-2);
  font-size: var(--text-xs); color: var(--muted); line-height: var(--leading-relaxed);
}
.dark .region-window { background: var(--card); border-color: var(--line); }
.dark .region-window.active { background: rgba(var(--river-rgb, var(--primary-rgb)), .12); }
@media (prefers-reduced-motion: reduce) {
  .region-window:hover,
  .region-window:active { transform: none; }
  .region-window:hover .rw-motif { transform: none; }
}

/* ══════════════════════════════════════════════════════════════════════
   BOOKING NOTE — "sổ tay đặt phòng" callout: reference content gets
   reference-styling (bordered card), not H2 prose, to keep the page's
   editorial rhythm from getting bogged down in logistics.
   ══════════════════════════════════════════════════════════════════════ */
.booking-note {
  margin-top: var(--space-6);
  padding: var(--space-5);
  border: .5px solid var(--line);
  border-left: 3px solid var(--tertiary, var(--primary));
  border-radius: var(--radius-md);
  background: var(--bg-alt);
}
.booking-note-kicker {
  margin: 0 0 var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--tertiary, var(--primary-fg));
}
.booking-note p:last-child {
  margin: 0; color: var(--muted); font-size: var(--text-sm); line-height: var(--leading-relaxed);
}
.dark .booking-note { background: var(--bg-alt); border-color: var(--line); }
</style>
