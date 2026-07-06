<template>
  <section class="page dd-page">
    <span class="almanac-progress" aria-hidden="true"><span class="almanac-progress-fill" :style="{ transform: `scaleY(${scrollProgress})` }"></span></span>
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Địa điểm' }]" />

    <!-- Almanac hero — bến đò signboard: horizon wash + hand-drawn route line -->
    <section class="catalog-hero cat-directory almanac-hero" aria-label="Danh bạ địa điểm">
      <span class="almanac-route" aria-hidden="true"></span>
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon almanac-compass" aria-hidden="true" v-html="COMPASS_SVG"></span>
        <div>
          <h1>Danh bạ địa điểm</h1>
          <p>1.532 điểm đến đã xác minh, từ cù lao giữa sông đến quầy hàng trong hẻm nhỏ — Vĩnh Long, Bến Tre, Trà Vinh, không sót nơi nào.</p>
        </div>
      </div>
      <div v-if="total" class="catalog-stats almanac-stats">
        <div class="stat-item almanac-stat" tabindex="0">
          <CountUp :value="total" class="stat-num" />
          <span class="stat-label">địa điểm</span>
          <span class="almanac-gloss" aria-hidden="true">từ chợ nổi đến chùa cổ</span>
        </div>
        <div class="stat-item almanac-stat" tabindex="0">
          <CountUp :value="CARD_TYPES.length" class="stat-num" />
          <span class="stat-label">loại hình</span>
          <span class="almanac-gloss" aria-hidden="true">đủ mọi cách sống ở đây</span>
        </div>
        <div class="stat-item almanac-stat" tabindex="0">
          <CountUp :value="Object.keys(AREA_META).length" class="stat-num" />
          <span class="stat-label">khu vực</span>
          <span class="almanac-gloss" aria-hidden="true">một dải sông chung dòng</span>
        </div>
      </div>
    </section>

    <!-- Spotlight -->
    <CatalogSpotlight :items="firstPage" />

    <!-- Region discovery — SIGNATURE MOMENT: province stamps -->
    <section class="block band reveal">
      <div class="sediment-head section-head">
        <h2>Khám phá theo khu vực</h2>
      </div>
      <div class="province-stamps">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['province-stamp', { active: areaFilter === key }]"
          :style="{ '--stamp-rgb': STAMP_RGB[key as string] || 'var(--primary-rgb)' }"
          :aria-pressed="areaFilter === key"
          @click="pickArea(key as string)"
        >
          <span class="stamp-mark" aria-hidden="true">{{ meta.emoji }}</span>
          <span class="stamp-name">{{ meta.name }}</span>
          <span class="stamp-caption">{{ meta.blurb }}</span>
        </button>
      </div>
    </section>

    <!-- Type discovery -->
    <section class="block reveal">
      <div class="sediment-head section-head">
        <h2>Duyệt theo loại hình</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Loại hình" tabindex="0">
        <button type="button"
          v-for="t in typeChips" :key="t.value"
          :class="['dd-type-card', { active: typeFilter === t.value }]"
          :aria-pressed="typeFilter === t.value"
          @click="pickType(t.value)"
        >
          <span class="dd-type-icon">{{ t.emoji }}</span>
          <span class="dd-type-label">{{ t.label }}</span>
        </button>
      </div>
    </section>

    <!-- Interstitial -->
    <!-- Editorial (declutter-2 A2: interstitial inline vào mạch bài) -->
    <section v-once class="page-article reveal">
      <div class="sediment-head"><h2>Khám phá toàn bộ điểm đến Vĩnh Long</h2></div>
      <div class="editorial-body drop-cap">
        <p>Danh bạ địa điểm tổng hợp mọi điểm đến, trải nghiệm, sản phẩm, lưu trú và di tích trên toàn vùng Vĩnh Long, Bến Tre và Trà Vinh. Mỗi mục đều có thông tin thực tế: địa chỉ, số điện thoại, giờ mở cửa, giá tham khảo và mùa vụ phù hợp.</p>
      </div>

      <CatalogInterstitial
        fact="Vĩnh Long, Bến Tre và Trà Vinh có hơn 1.500 điểm đến, đặc sản và dịch vụ — từ cù lao xanh mát đến làng nghề trăm năm, tất cả được xác minh và cập nhật liên tục."
        icon="📊"
        variant="warm"
        :links="[{ to: '/ban-do', label: 'Xem bản đồ' }, { to: '/du-lich', label: 'Du lịch sinh thái' }]"
      />
    </section>

    <!-- Refine bar — search only. Area/type are already fully controllable via
         the province-stamps + type-scroll-row above (signature pickers); this
         bar no longer duplicates them with a second FilterChips pair. -->
    <div ref="gridAnchor" class="dd-refine">
      <div class="dd-search">
        <svg class="dd-search-ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input v-model="qInput" type="search" enterkeyhint="search" class="dd-search-input" placeholder="Tìm địa điểm, đặc sản, làng nghề…" aria-label="Tìm địa điểm" @keyup.enter="applyQuery" />
        <button v-if="qApplied" type="button" class="dd-search-clear" aria-label="Xoá tìm" @click="clearQuery">&times;</button>
        <button type="button" class="btn btn-primary btn-sm" @click="applyQuery">Tìm</button>
      </div>
    </div>

    <p v-if="!pending && qApplied" class="dd-count" aria-live="polite">
      <strong>{{ total }}</strong> địa điểm cho “{{ qApplied }}”
    </p>

    <SkeletonGrid v-if="pending && !items.length" :count="9" />

    <EmptyState
      v-else-if="listError && !items.length"
      icon="⚠️" title="Không thể tải danh sách"
      message="Đã có lỗi khi tải dữ liệu. Vui lòng thử lại."
      tone="error"
    >
      <template #actions>
        <button type="button" class="btn btn-primary btn-sm" @click="refresh()">Thử lại</button>
      </template>
    </EmptyState>

    <EmptyState
      v-else-if="!items.length"
      icon="🔍" :title="emptyTitle"
      :message="emptyMessage"
    >
      <template #actions>
        <div v-if="emptyRecovery.length" class="dd-empty-recovery">
          <button v-for="r in emptyRecovery" :key="r.label" type="button" class="chip" @click="r.apply">{{ r.label }}</button>
        </div>
        <button type="button" class="btn btn-outline btn-sm" @click="resetAll">Xoá bộ lọc</button>
      </template>
    </EmptyState>

    <template v-else>
      <div class="grid dd-grid" role="list" aria-label="Danh sách địa điểm">
        <template v-for="(e, i) in items" :key="e.id">
          <div v-if="i > 0 && i % 9 === 0" class="grid-divider reveal" role="presentation" aria-hidden="true">
            <span class="grid-divider-label">{{ dividerFact(i) }}</span>
          </div>
          <EntityCard :entity="e" />
        </template>
      </div>
      <p v-if="loadMoreError" class="dd-load-error" role="alert">Không tải thêm được. <button type="button" class="btn-text" @click="loadMore">Thử lại</button></p>
      <button v-if="hasMore" type="button" class="btn btn-ghost dd-more" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? 'Đang tải…' : loadMoreLabel }}
      </button>
    </template>
  </section>
