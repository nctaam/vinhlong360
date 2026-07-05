<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tuyến đường gợi ý' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-route">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🛤️</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="ROUTES.length" class="stat-num" />
          <span class="stat-label">tuyến đường</span>
        </div>
        <div class="stat-item">
          <CountUp :value="3" class="stat-num" />
          <span class="stat-label">khu vực</span>
        </div>
      </div>

      <!-- Signature: map-vignette strip — spatial orientation before the list.
           Tri-province silhouette line-art with a pin per route, positioned by
           its area (x-band) so "these routes spread across 3 areas" reads at
           a glance before any card text. -->
      <div class="route-vignette" role="img" aria-label="Vị trí các tuyến đường trên 3 khu vực Vĩnh Long, Bến Tre, Trà Vinh">
        <svg viewBox="0 0 640 90" preserveAspectRatio="none" aria-hidden="true" class="route-vignette-svg">
          <path d="M0 46 Q 90 20 180 46 T 360 46 T 540 46 T 640 40" class="rv-river" />
          <path d="M0 64 Q 100 78 220 60 T 440 66 T 640 58" class="rv-road" />
        </svg>
        <span v-for="r in ROUTES" :key="'pin-' + r.id" class="rv-pin" :class="`area-${r.area}`" :style="pinStyle(r)" :title="r.name">
          <span class="rv-pin-dot" aria-hidden="true" />
        </span>
        <div class="rv-labels" aria-hidden="true">
          <span>Vĩnh Long</span><span>Bến Tre</span><span>Trà Vinh</span>
        </div>
      </div>
    </section>

    <div class="block">
    <div class="controls">
      <p class="control-label">Khu vực</p>
      <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
        <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', 'chip-area', `area-${key}`, { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = key as string"
        >{{ meta.emoji }} {{ meta.name }}</button>
      </div>
    </div>
    </div>

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <div class="sediment-head route-article-head"><h2>Tự khám phá miền Tây bằng xe máy hoặc ô tô</h2></div>
      <p>Các tuyến đường dưới đây được thiết kế cho người muốn <strong>tự đi</strong> — không cần tour, không cần hướng dẫn viên. Mỗi tuyến ghi rõ khoảng cách, thời gian di chuyển và các điểm dừng theo thứ tự hợp lý. Đường liên tỉnh giữa Vĩnh Long, Bến Tre và Trà Vinh phần lớn là đường nhựa tốt, phù hợp cả xe máy lẫn ô tô 4-7 chỗ.</p>
      <p>Nếu đi xe máy, ưu tiên khởi hành sáng sớm (trước 7h) để tránh nắng và tận dụng ánh sáng đẹp. Mang theo áo mưa — miền Tây hay có mưa rào chiều, đặc biệt từ tháng 6 đến tháng 11. Đường vào các làng nghề đôi khi hẹp và dốc cầu, chạy chậm khi qua khu dân cư.</p>
    </section>

    <CatalogInterstitial
      fact="Mỗi tuyến ghi rõ khoảng cách, thời gian và điểm dừng — tải về hoặc lưu vào tài khoản để xem offline khi đi."
      icon="🛤️"
      :links="[
        { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
        { to: '/ban-do', label: 'Xem bản đồ' },
      ]"
    />

    <p class="result-meta" aria-live="polite">{{ filtered.length }} tuyến đường</p>

    <div v-if="filtered.length" class="route-grid">
      <article v-for="r in filtered" :key="r.id" class="route-card" :class="`area-${r.area}`" :aria-label="r.name + ' — ' + r.duration">
        <div :class="['route-header', `area-${r.area}`]">
          <span class="route-emoji">{{ r.emoji }}</span>
          <div>
            <h3 class="route-name">{{ r.name }}</h3>
            <span class="route-meta">{{ r.duration }} · {{ r.distance }}</span>
          </div>
        </div>
        <div class="route-body">
          <p>{{ r.description }}</p>

          <!-- Stat trio, styled like the hero's CountUp stats — visual rhyme
               between hero and card (premium cue §2.7). -->
          <div class="route-stat-trio">
            <div class="rstat"><span class="rstat-num">{{ r.stops.length }}</span><span class="rstat-label">điểm dừng</span></div>
            <div class="rstat"><span class="rstat-num">{{ r.duration }}</span><span class="rstat-label">thời gian</span></div>
            <div class="rstat"><span class="rstat-num">{{ r.distance }}</span><span class="rstat-label">quãng đường</span></div>
          </div>

          <!-- "Tuyến này hợp mùa nào?" — cross-link tying the road to the almanac. -->
          <NuxtLink v-if="routeSeasonTag(r)" :to="`/theo-mua?mua=${routeSeasonTag(r)!.month}`" class="route-season-tag">
            <span aria-hidden="true">📅</span> Hợp mùa: {{ routeSeasonTag(r)!.label }}
          </NuxtLink>

          <h3 class="route-stops-head">Điểm dừng chân</h3>
          <!-- Signature: day-strip rail — a route stops being a bulleted <ol>
               and becomes a small drawn path, dot by dot, in the route's own
               color (clay/leaf/river via area-*). -->
          <ol class="route-rail">
            <li v-for="(stop, i) in r.stops" :key="i" class="rail-stop">
              <span class="rail-dot" aria-hidden="true">{{ i + 1 }}</span>
              <span class="rail-text">
                <strong>{{ stop.name }}</strong>
                <span v-if="stop.note"> — {{ stop.note }}</span>
              </span>
            </li>
          </ol>

          <div class="route-tips" v-if="r.tips">
            <span class="route-tips-eyebrow">Mẹo đi đường</span>
            {{ r.tips }}
          </div>
          <div class="route-links">
            <NuxtLink :to="`/khu-vuc/${r.area}`" class="btn btn-outline btn-sm">📍 {{ AREA_META[r.area]?.name }}</NuxtLink>
            <NuxtLink to="/ban-do" no-prefetch class="btn btn-ghost btn-sm">🗺️ Xem bản đồ</NuxtLink>
            <NuxtLink to="/lien-he" class="btn btn-ghost btn-sm route-contact-cta">📞 Hỏi HTX/homestay dọc tuyến</NuxtLink>
          </div>
        </div>
      </article>
    </div>

    <!-- Designed empty state (e.g. filter to an area with 0 routes) -->
    <div v-else class="block">
      <EmptyState
        icon="🛤️"
        title="Không tìm thấy tuyến"
        message="Chưa có tuyến đường gợi ý cho khu vực này. Thử chọn khu vực khác nhé."
      >
        <template #actions>
          <button type="button" class="btn btn-outline" @click="areaFilter = 'all'">Xem tất cả khu vực</button>
        </template>
      </EmptyState>
    </div>

    <!-- Cross-links -->
    <section class="block band catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <p class="cross-sub">Tiếp tục hành trình miền Tây của bạn</p>
      <div class="cross-links">
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { DEFAULT_ROUTES, type RouteDef } from '~/utils/routesContent'

