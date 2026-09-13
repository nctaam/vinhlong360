<template>
  <section class="page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tuyến đường gợi ý' }]" :json-ld="true" />

    <!-- Hero -->
    <section class="catalog-hero cat-route">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true"><IconLine name="route" /></span>
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
      <div class="route-vignette" role="img" aria-label="Vị trí các tuyến đường trên 3 khu vực tỉnh Vĩnh Long hợp nhất (trước 7-2025)">
        <svg viewBox="0 0 640 90" preserveAspectRatio="none" aria-hidden="true" class="route-vignette-svg">
          <path d="M0 46 Q 90 20 180 46 T 360 46 T 540 46 T 640 40" class="rv-river" />
          <path d="M0 64 Q 100 78 220 60 T 440 66 T 640 58" class="rv-road" />
        </svg>
        <span v-for="r in ROUTES" :key="'pin-' + r.id" class="rv-pin" :class="`area-${r.area}`" :style="pinStyle(r)" :title="r.name">
          <span class="rv-pin-dot" aria-hidden="true" />
        </span>
        <div class="rv-labels" aria-hidden="true">
          <span>Vùng Vĩnh Long</span><span>Vùng Bến Tre (cũ)</span><span>Vùng Trà Vinh (cũ)</span>
        </div>
      </div>
    </section>

    <!-- AEO Plaque: River Ecology Routes & Land Road Adventures -->
    <CatalogAeoPlaque
      title="Cẩm Nang Tuyến Đường Khám Phá &amp; Hành Trình Sông Nước"
      kicker="Góc nhìn bản địa · Kết nối liên vùng &amp; Nhịp sống bến phà"
      accent="leaf"
      icon="route"
      :entries="[
        {
          heading: 'Cung đường Cù lao An Bình &amp; Đò ngang sông Cổ Chiên',
          text: 'Lộ trình len lỏi qua các liếp vườn cây trái trĩu cành, trải nghiệm qua phà An Bình ngắm toàn cảnh sông nước mênh mông.',
        },
        {
          heading: 'Cung đường Di sản Gốm đỏ Mang Thít (ĐT 902)',
          text: 'Chạy xe dọc kênh Thầy Cai chiêm ngưỡng hàng ngàn mái lò nung gạch đất nung rêu phong cổ kính độc bản phương Nam.',
        },
        {
          heading: 'Hành trình Liên Vùng Ba Con Sông (Tiền – Cổ Chiên – Hậu)',
          text: 'Kết nối các trục lộ huyết mạch QL53, QL57 qua Chợ Lách và Trà Vinh (địa hạt trước 7-2025), ngắm những rặng bần xanh ngắt và cồn bãi màu mỡ.',
        },
      ]"
      cta-to="/tao-lich-trinh"
      cta-label="Lập lịch trình thông minh theo tuyến"
    />

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
          ><IconLine :name="meta.icon || 'pin'" class="chip-area-icon" /> {{ meta.name }}</button>
        </div>
        <div v-if="areaFilter !== 'all'" class="active-filter-ledger" role="region" aria-label="Bộ lọc đang áp dụng">
          <span class="afl-heading">Đang lọc:</span>
          <div class="afl-chips">
            <span class="afl-chip">
              <span class="afl-text">{{ AREA_META[areaFilter]?.name || areaFilter }}</span>
              <button type="button" class="afl-remove" aria-label="Bỏ lọc khu vực" @click="areaFilter = 'all'"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <button type="button" class="afl-clear-all" @click="areaFilter = 'all'">Xóa tất cả</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <div class="sediment-head route-article-head"><h2>Tự khám phá Vĩnh Long bằng xe máy hoặc ô tô</h2></div>
      <p>Các tuyến đường dưới đây được thiết kế cho người muốn <strong>tự đi</strong> — không cần tour, không cần hướng dẫn viên. Mỗi tuyến ghi rõ khoảng cách, thời gian di chuyển và các điểm dừng theo thứ tự hợp lý. Đường liên vùng kết nối giữa các khu vực của tỉnh Vĩnh Long hợp nhất (gồm Bến Tre và Trà Vinh trước 7-2025) phần lớn là đường nhựa tốt, phù hợp cả xe máy lẫn ô tô 4-7 chỗ.</p>
      <p>Nếu đi xe máy, ưu tiên khởi hành sáng sớm (trước 7h) để tránh nắng và tận dụng ánh sáng đẹp. Mang theo áo mưa — vùng này hay có mưa rào chiều, đặc biệt từ tháng 6 đến tháng 11. Đường vào các làng nghề đôi khi hẹp và dốc cầu, chạy chậm khi qua khu dân cư.</p>

      <!-- declutter-2 A2: interstitial inline vào mạch bài -->
      <CatalogInterstitial
        fact="Mỗi tuyến ghi rõ khoảng cách, thời gian và điểm dừng — tải về hoặc lưu vào tài khoản để xem offline khi đi."
        icon-name="route"
        :links="[
          { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
          { to: '/ban-do', label: 'Xem bản đồ' },
        ]"
      />
    </section>

    <p class="result-meta" aria-live="polite">{{ filtered.length }} tuyến đường</p>

    <div v-if="filtered.length" class="route-grid">
      <article v-for="r in filtered" :key="r.id" class="route-card" :class="`area-${r.area}`" :aria-label="r.name + ' — ' + r.duration">
        <div :class="['route-header', `area-${r.area}`]">
          <span class="route-emoji" aria-hidden="true"><IconLine :name="routeIcon(r)" /></span>
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
            <span aria-hidden="true"><IconLine name="calendar" /></span> Hợp mùa: {{ routeSeasonTag(r)!.label }}
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
            <NuxtLink :to="`/khu-vuc/${r.area}`" class="btn btn-outline btn-sm"><IconLine name="pin" /> {{ AREA_META[r.area]?.name }}</NuxtLink>
            <NuxtLink :to="{ path: '/tao-lich-trinh', query: { title: r.name } }" class="btn btn-ghost btn-sm"><IconLine name="plus" /> Lập lịch trình</NuxtLink>
            <button type="button" class="btn btn-ghost btn-sm route-preview-btn" @click="openRoutePreview(r)">
              <IconLine name="map" /> Bản đồ lộ trình
            </button>
            <NuxtLink to="/ban-do" no-prefetch class="btn btn-ghost btn-sm"><IconLine name="compass" /> Xem bản đồ</NuxtLink>
            <NuxtLink to="/lien-he" class="btn btn-ghost btn-sm route-contact-cta"><IconLine name="phone" /> Hỏi HTX/homestay dọc tuyến</NuxtLink>
          </div>
        </div>
      </article>
    </div>

    <!-- Designed empty state (e.g. filter to an area with 0 routes) -->
    <div v-else class="block">
      <EmptyState
        icon-name="route"
        title="Không tìm thấy tuyến"
        message="Chưa có tuyến đường gợi ý cho khu vực này. Thử chọn khu vực khác nhé."
      >
        <template #actions>
          <button type="button" class="btn btn-outline" @click="areaFilter = 'all'">Xem tất cả khu vực</button>
        </template>
      </EmptyState>
    </div>

    <!-- Cross-links -->
    <CatalogCrossLinks subtitle="Tiếp tục hành trình Vĩnh Long của bạn" />

    <!-- Interactive Route Preview Modal -->
    <Teleport to="body">
      <div
        v-if="previewRoute"
        class="route-modal-backdrop"
        role="presentation"
        @click.self="closeRoutePreview"
      >
        <div
          class="route-preview-dialog"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="'route-preview-title-' + previewRoute.id"
        >
          <header class="route-preview-header" :class="`area-${previewRoute.area}`">
            <div class="route-preview-header-copy">
              <span class="route-preview-kicker">
                {{ AREA_META[previewRoute.area]?.name || 'Lộ trình khám phá' }} · {{ previewRoute.duration }} · {{ previewRoute.distance }}
              </span>
              <h2 :id="'route-preview-title-' + previewRoute.id" class="route-preview-title">
                {{ previewRoute.name }}
              </h2>
            </div>
            <button
              type="button"
              class="route-preview-close"
              aria-label="Đóng bản đồ lộ trình"
              @click="closeRoutePreview"
            >
              <IconLine name="x" aria-hidden="true" />
            </button>
          </header>

          <div class="route-preview-body">
            <!-- Map Waypoint Canvas -->
            <div class="route-preview-map-pane">
              <div class="route-preview-map-canvas" role="region" aria-label="Sơ đồ trạm dừng">
                <svg
                  viewBox="0 0 600 320"
                  class="route-map-svg"
                  preserveAspectRatio="xMidYMid meet"
                  role="img"
                  aria-label="Sơ đồ không gian các điểm dừng"
                >
                  <defs>
                    <linearGradient id="routeWaterGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="var(--river-600)" stop-opacity="0.1" />
                      <stop offset="100%" stop-color="var(--color-material-river, var(--color-action))" stop-opacity="0.22" />
                    </linearGradient>
                  </defs>
                  <rect width="100%" height="100%" fill="var(--bg-alt)" rx="12" />
                  <path
                    d="M 0 110 Q 150 70 300 130 T 600 120 L 600 200 Q 450 240 300 190 T 0 210 Z"
                    fill="url(#routeWaterGradient)"
                  />
                  <path
                    :d="routeSvgPath(previewRoute.stops)"
                    class="route-path-line"
                    fill="none"
                    stroke="var(--color-action)"
                    stroke-width="3"
                    stroke-dasharray="6 4"
                  />
                  <g
                    v-for="(stop, idx) in previewRoute.stops"
                    :key="idx"
                    class="route-waypoint-pin"
                    :class="{ 'is-active': selectedStopIndex === idx }"
                    tabindex="0"
                    role="button"
                    :aria-label="`Trạm ${idx + 1}: ${stop.name}`"
                    @click="selectedStopIndex = idx"
                    @keydown.enter="selectedStopIndex = idx"
                    @keydown.space.prevent="selectedStopIndex = idx"
                  >
                    <circle
                      :cx="stopCoords(idx, previewRoute.stops.length)[0]"
                      :cy="stopCoords(idx, previewRoute.stops.length)[1]"
                      r="16"
                      class="waypoint-circle"
                    />
                    <text
                      :x="stopCoords(idx, previewRoute.stops.length)[0]"
                      :y="stopCoords(idx, previewRoute.stops.length)[1] + 5"
                      text-anchor="middle"
                      class="waypoint-num"
                    >{{ idx + 1 }}</text>
                    <text
                      :x="stopCoords(idx, previewRoute.stops.length)[0]"
                      :y="stopCoords(idx, previewRoute.stops.length)[1] + (idx % 2 === 0 ? -22 : 28)"
                      text-anchor="middle"
                      class="waypoint-name-label"
                    >{{ stop.name }}</text>
                  </g>
                </svg>
              </div>

              <!-- Selected Waypoint Card -->
              <div v-if="currentPreviewStop" class="route-waypoint-info-card">
                <div class="waypoint-card-header">
                  <span class="waypoint-order-badge">Trạm dừng số {{ selectedStopIndex + 1 }} / {{ previewRoute.stops.length }}</span>
                  <div class="waypoint-card-nav">
                    <button
                      type="button"
                      class="btn btn-outline btn-sm"
                      :disabled="selectedStopIndex === 0"
                      aria-label="Xem trạm trước"
                      @click="selectedStopIndex = Math.max(0, selectedStopIndex - 1)"
                    >
                      <IconLine name="arrow-left" aria-hidden="true" /> Trước
                    </button>
                    <button
                      type="button"
                      class="btn btn-outline btn-sm"
                      :disabled="selectedStopIndex >= previewRoute.stops.length - 1"
                      aria-label="Xem trạm tiếp theo"
                      @click="selectedStopIndex = Math.min(previewRoute.stops.length - 1, selectedStopIndex + 1)"
                    >
                      Sau <IconLine name="arrow-right" aria-hidden="true" />
                    </button>
                  </div>
                </div>
                <h3 class="waypoint-card-title">{{ currentPreviewStop.name }}</h3>
                <p v-if="currentPreviewStop.note" class="waypoint-card-note">
                  {{ currentPreviewStop.note }}
                </p>
              </div>
            </div>

            <!-- Waypoint List Sidebar -->
            <div class="route-preview-sidebar">
              <h3 class="route-preview-sidebar-title">Lộ trình di chuyển</h3>
              <ol class="route-preview-stops-rail">
                <li
                  v-for="(stop, idx) in previewRoute.stops"
                  :key="idx"
                  class="preview-rail-item"
                  :class="{ 'is-selected': selectedStopIndex === idx }"
                  tabindex="0"
                  role="button"
                  @click="selectedStopIndex = idx"
                  @keydown.enter="selectedStopIndex = idx"
                  @keydown.space.prevent="selectedStopIndex = idx"
                >
                  <span class="preview-rail-badge">{{ idx + 1 }}</span>
                  <div class="preview-rail-meta">
                    <strong>{{ stop.name }}</strong>
                    <span v-if="stop.note">{{ stop.note }}</span>
                  </div>
                </li>
              </ol>
              <div class="route-preview-dialog-actions">
                <NuxtLink
                  :to="{ path: '/tao-lich-trinh', query: { title: previewRoute.name } }"
                  class="btn btn-primary btn-sm preview-action-btn"
                  @click="closeRoutePreview"
                >
                  <IconLine name="plus" /> Lập lịch trình tuyến này
                </NuxtLink>
                <NuxtLink
                  to="/ban-do"
                  class="btn btn-outline btn-sm preview-action-btn"
                  @click="closeRoutePreview"
                >
                  <IconLine name="compass" /> Mở bản đồ toàn cảnh
                </NuxtLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { DEFAULT_ROUTES, type RouteDef, type RouteStop } from '~/utils/routesContent'

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