</template>

<script setup lang="ts">
import { TYPE_META, CARD_TYPES, AREA_META } from '~/composables/useConstants'
useReveal()

// Almanac hero glyph — a compass rose (editorial, single-colour) replacing the
// bare 📍 emoji app-icon. Static markup only, no data dependency.
const COMPASS_SVG = `<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="24" cy="24" r="19"/><circle cx="24" cy="24" r="1.6" fill="currentColor" stroke="none"/><path d="M24 8 L28 22 L24 26 L20 22Z" fill="currentColor" stroke="none"/><path d="M24 40 L20 26 L24 22 L28 26Z" fill="none"/><path d="M24 6 L24 11" stroke-linecap="round"/><path d="M24 37 L24 42" stroke-linecap="round"/><path d="M6 24 L11 24" stroke-linecap="round"/><path d="M37 24 L42 24" stroke-linecap="round"/></svg>`

// Province-stamp tint per area — reuses existing brand RGB tokens (no new colours).
const STAMP_RGB: Record<string, string> = {
  'vinh-long': 'var(--primary-rgb)',
  'ben-tre': 'var(--secondary-rgb)',
  'tra-vinh': 'var(--river-rgb)',
  'lien-vung': 'var(--accent-rgb)',
}

const route = useRoute()
const router = useRouter()
const PAGE = 24
const gridAnchor = ref<HTMLElement | null>(null)