useReveal()
const { f: pc } = usePageContent('tuyen_duong')
const { get: ss } = useSiteSettings()

const areaFilter = ref('all')

// Admin-editable via `tuyen_duong.routes` (JSON); falls back to DEFAULT_ROUTES.
const ROUTES = computed(() => {
  const r = ss('tuyen_duong.routes', DEFAULT_ROUTES)
  return Array.isArray(r) && r.length ? r : DEFAULT_ROUTES
})

const filtered = computed(() => {
  if (areaFilter.value === 'all') return ROUTES.value
  return ROUTES.value.filter(r => r.area === areaFilter.value)
})

useFilterUrl({ vung: areaFilter }, { vung: 'all' })

// ── Map-vignette pin placement (§2.2) ──────────────────────────────────────
// Positions each route pin along the tri-province strip by area band, so the
// spatial spread reads before any card text. Pure presentation — no new data.
const AREA_X_BAND: Record<string, [number, number]> = {
  'vinh-long': [8, 34],
  'ben-tre': [38, 64],
  'tra-vinh': [68, 94],
  'lien-vung': [20, 80],
}
function pinStyle(r: RouteDef) {
  const [lo, hi] = AREA_X_BAND[r.area] || [20, 80]
  // Deterministic spread within the band from the route id (stable across renders).
  let h = 0
  for (let i = 0; i < r.id.length; i++) h = (h * 31 + r.id.charCodeAt(i)) >>> 0
  const pct = lo + (h % 1000) / 1000 * (hi - lo)
  return { left: `${pct}%` }
}