function routeIcon(r: RouteDef): string {
  if (r.emoji === '🍊') return 'fruit'
  if (r.emoji === '🥥') return 'leaf'
  if (r.emoji === '🛕') return 'landmark'
  if (r.emoji === '🌊' || r.emoji === '🛶') return 'compass'
  return AREA_META[r.area]?.icon || 'route'
}

const previewRoute = ref<RouteDef | null>(null)
const selectedStopIndex = ref(0)
const currentPreviewStop = computed<RouteStop | null>(() => {
  if (!previewRoute.value || !previewRoute.value.stops) return null
  return previewRoute.value.stops[selectedStopIndex.value] || null
})

function openRoutePreview(r: RouteDef) {
  previewRoute.value = r
  selectedStopIndex.value = 0
}

function closeRoutePreview() {
  previewRoute.value = null
}

function stopCoords(index: number, total: number): [number, number] {
  if (total <= 1) return [300, 160]
  const progress = index / (total - 1)
  const x = 70 + progress * 460
  const wave = Math.sin(progress * Math.PI * 2) * 45
  const alt = (index % 2 === 1 ? 20 : -20)
  const y = 160 + wave + alt
  return [Math.round(x), Math.round(y)]
}

function routeSvgPath(stops?: any[]): string {
  if (!stops || !stops.length) return ''
  return stops.map((_, i) => {
    const [x, y] = stopCoords(i, stops.length)
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
  }).join(' ')
}

function onModalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && previewRoute.value) {
    closeRoutePreview()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onModalKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onModalKeydown)
})

useSeoMeta({
  ogType: 'website',
  title: () => pc('seo_title') || 'Tuyến đường gợi ý Vĩnh Long — vinhlong360',
  description: () => pc('seo_description') || 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  ogTitle: () => pc('og_title') || 'Tuyến đường gợi ý — vinhlong360',
  ogDescription: () => pc('og_description') || 'Tự khám phá Vĩnh Long bằng xe máy hoặc ô tô.',
  ogUrl: () => canonicalUrl('/tuyen-duong'),
  twitterCard: 'summary_large_image',
})

useHead(() => {
  const pageUrl = canonicalUrl('/tuyen-duong')
  const schemaGraph = buildRoutesCatalogSchemaGraph({
    routes: ROUTES.value.map((r: any) => ({
      id: r.id,
      name: r.name,
      description: r.description,
      duration: r.duration,
      distance: r.distance,
      area: r.area,
      stops: r.stops,
    })),
    totalCount: ROUTES.value.length,
    canonicalUrl: pageUrl,
  })

  return {
    link: [{ rel: 'canonical', href: pageUrl }],
    script: [{
      type: 'application/ld+json',
      innerHTML: safeJsonLd(schemaGraph),
    }],
  }
})
</script>