function scrollToGrid() {
  gridAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// Scroll-linked river-tick — desktop-only wayfinding cue in the page gutter,
// reuses the shared useScrollProgress() engine (already powers SedimentThread
// elsewhere); no new scroll-listener logic invented here.
const { progress: scrollProgress } = useScrollProgress()

const typeFilter = ref<string>(typeof route.query.type === 'string' ? route.query.type : 'all')
const areaFilter = ref<string>(typeof route.query.area === 'string' ? route.query.area : 'all')
const qApplied = ref<string>(typeof route.query.q === 'string' ? route.query.q : '')
const qInput = ref<string>(qApplied.value)

const typeChips = CARD_TYPES.map(t => ({ value: t, emoji: TYPE_META[t]?.emoji || '📍', label: TYPE_META[t]?.label || t }))

function buildUrl(offset: number) {
  const p = new URLSearchParams({ limit: String(PAGE), offset: String(offset) })
  if (typeFilter.value !== 'all') p.set('type', typeFilter.value)
  if (areaFilter.value !== 'all') p.set('area', areaFilter.value)
  if (qApplied.value) p.set('q', qApplied.value)
  return `/api/entities?${p}`
}

// Trang đầu (SSR-friendly cho SEO); load-more nối client-side.
const { data, pending, refresh, error: listError } = await useAsyncData(
  'dia-diem-list',
  () => apiFetch<{ total: number; entities: any[] }>(buildUrl(0)),
  { watch: [] },
)
const firstPage = computed(() => data.value?.entities || [])
const total = computed(() => data.value?.total || 0)

const extra = ref<any[]>([])
const items = computed(() => [...firstPage.value, ...extra.value])
const hasMore = computed(() => items.value.length < total.value)
const loadingMore = ref(false)
const loadMoreError = ref(false)

async function loadMore() {
  if (loadingMore.value) return
  loadingMore.value = true
  loadMoreError.value = false
  try {
    const res = await $fetch<{ entities: any[] }>(buildUrl(items.value.length))
    extra.value.push(...(res.entities || []))
  } catch {
    loadMoreError.value = true
  }
  loadingMore.value = false
}

// Đổi bộ lọc → reset trang nối + đồng bộ URL + refetch trang đầu
function syncUrlAndRefresh() {
  extra.value = []
  const query: Record<string, string> = {}
  if (typeFilter.value !== 'all') query.type = typeFilter.value
  if (areaFilter.value !== 'all') query.area = areaFilter.value
  if (qApplied.value) query.q = qApplied.value
  router.replace({ query })
  refresh()
}
function pickArea(key: string) { areaFilter.value = areaFilter.value === key ? 'all' : key; syncUrlAndRefresh(); scrollToGrid() }
function pickType(value: string) { typeFilter.value = typeFilter.value === value ? 'all' : value; syncUrlAndRefresh(); scrollToGrid() }
let _qTimer: ReturnType<typeof setTimeout> | undefined
function cancelQDebounce() { clearTimeout(_qTimer) }
function applyQuery() { cancelQDebounce(); qApplied.value = qInput.value.trim(); syncUrlAndRefresh() }
function clearQuery() { cancelQDebounce(); qInput.value = ''; qApplied.value = ''; syncUrlAndRefresh() }
function resetAll() { cancelQDebounce(); typeFilter.value = 'all'; areaFilter.value = 'all'; qInput.value = ''; qApplied.value = ''; syncUrlAndRefresh() }
watch(qInput, (val) => {
  cancelQDebounce()
  const trimmed = val.trim()
  if (trimmed === qApplied.value) return
  _qTimer = setTimeout(() => { qApplied.value = trimmed; syncUrlAndRefresh() }, 350)
})

// Curiosity copy — warm empty state instead of a bare "not found." Presents the
// active filter combo in words + 1-2 real recovery chips (only what the current
// data proves exists: other areas when a type+area combo is empty).
const activeTypeLabel = computed(() => typeFilter.value === 'all' ? '' : (TYPE_META[typeFilter.value]?.label || ''))
const activeAreaName = computed(() => areaFilter.value === 'all' ? '' : (AREA_META[areaFilter.value]?.name || ''))
const emptyTitle = 'Chưa có trong danh bạ'
const emptyMessage = computed(() => {
  if (activeTypeLabel.value && activeAreaName.value) {
    return `Chưa có “${activeTypeLabel.value.toLowerCase()}” ở ${activeAreaName.value} trong danh bạ.`
  }
  if (qApplied.value) return `Không tìm thấy kết quả cho “${qApplied.value}”.`
  return 'Thử bỏ bớt bộ lọc hoặc đổi từ khoá tìm kiếm.'
})
const emptyRecovery = computed(() => {
  if (!activeTypeLabel.value || !activeAreaName.value) return []
  const otherAreas = Object.entries(AREA_META).filter(([k]) => k !== areaFilter.value).slice(0, 2)
  return otherAreas.map(([key, meta]) => ({
    label: `Thử ${meta.name}?`,
    apply: () => { areaFilter.value = key; syncUrlAndRefresh() },
  }))
})

// Grid divider — every 9 cards, a typographic interruption (real place-name,
// no invented facts) so a long grid reads as an almanac, not an infinite dump.
function dividerFact(index: number): string {
  const seen = items.value.slice(0, index)
  const areasSeen = new Set(seen.map(e => e.placeName || e.place_name).filter(Boolean))
  const nth = Math.floor(index / 9)
  const pool = Array.from(areasSeen)
  if (pool.length) return pool[nth % pool.length] as string
  return `${index} nơi đã lật qua`
}

// Load-more teaser — a real name instead of a bare count. We don't have the
// true next-hidden item client-side without prefetching page N+1 (out of scope:
// would touch pagination logic), so the honest MVP teases with the last-loaded
// card's own place — still a real, non-fabricated name (concept doc §6 MVP).
const loadMoreLabel = computed(() => {
  const remaining = total.value - items.value.length
  if (remaining <= 0) return ''
  const last = items.value[items.value.length - 1]
  const teaseName = last?.placeName || last?.place_name || last?.name
  if (teaseName) return `Xem thêm — còn ${remaining} nơi nữa, kể cả gần ${teaseName} →`
  return `Xem thêm (còn ${remaining})`
})

useSeoMeta({
  title: () => activeTypeLabel.value
    ? `${activeTypeLabel.value} — Danh bạ địa điểm — vinhlong360`
    : 'Danh bạ địa điểm — Vĩnh Long, Bến Tre, Trà Vinh — vinhlong360',
  description: () => 'Khám phá toàn bộ điểm đến, đặc sản OCOP, làng nghề, lưu trú và di tích của Vĩnh Long, Bến Tre, Trà Vinh. Lọc theo loại hình và khu vực.',
  ogTitle: 'Danh bạ địa điểm — vinhlong360',
  ogDescription: 'Điểm đến, đặc sản, làng nghề, lưu trú và di tích miền Tây — tìm theo loại và khu vực.',
})

// JSON-LD: ItemList structured data for search engines
const listJsonLd = computed(() => {
  return itemListJsonLd(
    'Danh bạ địa điểm — vinhlong360',
    'Tất cả điểm đến, đặc sản, làng nghề, lưu trú và di tích của Vĩnh Long, Bến Tre, Trà Vinh.',
    '/dia-diem',
    firstPage.value,
  )
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/dia-diem') }],
  script: [{ type: 'application/ld+json', innerHTML: () => JSON.stringify(listJsonLd.value) }],
})
</script>

<style scoped>
.dd-page { max-width: 1100px; margin: 0 auto; }

.dd-type-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-lg);
  cursor: pointer; transition: border-color .2s, box-shadow .2s;
  min-width: 100px; flex-shrink: 0;
}
.dd-type-card:hover { border-color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.dd-type-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dd-type-card.active { border-color: var(--primary); background: rgba(var(--primary-rgb), .06); }
.dd-type-icon { font-size: 1.6rem; }
.dd-type-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); white-space: nowrap; }