// ── "Tuyến này hợp mùa nào?" (§2.5) ─────────────────────────────────────────
// Cross-references a route's OWN copy (id / tips) against explicit month
// ranges already stated in its `tips` field in routesContent.ts — we only tag
// routes that already carry an honest, explicit seasonal claim in their own
// text (no invented seasonality). Links to the shared /theo-mua almanac,
// reusing its existing `?mua=` query contract — no schema change.
const ROUTE_SEASON: Record<string, { month: number; label: string }> = {
  'vong-trai-cay-vinh-long': { month: 6, label: 'mùa chôm chôm, T5–T7' },
  'vong-mua-nuoc-noi': { month: 9, label: 'mùa nước nổi, T8–T11' },
}
function routeSeasonTag(r: RouteDef) {
  return ROUTE_SEASON[r.id] || null
}

useSeoMeta({
  ogType: 'website',
  title: () => pc('seo_title') || 'Tuyến đường gợi ý miền Tây — vinhlong360',
  description: () => pc('seo_description') || 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: () => pc('og_title') || 'Tuyến đường gợi ý — vinhlong360',
  ogDescription: () => pc('og_description') || 'Tự khám phá miền Tây bằng xe máy hoặc ô tô.',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/tuyen-duong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Tuyến đường gợi ý miền Tây',
      description: 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/tuyen-duong',
      mainEntity: {
        '@type': 'ItemList',
        numberOfItems: ROUTES.value.length,
        itemListElement: ROUTES.value.map((r: any, i: number) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: r.name,
          description: `${r.duration} · ${r.distance}`,
        })),
      },
    }),
  }],
}))
</script>

<style scoped>
.route-grid { display: flex; flex-direction: column; gap: var(--space-6); }
.route-card { position: relative; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
/* glassy top-sheen, revealed on hover for an Apple-style finish */
.route-card::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 40%; pointer-events: none; opacity: 0; background: linear-gradient(180deg, rgba(255,255,255,.18), transparent); transition: opacity .35s var(--ease-out); z-index: 2; }
.route-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--primary-rgb), .14), 0 18px 40px -18px rgba(var(--primary-rgb), .35); border-color: var(--border); }
.route-card:hover::before { opacity: .9; }
.route-card:active { transform: translateY(0) scale(.99); transition-duration: .08s; }
.route-header { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-5) var(--space-6); color: var(--text-on-dark, #fff); box-shadow: inset 0 1px 0 rgba(255,255,255,.15), 0 1px 2px rgba(0,0,0,.1); transition: background .3s var(--ease-out); }
.route-header h3 { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); text-shadow: var(--shadow-text); overflow-wrap: break-word; word-break: break-word; }
.route-meta { font-size: var(--text-sm); opacity: .9; }
.route-emoji { font-size: var(--text-3xl); text-shadow: var(--shadow-text); }
.route-header.area-vinh-long { background: var(--cat-experience); }
.route-header.area-ben-tre { background: var(--cat-product); }
.route-header.area-tra-vinh { background: var(--cat-attraction); }
.route-header.area-lien-vung { background: linear-gradient(135deg, var(--river-600), var(--amber-600) 55%, var(--clay-600)); }
/* Route name — editorial italic for the poetic ones, small but distinctive
   (matches CE mastheads elsewhere on site). Wayfinding stop-names stay sans. */
.route-name { font-family: var(--font-editorial); font-style: italic; }
.route-body { padding: var(--space-5) var(--space-6); }
.route-body p { margin: 0 0 var(--space-3); line-height: var(--leading-relaxed); color: var(--ink); }
.route-stops-head { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: var(--space-4) 0 var(--space-3); }

