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
    </section>

    <div class="controls">
      <p class="control-label">Khu vực</p>
      <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
        <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = key as string"
        >{{ meta.emoji }} {{ meta.name }}</button>
      </div>
    </div>

    <!-- Editorial -->
    <section class="page-article reveal">
      <h2>Tự khám phá miền Tây bằng xe máy hoặc ô tô</h2>
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

    <section class="reveal">
    <div v-if="filtered.length" class="route-grid">
      <article v-for="r in filtered" :key="r.id" class="route-card" :aria-label="r.name + ' — ' + r.duration">
        <div :class="['route-header', `area-${r.area}`]">
          <span class="route-emoji">{{ r.emoji }}</span>
          <div>
            <h3>{{ r.name }}</h3>
            <span class="route-meta">{{ r.duration }} · {{ r.distance }}</span>
          </div>
        </div>
        <div class="route-body">
          <p>{{ r.description }}</p>
          <h3>Điểm dừng chân</h3>
          <ol class="route-stops">
            <li v-for="(stop, i) in r.stops" :key="i">
              <strong>{{ stop.name }}</strong>
              <span v-if="stop.note"> — {{ stop.note }}</span>
            </li>
          </ol>
          <div class="route-tips" v-if="r.tips">
            <strong>💡 Mẹo:</strong> {{ r.tips }}
          </div>
          <div class="route-links">
            <NuxtLink :to="`/khu-vuc/${r.area}`" class="btn btn-outline btn-sm">📍 {{ AREA_META[r.area]?.name }}</NuxtLink>
            <NuxtLink to="/ban-do" no-prefetch class="btn btn-ghost btn-sm">🗺️ Xem bản đồ</NuxtLink>
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
    </section>

    <!-- Cross-links -->
    <section class="block band catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <p class="cross-sub">Tiếp tục hành trình miền Tây của bạn</p>
      <div class="cross-links">
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { DEFAULT_ROUTES } from '~/utils/routesContent'

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
.route-body { padding: var(--space-5) var(--space-6); }
.route-body p { margin: 0 0 var(--space-3); line-height: var(--leading-relaxed); color: var(--ink); }
.route-body h3 { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: var(--space-4) 0 var(--space-2); }
.route-stops { margin: 0 0 var(--space-3); padding-inline-start: var(--space-5); }
.route-stops li { margin-bottom: var(--space-2); padding: 2px var(--space-2); margin-left: calc(var(--space-2) * -1); border-radius: var(--radius-sm); line-height: var(--leading-normal); transition: transform .3s var(--ease-out), background .25s var(--ease-out); animation: stopFadeIn .4s var(--ease-out) both; }
.route-stops li:nth-child(1) { animation-delay: 40ms; }
.route-stops li:nth-child(2) { animation-delay: 80ms; }
.route-stops li:nth-child(3) { animation-delay: 120ms; }
.route-stops li:nth-child(4) { animation-delay: 160ms; }
.route-stops li:nth-child(5) { animation-delay: 200ms; }
.route-stops li:nth-child(n+6) { animation-delay: 240ms; }
@keyframes stopFadeIn { from { opacity: 0; transform: translateY(4px); } }
.route-stops li:hover { transform: translateX(2px); background: var(--overlay-subtle); }
.route-stops li:hover strong { color: var(--primary-fg); }
.route-stops strong { color: var(--ink); transition: color .25s var(--ease-out); }
.route-stops span { color: var(--muted); font-size: var(--text-sm); }
.route-tips { background: var(--badge-season-bg); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm); font-size: var(--text-sm); margin-bottom: var(--space-3); line-height: var(--leading-normal); border: .5px solid rgba(var(--primary-rgb), .15); box-shadow: 0 1px 2px rgba(var(--primary-rgb), .2); transition: box-shadow .3s var(--ease-out); }
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
.dark .route-stops li:hover strong { color: var(--primary); }
.dark .route-stops span { color: rgba(255,255,255,.55); }

/* Mobile: tighten card padding so emoji + name don't crowd narrow screens */
@media (max-width: 640px) {
  .route-header { padding: var(--space-4) var(--space-5); }
  .route-body { padding: var(--space-4) var(--space-5); }
  .route-stops li { line-height: var(--leading-relaxed); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .route-card:hover { transform: none; }
  .route-card:active { transform: none; }
  .route-card:hover::before { opacity: 0; }
  .route-stops li:hover { transform: none; }
  .route-links .btn:active { transform: none; }
  .route-grid > .route-card { animation: none; }
  .route-stops li { animation: none; }
  .route-card:hover .route-tips { animation: none; box-shadow: 0 1px 8px rgba(var(--primary-rgb), .28); }
}
</style>