.dd-search { display: flex; align-items: center; gap: var(--space-2); padding: .35rem .5rem .35rem .75rem; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-full); margin-bottom: var(--space-3); }
.dd-search:focus-within { border-color: var(--primary); }
.dd-search-ic { color: var(--muted); flex-shrink: 0; }
.dd-search-input { flex: 1; min-width: 0; border: none; background: none; outline: none; color: var(--ink); font-size: var(--text-sm); padding: .4rem 0; }
.dd-search-input:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dd-search-input::placeholder { color: var(--muted); }
.dd-search-clear { border: none; background: none; color: var(--muted); font-size: 1.3rem; line-height: 1; cursor: pointer; padding: 0 .25rem; }
.dd-search-clear:hover { color: var(--ink); }

.dd-count { font-size: var(--text-sm); color: var(--muted); margin: 0 0 var(--space-4); }
.dd-count strong { color: var(--ink); }

.dd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-4); }
.dd-more { display: block; margin: var(--space-5) auto 0; }
.dd-load-error { text-align: center; color: var(--danger, #dc2626); font-size: var(--text-sm); margin: var(--space-3) 0; }
.dd-load-error .btn-text { color: var(--primary-fg); font-weight: var(--weight-semibold); background: none; border: none; cursor: pointer; text-decoration: underline; }

/* ============================================================
   ALMANAC HERO — bến đò signboard: horizon wash + hand-drawn
   route line + compass glyph + stat hover-gloss.
   ============================================================ */
.almanac-hero { isolation: isolate; }
/* hand-drawn dashed route meandering behind the headline — decorative, static */
.almanac-route {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-repeat: no-repeat; background-position: center; background-size: 100% 100%;
  opacity: .16;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='900'%20height='220'%20viewBox='0%200%20900%20220'%20fill='none'%3E%3Cpath%20d='M-20%20150%20Q120%2060%20260%20120%20T520%2090%20T780%20140%20T1000%2080'%20stroke='%239C3D22'%20stroke-width='2'%20stroke-dasharray='2%2010'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
.dark .almanac-route {
  opacity: .14;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='900'%20height='220'%20viewBox='0%200%20900%20220'%20fill='none'%3E%3Cpath%20d='M-20%20150%20Q120%2060%20260%20120%20T520%2090%20T780%20140%20T1000%2080'%20stroke='%23D98A6F'%20stroke-width='2'%20stroke-dasharray='2%2010'%20stroke-linecap='round'/%3E%3C/svg%3E");
}
.almanac-compass { color: var(--clay-600); display: inline-flex; }
.almanac-compass :deep(svg) { width: 2.2rem; height: 2.2rem; }
.dark .almanac-compass { color: var(--primary-fg); }
@media (max-width: 640px) { .almanac-compass :deep(svg) { width: 1.7rem; height: 1.7rem; } }

/* Stat hover-gloss — a second poetic line reveals under the count on hover/focus,
   absolute-positioned so it never shifts layout. */
.almanac-stat { position: relative; }
.almanac-gloss {
  position: absolute; left: var(--space-3); top: 100%; margin-top: 2px;
  font-family: var(--font-editorial); font-style: italic; font-size: var(--text-xs);
  color: var(--primary-fg); white-space: nowrap;
  opacity: 0; transform: translateY(-2px);
  transition: opacity .3s var(--ease-out), transform .3s var(--ease-out);
  pointer-events: none;
}
.almanac-stat:hover .almanac-gloss,
.almanac-stat:focus-visible .almanac-gloss { opacity: 1; transform: translateY(0); }
.dark .almanac-gloss { color: var(--primary-fg-strong); }
@media (prefers-reduced-motion: reduce) {
  .almanac-gloss { transition: opacity .01s linear; transform: none; }
}
@media (max-width: 640px) {
  /* no hover on touch — keep the gloss statically visible, small, understated */
  .almanac-gloss { position: static; display: block; opacity: 1; transform: none; margin-top: 1px; }
}

/* ============================================================
   PROVINCE STAMPS — signature moment. Postage-stamp shaped cards
   (serrated top edge via clip-path), serif name, corner emoji mark,
   AREA_META blurb as caption. Replaces plain quick-pick buttons.
   ============================================================ */
.province-stamps {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4); margin-bottom: var(--space-2);
}
.province-stamp {
  --stamp-rgb: var(--primary-rgb);
  position: relative; text-align: left; cursor: pointer;
  display: flex; flex-direction: column; gap: var(--space-2);
  padding: var(--space-5) var(--space-4) var(--space-4);
  background: linear-gradient(160deg, rgba(var(--stamp-rgb), .08) 0%, var(--card) 55%);
  border: .5px solid var(--line);
  /* serrated/torn top edge — decorative zigzag, CSS-only */
  clip-path: polygon(
    0% 6px, 3% 0%, 6% 6px, 9% 0%, 12% 6px, 15% 0%, 18% 6px, 21% 0%, 24% 6px, 27% 0%,
    30% 6px, 33% 0%, 36% 6px, 39% 0%, 42% 6px, 45% 0%, 48% 6px, 51% 0%, 54% 6px, 57% 0%,
    60% 6px, 63% 0%, 66% 6px, 69% 0%, 72% 6px, 75% 0%, 78% 6px, 81% 0%, 84% 6px, 87% 0%,
    90% 6px, 93% 0%, 96% 6px, 99% 0%, 100% 6px,
    100% 100%, 0% 100%
  );
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out-expo), border-color .2s var(--ease-out);
  transform: rotate(-1deg);
}
.province-stamp:nth-child(2n) { transform: rotate(.6deg); }
.province-stamp:nth-child(3n) { transform: rotate(-.4deg); }
.province-stamp:hover, .province-stamp:focus-visible {
  transform: rotate(0deg) translateY(-3px);
  box-shadow: var(--shadow-md), 0 0 0 1px rgba(var(--stamp-rgb), .3);
  border-color: rgba(var(--stamp-rgb), .4);
}
.province-stamp:active { transform: rotate(0deg) scale(.98); transition-duration: .08s; }
.province-stamp:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.province-stamp.active {
  border-color: rgba(var(--stamp-rgb), .5);
  background: linear-gradient(160deg, rgba(var(--stamp-rgb), .14) 0%, var(--card) 55%);
  box-shadow: 0 0 0 1px rgba(var(--stamp-rgb), .35);
}
.stamp-mark {
  position: absolute; top: var(--space-3); right: var(--space-3);
  font-size: 1.4rem; opacity: .9;
}
.stamp-name {
  font-family: var(--font-editorial); font-weight: 600; font-size: var(--text-lg);
  color: var(--ink); letter-spacing: var(--tracking-tight); padding-right: 2rem;
}
.stamp-caption {
  font-size: var(--text-xs); color: var(--muted); line-height: var(--leading-relaxed);
  font-style: italic;
}
@media (prefers-reduced-motion: reduce) {
  .province-stamp, .province-stamp:nth-child(2n), .province-stamp:nth-child(3n) { transform: none; }
  .province-stamp:hover, .province-stamp:focus-visible { transform: none; }
  .province-stamp:active { transform: none; }
}
@media (max-width: 640px) {
  .province-stamps { grid-template-columns: repeat(2, 1fr); }
}

/* ============================================================
   TYPE FILMSTRIP — thin category-color underline draws in on
   hover/focus, evoking flipping through indexed photo negatives.
   ============================================================ */
.dd-type-card { position: relative; overflow: hidden; }
.dd-type-card::after {
  content: ""; position: absolute; left: var(--space-4); right: var(--space-4); bottom: 6px;
  height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, var(--river-600), var(--amber-600), var(--clay-600));
  transform: scaleX(0); transform-origin: left; transition: transform .3s var(--ease-out-expo);
}
.dd-type-card:hover::after, .dd-type-card:focus-visible::after, .dd-type-card.active::after { transform: scaleX(1); }
.dark .dd-type-card::after { background: linear-gradient(90deg, #74ABB5, var(--amber-500), var(--clay-400)); }
@media (prefers-reduced-motion: reduce) {
  .dd-type-card::after { transition: none; }
}

/* ============================================================
   REFINE BAR — sticky search-only control surface. Area/type filtering
   lives solely in the province-stamps + type-scroll-row above (the
   signature pickers); this bar no longer duplicates them with a second
   FilterChips pair, so it holds just the search field.
   ============================================================ */
.dd-refine {
  position: sticky; top: 78px; z-index: var(--z-sticky, 100);
  background: var(--surface-translucent); backdrop-filter: var(--glass);
  -webkit-backdrop-filter: var(--glass);
  border: .5px solid var(--line); border-top: 1px solid var(--line);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--space-3); margin-bottom: var(--space-4);
}
.dd-refine .dd-search { margin-bottom: 0; }
.dark .dd-refine { background: var(--surface-translucent); border-color: var(--line); }

/* ============================================================
   EMPTY-STATE RECOVERY — near-match chips before the generic reset.
   ============================================================ */
.dd-empty-recovery { display: flex; gap: var(--space-2); flex-wrap: wrap; justify-content: center; margin-bottom: var(--space-3); }

/* ============================================================
   GRID DIVIDER — typographic interruption every 9 cards. Full-bleed,
   not another card/CTA — just a quiet place-name break.
   ============================================================ */
.grid-divider {
  grid-column: 1 / -1;
  display: flex; align-items: center; gap: var(--space-4);
  margin: var(--space-2) 0; padding: var(--space-2) 0;
}
.grid-divider::before, .grid-divider::after { content: ''; flex: 1; height: .5px; background: var(--line); }
.grid-divider-label {
  font-family: var(--font-editorial); font-style: italic; font-size: var(--text-sm);
  color: var(--muted); white-space: nowrap; padding: 0 var(--space-2);
}

/* ============================================================
   SCROLL-TICK — desktop-only wayfinding cue in the page gutter,
   fills river→amber→clay as the visitor scrolls the almanac.
   ============================================================ */
.almanac-progress {
  position: fixed; left: var(--space-2); top: 15vh; bottom: 15vh; width: 3px;
  border-radius: var(--radius-full); background: var(--line);
  z-index: var(--z-floating, 75); overflow: hidden; display: none;
}
.almanac-progress-fill {
  position: absolute; inset: 0; transform-origin: top; transform: scaleY(0);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
  transition: transform .1s linear;
}
.dark .almanac-progress-fill { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
@media (min-width: 1200px) { .almanac-progress { display: block; } }
@media (prefers-reduced-motion: reduce) {
  .almanac-progress { display: none; }
}

/* ============================================================
   DARK MODE (batch) — additional pairs not already covered inline above.
   ============================================================ */
.dark .province-stamp { background: linear-gradient(160deg, rgba(var(--stamp-rgb), .12) 0%, var(--card) 55%); }
.dark .province-stamp.active { background: linear-gradient(160deg, rgba(var(--stamp-rgb), .2) 0%, var(--card) 55%); }
</style>