<style scoped>
.route-grid { display: flex; flex-direction: column; gap: var(--space-6); }
.route-card { position: relative; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); overflow: hidden; box-shadow: var(--shadow-sm); transition: transform .35s cubic-bezier(0.16, 1, 0.3, 1), box-shadow .35s cubic-bezier(0.16, 1, 0.3, 1), border-color .3s var(--ease-out); }
/* glassy top-sheen, revealed on hover for an Apple-style finish */
.route-card::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 40%; pointer-events: none; opacity: 0; background: linear-gradient(180deg, rgba(var(--white-rgb),.18), transparent); transition: opacity .35s var(--ease-out); z-index: 2; }
.route-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--color-action-rgb), .14), 0 18px 40px -18px rgba(var(--color-action-rgb), .25); border-color: var(--border); }
.route-card:hover::before { opacity: .9; }
.route-card:active { transform: translateY(0) scale(.99); transition-duration: .08s; }
.route-header { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-5) var(--space-6); color: var(--text-on-dark, var(--white)); box-shadow: inset 0 1px 0 rgba(var(--white-rgb),.15), 0 1px 2px rgba(var(--black-rgb),.1); transition: background .3s var(--ease-out); }
.route-header h3 { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); text-shadow: var(--shadow-text); overflow-wrap: break-word; word-break: break-word; }
.route-meta { font-size: var(--text-sm); opacity: .9; }
.route-emoji { font-size: var(--text-2xl); display: inline-flex; align-items: center; justify-content: center; color: currentColor; }
.chip-area-icon { margin-right: .25rem; font-size: .95em; }
.route-header.area-vinh-long { background: var(--cat-experience); }
.route-header.area-ben-tre {
  background: var(--cat-product);
  color: var(--mekong-ink);
}
.route-header.area-ben-tre h3,
.route-header.area-ben-tre .route-name,
.route-header.area-ben-tre .route-meta,
.route-header.area-ben-tre .route-emoji {
  color: var(--mekong-ink);
  text-shadow: none;
}
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
.rstat-num { font-size: var(--text-lg); font-weight: var(--weight-extrabold); color: var(--color-action); letter-spacing: var(--tracking-tight); font-variant-numeric: tabular-nums; line-height: 1.2; overflow-wrap: break-word; }
.rstat-label { font-size: var(--text-2xs); color: var(--muted); text-transform: uppercase; letter-spacing: var(--tracking-caps); font-weight: var(--weight-semibold); }