/* ── Stat trio — rhymes with the hero's CountUp stats (premium cue §2.7) ── */
.route-stat-trio {
  display: flex; gap: var(--space-4); margin: 0 0 var(--space-4);
  padding: var(--space-3) 0; border-top: .5px solid var(--line); border-bottom: .5px solid var(--line);
}
.rstat { display: flex; flex-direction: column; gap: 1px; flex: 1 1 0; min-width: 0; }
.rstat-num { font-size: var(--text-lg); font-weight: var(--weight-extrabold); color: var(--primary-fg); letter-spacing: var(--tracking-tight); font-variant-numeric: tabular-nums; line-height: 1.2; overflow-wrap: break-word; }
.rstat-label { font-size: var(--text-2xs); color: var(--muted); text-transform: uppercase; letter-spacing: var(--tracking-caps); font-weight: var(--weight-semibold); }

/* ── Season cross-tag → /theo-mua (§2.5 highest-leverage cross-link) ── */
.route-season-tag {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--secondary-fg);
  background: rgba(var(--secondary-rgb), .1); border: .5px solid rgba(var(--secondary-rgb), .22);
  padding: var(--space-1) var(--space-3); border-radius: var(--radius-full);
  margin-bottom: var(--space-4); min-height: 30px;
  transition: background .25s var(--ease-out), border-color .25s var(--ease-out);
}
.route-season-tag:hover { background: rgba(var(--secondary-rgb), .18); border-color: rgba(var(--secondary-rgb), .35); }
.route-season-tag:focus-visible { outline: 2px solid var(--secondary); outline-offset: 2px; }

/* ── Signature: day-strip rail — the path drawing itself, dot by dot ──
   Replaces the plain <ol> bullet list. Vertical hairline + numbered dots,
   tinted per area (echoes the tri-province sediment gradient when a route
   crosses all 3 — see .area-lien-vung below). */
.route-rail { position: relative; list-style: none; margin: 0 0 var(--space-4); padding: 0 0 0 32px; }
.route-rail::before {
  content: ""; position: absolute; left: 11px; top: 6px; bottom: 6px; width: 2px;
  background: linear-gradient(180deg, var(--rail-tone, var(--primary)) 0%, color-mix(in srgb, var(--rail-tone, var(--primary)) 35%, transparent) 100%);
  border-radius: var(--radius-full);
}
.route-card.area-vinh-long .route-rail { --rail-tone: var(--secondary); }
.route-card.area-ben-tre .route-rail { --rail-tone: var(--accent); }
.route-card.area-tra-vinh .route-rail { --rail-tone: var(--tertiary); }
/* Cross-province tour: rail literally uses the sediment river→amber→clay
   gradient — visually saying "this crosses all 3 areas" with no legend. */
.route-card.area-lien-vung .route-rail::before {
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 50%, var(--clay-600) 100%);
}
.rail-stop {
  position: relative; display: flex; align-items: baseline; gap: var(--space-3);
  padding: 2px var(--space-2) 2px 0; margin-bottom: var(--space-3); margin-left: calc(var(--space-2) * -1);
  border-radius: var(--radius-sm); line-height: var(--leading-normal);
  transition: transform .3s var(--ease-out), background .25s var(--ease-out);
  animation: railStopIn .4s var(--ease-out) both;
}
.rail-stop:last-child { margin-bottom: 0; }
.rail-stop:nth-child(1) { animation-delay: 40ms; }
.rail-stop:nth-child(2) { animation-delay: 80ms; }
.rail-stop:nth-child(3) { animation-delay: 120ms; }
.rail-stop:nth-child(4) { animation-delay: 160ms; }
.rail-stop:nth-child(5) { animation-delay: 200ms; }
.rail-stop:nth-child(n+6) { animation-delay: 240ms; }
@keyframes railStopIn { from { opacity: 0; transform: translateY(4px); } }
.rail-dot {
  position: absolute; left: 2px; top: 1px;
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-2xs); font-weight: var(--weight-bold); font-variant-numeric: tabular-nums;
  background: var(--card); color: var(--rail-tone, var(--primary));
  box-shadow: 0 0 0 2px var(--rail-tone, var(--primary)) inset, var(--shadow-xs);
  transition: transform .3s var(--ease-spring-gentle), background .25s var(--ease-out), color .25s var(--ease-out);
}
.rail-text strong { color: var(--ink); transition: color .25s var(--ease-out); }
.rail-text span { color: var(--muted); font-size: var(--text-sm); }
.rail-stop:hover { transform: translateX(2px); background: var(--overlay-subtle); }
.rail-stop:hover .rail-dot { transform: scale(1.1); background: var(--rail-tone, var(--primary)); color: var(--text-on-dark, #fff); }
.rail-stop:hover .rail-text strong { color: var(--primary-fg); }
/* hovering a dot nudges the connecting line's tone brighter — "this is a path" */
.route-rail:has(.rail-stop:hover)::before { filter: saturate(1.3) brightness(1.08); }

.route-tips {
  background: var(--badge-season-bg); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm);
  font-size: var(--text-sm); margin-bottom: var(--space-3); line-height: var(--leading-normal);
  border: .5px solid rgba(var(--primary-rgb), .15); box-shadow: 0 1px 2px rgba(var(--primary-rgb), .2);
  transition: box-shadow .3s var(--ease-out);
}
.route-tips-eyebrow {
  display: block; font-size: var(--text-2xs); font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--primary-fg);
  margin-bottom: 2px;
}
/* subtle breathing pulse when the card is hovered, to draw the eye to the tip */
.route-card:hover .route-tips { animation: tips-pulse 2.4s var(--ease-out) infinite; }
@keyframes tips-pulse {
  0%, 100% { box-shadow: 0 1px 2px rgba(var(--primary-rgb), .2); }
  50%      { box-shadow: 0 1px 8px rgba(var(--primary-rgb), .32); }
}
/* staggered entrance for route cards, tying into the batch signature rhythm */
.route-grid > .route-card { animation: card-rise .55s var(--ease-out-expo) both; }
.route-grid > .route-card:nth-child(1) { animation-delay: .02s; }
.route-grid > .route-card:nth-child(2) { animation-delay: .06s; }
.route-grid > .route-card:nth-child(3) { animation-delay: .10s; }
.route-grid > .route-card:nth-child(4) { animation-delay: .14s; }
.route-grid > .route-card:nth-child(5) { animation-delay: .18s; }
.route-grid > .route-card:nth-child(n+6) { animation-delay: .22s; }
.cross-sub { margin: calc(var(--space-3) * -1) 0 var(--space-4); color: var(--muted); font-size: var(--text-sm); }
.route-links { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.route-links .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.route-links .btn:active { transform: scale(.95); transition-duration: .08s; }
.dark .route-card { background: var(--card); border-color: var(--line); }
.dark .route-card::before { background: linear-gradient(180deg, rgba(255,255,255,.07), transparent); }
.dark .route-card:hover { box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--primary-rgb), .22), 0 18px 44px -18px rgba(0,0,0,.6); border-color: var(--border); }
.dark .route-tips { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.1); }
.dark .route-body p { color: rgba(255,255,255,.85); }
.dark .rail-stop:hover .rail-text strong { color: var(--primary); }
.dark .rail-text span { color: rgba(255,255,255,.55); }
.dark .rail-dot { background: var(--card); box-shadow: 0 0 0 2px var(--rail-tone, var(--primary)) inset, 0 1px 3px rgba(0,0,0,.4); }
.dark .route-stat-trio { border-color: var(--line); }
.dark .rstat-num { color: var(--primary); }
.dark .route-season-tag { background: rgba(var(--secondary-rgb), .16); border-color: rgba(var(--secondary-rgb), .3); }
.dark .route-season-tag:hover { background: rgba(var(--secondary-rgb), .24); }
.dark .route-header.area-lien-vung { background: linear-gradient(135deg, #74ABB5, var(--amber-500) 55%, var(--clay-400)); }
.dark .route-card.area-lien-vung .route-rail::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 50%, var(--clay-400) 100%); }