/* ── Season cross-tag → /theo-mua (§2.5 highest-leverage cross-link) ── */
.route-season-tag {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--secondary-fg);
  background: rgba(var(--secondary-rgb), .1); border: .5px solid rgba(var(--secondary-rgb), .22);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-pill, 999px);
  margin-bottom: var(--space-4); min-height: 44px;
  transition: background .25s var(--ease-out), border-color .25s var(--ease-out);
}
.route-season-tag:hover { background: rgba(var(--secondary-rgb), .18); border-color: rgba(var(--secondary-rgb), .35); }
.route-season-tag:focus-visible { outline: 2px solid var(--secondary); outline-offset: 2px; }

/* ── Signature: day-strip rail — the path drawing itself, dot by dot ──
   Replaces the plain <ol> bullet list. Vertical hairline + numbered dots,
   tinted per area (echoes the tri-province sediment gradient when a route
   crosses all 3 — see .area-lien-vung below). */
.route-rail { position: relative; list-style: none; margin: 0 0 var(--space-4); padding: 0 0 0 var(--space-8); }
.route-rail::before {
  content: ""; position: absolute; left: 11px; top: 6px; bottom: 6px; width: 2px;
  background: linear-gradient(180deg, var(--rail-tone, var(--color-action)) 0%, color-mix(in srgb, var(--rail-tone, var(--color-action)) 35%, transparent) 100%);
  border-radius: var(--radius-pill, 999px);
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
  border-radius: var(--radius-control); line-height: var(--leading-normal);
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
  background: var(--card); color: var(--rail-tone, var(--color-action));
  box-shadow: 0 0 0 2px var(--rail-tone, var(--color-action)) inset, var(--shadow-xs);
  transition: transform .3s var(--ease-out-expo), background .25s var(--ease-out), color .25s var(--ease-out);
}
.rail-text strong { color: var(--ink); transition: color .25s var(--ease-out); }
.rail-text span { color: var(--muted); font-size: var(--text-sm); }
.rail-stop:hover { transform: translateX(2px); background: var(--overlay-subtle); }
.rail-stop:hover .rail-dot { transform: scale(1.1); background: var(--rail-tone, var(--color-action)); color: var(--color-on-action); }
.rail-stop:hover .rail-text strong { color: var(--color-action); }
/* hovering a dot nudges the connecting line's tone brighter — "this is a path" */
.route-rail:has(.rail-stop:hover)::before { filter: saturate(1.3) brightness(1.08); }

.route-tips {
  background: var(--badge-season-bg); padding: var(--space-3) var(--space-4); border-radius: var(--radius-control);
  font-size: var(--text-sm); margin-bottom: var(--space-3); line-height: var(--leading-normal);
  border: .5px solid rgba(var(--color-action-rgb), .15); box-shadow: 0 1px 2px rgba(var(--color-action-rgb), .15);
  transition: box-shadow .3s var(--ease-out);
}
.route-tips-eyebrow {
  display: block; font-size: var(--text-2xs); font-weight: var(--weight-bold);
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--color-brand);
  margin-bottom: 2px;
}
/* subtle breathing pulse when the card is hovered, to draw the eye to the tip */
.route-card:hover .route-tips { animation: tips-pulse 2.4s var(--ease-out) infinite; }
@keyframes tips-pulse {
  0%, 100% { box-shadow: 0 1px 2px rgba(var(--color-action-rgb), .15); }
  50%      { box-shadow: 0 1px 8px rgba(var(--color-action-rgb), .25); }
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
.route-links .btn { transition: transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo); }
.route-links .btn:active { transform: scale(.95); transition-duration: .08s; }
.dark .route-card { background: var(--card); border-color: var(--line); }
.dark .route-card::before { background: linear-gradient(180deg, rgba(var(--white-rgb),.07), transparent); }
.dark .route-card:hover { box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--color-action-rgb), .22), 0 18px 44px -18px rgba(var(--black-rgb),.6); border-color: var(--border); }
.dark .route-tips { background: rgba(var(--white-rgb),.06); border-color: rgba(var(--white-rgb),.1); }
.dark .route-body p { color: rgba(var(--white-rgb),.85); }
.dark .rail-stop:hover .rail-text strong { color: var(--color-action); }
.dark .rail-text span { color: rgba(var(--white-rgb),.55); }
.dark .rail-dot { background: var(--card); box-shadow: 0 0 0 2px var(--rail-tone, var(--color-action)) inset, 0 1px 3px rgba(var(--black-rgb),.4); }
.dark .route-stat-trio { border-color: var(--line); }
.dark .rstat-num { color: var(--color-action); }
.dark .route-season-tag { background: rgba(var(--secondary-rgb), .16); border-color: rgba(var(--secondary-rgb), .3); }
.dark .route-season-tag:hover { background: rgba(var(--secondary-rgb), .24); }
.dark .route-header.area-lien-vung { background: linear-gradient(135deg, var(--river-legacy-dark), var(--amber-500) 55%, var(--clay-400)); }
.dark .route-card.area-lien-vung .route-rail::before { background: linear-gradient(180deg, var(--river-legacy-dark) 0%, var(--amber-500) 50%, var(--clay-400) 100%); }

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
  .route-card:hover .route-tips { animation: none; box-shadow: 0 1px 8px rgba(var(--color-action-rgb), .25); }
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
.dark .rv-river { stroke: var(--river-legacy-dark); }
.dark .rv-road { stroke: var(--clay-400); }
.dark .rv-pin.area-tra-vinh .rv-pin-dot { background: var(--river-legacy-dark); }
.dark .rv-pin.area-lien-vung .rv-pin-dot { background: var(--clay-400); }
.dark .rv-pin-dot { box-shadow: 0 0 0 2px var(--card), 0 1px 3px rgba(var(--black-rgb),.4); }
@media (max-width: 640px) {
  .route-vignette { height: 52px; }
  .rv-labels { font-size: var(--text-2xs, 11px); }
}