/* Mobile: tighten card padding so emoji + name don't crowd narrow screens */
@media (max-width: 640px) {
  .route-header { padding: var(--space-4) var(--space-5); }
  .route-body { padding: var(--space-4) var(--space-5); }
  .rail-stop { line-height: var(--leading-relaxed); }
  .route-stat-trio { gap: var(--space-3); }
  .rstat-num { font-size: var(--text-base); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .route-card:hover { transform: none; }
  .route-card:active { transform: none; }
  .route-card:hover::before { opacity: 0; }
  .rail-stop:hover { transform: none; }
  .rail-stop:hover .rail-dot { transform: none; }
  .route-rail:has(.rail-stop:hover)::before { filter: none; }
  .route-links .btn:active { transform: none; }
  .route-grid > .route-card { animation: none; }
  .rail-stop { animation: none; }
  .route-card:hover .route-tips { animation: none; box-shadow: 0 1px 8px rgba(var(--primary-rgb), .28); }
}

/* ── Editorial essay heading — sediment-head sits inside .page-article, so
   restore the zero-top-margin the article's own `h2:first-child` rule
   expected before the wrapper div was introduced. ── */
.route-article-head h2 { margin-top: 0; }

/* ── Area-tinted filter chips — chips preview the route palette they filter,
   so filter and content read as one system before you even click (§2.3). ── */
.chip-area.area-vinh-long { border-left: 2px solid color-mix(in srgb, var(--secondary) 55%, transparent); }
.chip-area.area-ben-tre { border-left: 2px solid color-mix(in srgb, var(--accent) 55%, transparent); }
.chip-area.area-tra-vinh { border-left: 2px solid color-mix(in srgb, var(--tertiary) 55%, transparent); }
.chip-area.area-lien-vung { border-left: 2px solid color-mix(in srgb, var(--clay-600) 55%, transparent); }
.chip-area.active.area-vinh-long { background: var(--secondary); border-color: var(--secondary); }
.chip-area.active.area-ben-tre { background: var(--accent); border-color: var(--accent); color: var(--ink); }
.chip-area.active.area-tra-vinh { background: var(--tertiary); border-color: var(--tertiary); }

/* ── Contact CTA — visually distinct from the neutral map/area exits, since
   it's the page's one path from "read about a trip" to "ask a real person"
   (§2.6). Reuses the existing .btn.btn-ghost system, just a warmer tint. ── */
.route-contact-cta { color: var(--secondary-fg); }
.route-contact-cta:hover { background: rgba(var(--secondary-rgb), .1); }

/* ── Signature: map-vignette strip (§2.2) — spatial orientation before the
   list. Tri-province line-art with a pin per route positioned by area, so
   "these routes spread across 3 areas" reads before any card text. ── */
.route-vignette {
  position: relative; height: 64px; margin-top: var(--space-6);
  padding-top: var(--space-2);
}
.route-vignette-svg { position: absolute; inset: 0; width: 100%; height: 100%; opacity: .5; }
.rv-river { fill: none; stroke: var(--river-600); stroke-width: 2; stroke-linecap: round; }
.rv-road { fill: none; stroke: var(--clay-600); stroke-width: 1.5; stroke-dasharray: 1 6; stroke-linecap: round; opacity: .7; }
.rv-pin {
  position: absolute; top: 14px; width: 14px; height: 14px; transform: translateX(-50%);
  display: flex; align-items: center; justify-content: center; cursor: default;
}
.rv-pin-dot {
  width: 9px; height: 9px; border-radius: 50%; box-shadow: 0 0 0 2px var(--card), var(--shadow-xs);
  background: var(--secondary);
}
.rv-pin.area-vinh-long .rv-pin-dot { background: var(--secondary); }
.rv-pin.area-ben-tre .rv-pin-dot { background: var(--accent); }
.rv-pin.area-tra-vinh .rv-pin-dot { background: var(--tertiary); }
.rv-pin.area-lien-vung .rv-pin-dot { background: var(--clay-600); }
.rv-labels {
  position: absolute; inset: auto 0 0 0; display: flex; justify-content: space-between;
  font-size: var(--text-2xs); color: var(--muted); text-transform: uppercase; letter-spacing: var(--tracking-caps);
  font-weight: var(--weight-semibold); padding: 0 var(--space-1);
}
.dark .rv-river { stroke: #74ABB5; }
.dark .rv-road { stroke: var(--clay-400); }
.dark .rv-pin.area-tra-vinh .rv-pin-dot { background: #74ABB5; }
.dark .rv-pin.area-lien-vung .rv-pin-dot { background: var(--clay-400); }
.dark .rv-pin-dot { box-shadow: 0 0 0 2px var(--card), 0 1px 3px rgba(0,0,0,.4); }
@media (max-width: 640px) {
  .route-vignette { height: 52px; }
  .rv-labels { font-size: 9px; }
}
</style>