/* ── Interactive Route Preview Modal ── */
.route-preview-btn {
  color: var(--color-action);
}
.route-preview-btn:hover {
  background: rgba(var(--color-action-rgb), 0.1);
}
.route-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(var(--black-rgb), 0.65);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-4);
  animation: modalFadeIn 0.2s var(--ease-out);
}
@keyframes modalFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.route-preview-dialog {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-sheet);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 920px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: dialogSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes dialogSlideUp {
  from { transform: translateY(16px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.route-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  color: var(--text-on-dark, var(--white));
  background: var(--color-action);
}
.route-preview-header.area-vinh-long { background: var(--cat-experience); }
.route-preview-header.area-ben-tre {
  background: var(--cat-product);
  color: var(--mekong-ink);
}
.route-preview-header.area-ben-tre .route-preview-title,
.route-preview-header.area-ben-tre .route-preview-kicker,
.route-preview-header.area-ben-tre .route-preview-close {
  color: var(--mekong-ink);
}
.route-preview-header.area-tra-vinh { background: var(--cat-attraction); }
.route-preview-header.area-lien-vung { background: linear-gradient(135deg, var(--river-600), var(--amber-600) 55%, var(--clay-600)); }
.route-preview-kicker {
  display: block;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  opacity: 0.9;
}
.route-preview-title {
  margin: 0;
  font-size: var(--text-xl);
  font-family: var(--font-editorial);
  font-style: italic;
  font-weight: var(--weight-bold);
}
.route-preview-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border-radius: var(--radius-pill, 999px);
  background: rgba(var(--white-rgb), 0.2);
  color: currentColor;
  border: none;
  cursor: pointer;
  transition: background 0.2s var(--ease-out);
}
.route-preview-close:hover {
  background: rgba(var(--white-rgb), 0.35);
}
.route-preview-close:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.route-preview-body {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-4);
  padding: var(--space-5);
  overflow-y: auto;
  max-height: calc(90vh - 80px);
}
.route-preview-map-pane {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.route-preview-map-canvas {
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius-surface);
  overflow: hidden;
}
.route-map-svg {
  width: 100%;
  height: auto;
  display: block;
}
.route-path-line {
  stroke-linecap: round;
  animation: routeDash 20s linear infinite;
}
@keyframes routeDash {
  to { stroke-dashoffset: -100; }
}
.route-waypoint-pin {
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  outline: none;
}
.waypoint-circle {
  fill: var(--card);
  stroke: var(--color-action);
  stroke-width: 3;
  transition: all 0.2s var(--ease-out);
}
.waypoint-num {
  font-size: 11px;
  font-weight: var(--weight-bold);
  fill: var(--ink);
}
.waypoint-name-label {
  font-size: 11px;
  font-weight: var(--weight-medium);
  fill: var(--muted);
  pointer-events: none;
}
.route-waypoint-pin:hover .waypoint-circle,
.route-waypoint-pin:focus-visible .waypoint-circle {
  fill: var(--color-action);
  transform: scale(1.15);
  transform-origin: center;
}
.route-waypoint-pin:hover .waypoint-num,
.route-waypoint-pin:focus-visible .waypoint-num {
  fill: var(--color-on-action, var(--white));
}
.route-waypoint-pin:hover .waypoint-name-label,
.route-waypoint-pin:focus-visible .waypoint-name-label {
  fill: var(--color-action);
  font-weight: var(--weight-bold);
}
.route-waypoint-pin.is-active .waypoint-circle {
  fill: var(--color-action);
  stroke: var(--card);
  stroke-width: 4;
  filter: drop-shadow(0 0 6px rgba(var(--color-action-rgb), 0.5));
}
.route-waypoint-pin.is-active .waypoint-num {
  fill: var(--color-on-action, var(--white));
}
.route-waypoint-pin.is-active .waypoint-name-label {
  fill: var(--color-action);
  font-weight: var(--weight-bold);
}
.route-waypoint-info-card {
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius-surface);
  padding: var(--space-4);
}
.waypoint-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.waypoint-order-badge {
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  font-weight: var(--weight-bold);
  color: var(--color-brand);
}
.waypoint-card-nav {
  display: flex;
  gap: var(--space-2);
}
.waypoint-card-nav .btn {
  min-height: 44px;
}
.waypoint-card-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--ink);
}
.waypoint-card-note {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--muted);
}
.route-preview-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.route-preview-sidebar-title {
  margin: 0;
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  font-weight: var(--weight-bold);
  color: var(--muted);
}
.route-preview-stops-rail {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 280px;
  overflow-y: auto;
}
.preview-rail-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-control);
  cursor: pointer;
  min-height: 44px;
  transition: background 0.2s var(--ease-out);
  outline: none;
}
.preview-rail-item:hover {
  background: var(--overlay-subtle);
}
.preview-rail-item:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 1px;
}
.preview-rail-item.is-selected {
  background: color-mix(in srgb, var(--color-action) 12%, var(--card));
  border: 1px solid var(--color-action);
}
.preview-rail-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  border-radius: 50%;
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  background: var(--bg-alt);
  color: var(--color-action);
  border: 1px solid var(--line);
}
.preview-rail-item.is-selected .preview-rail-badge {
  background: var(--color-action);
  color: var(--color-on-action, var(--white));
  border-color: var(--color-action);
}
.preview-rail-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.preview-rail-meta strong {
  font-size: var(--text-sm);
  color: var(--ink);
}
.preview-rail-meta span {
  font-size: var(--text-xs);
  color: var(--muted);
}
.route-preview-dialog-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: auto;
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
}
.preview-action-btn {
  min-height: 44px;
}
.dark .route-modal-backdrop {
  background: rgba(var(--black-rgb), 0.75);
}
.dark .route-preview-dialog {
  background: var(--card);
  border-color: var(--line);
}
.dark .waypoint-num {
  fill: var(--ink);
}
.dark .preview-rail-item:hover {
  background: var(--overlay-light);
}
@media (max-width: 768px) {
  .route-preview-body {
    grid-template-columns: 1fr;
  }
  .route-preview-dialog {
    max-height: 95vh;
  }
}

/* ── High-Glare Outdoor Contrast Mode (>= 14:1) ── */
[data-outdoor-contrast="high"] .route-card {
  border: 2px solid var(--contrast-glare-border);
  background: var(--contrast-glare-bg);
  box-shadow: none;
}
[data-outdoor-contrast="high"] .route-preview-dialog {
  border: 2px solid var(--contrast-glare-border);
  background: var(--contrast-glare-bg);
}
[data-outdoor-contrast="high"] .route-preview-map-canvas {
  filter: var(--contrast-glare-map-filter, contrast(1.6) saturate(1.2) brightness(0.95));
}
[data-outdoor-contrast="high"] .route-map-svg {
  background: var(--contrast-glare-bg);
}
[data-outdoor-contrast="high"] .route-path-line {
  stroke: var(--contrast-glare-border) !important;
  stroke-width: 4px !important;
  stroke-dasharray: none !important;
}
[data-outdoor-contrast="high"] .waypoint-circle {
  fill: var(--contrast-glare-bg) !important;
  stroke: var(--contrast-glare-border) !important;
  stroke-width: 3px !important;
}
[data-outdoor-contrast="high"] .route-waypoint-pin.is-active .waypoint-circle {
  fill: var(--contrast-glare-fg) !important;
}
[data-outdoor-contrast="high"] .waypoint-num {
  fill: var(--contrast-glare-fg) !important;
  font-weight: 700 !important;
}
[data-outdoor-contrast="high"] .route-waypoint-pin.is-active .waypoint-num {
  fill: var(--contrast-glare-bg) !important;
}
[data-outdoor-contrast="high"] .waypoint-name-label {
  fill: var(--contrast-glare-fg) !important;
  font-weight: 700 !important;
}
</style>
