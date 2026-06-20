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
          <span class="stat-num">{{ ROUTES.length }}</span>
          <span class="stat-label">tuyến đường</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">3</span>
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

    <div v-if="filtered.length" class="route-grid">
      <div v-for="r in filtered" :key="r.id" class="route-card">
        <div :class="['route-header', `area-${r.area}`]">
          <span class="route-emoji">{{ r.emoji }}</span>
          <div>
            <h2>{{ r.name }}</h2>
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
      </div>
    </div>

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Khám phá thêm</h2>
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
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tuyen-duong') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Tuyến đường gợi ý miền Tây',
      description: 'Các tuyến đường tự khám phá qua miệt vườn, làng nghề và văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/tuyen-duong',
    }),
  }],
})
</script>

<style scoped>
.route-grid { display: flex; flex-direction: column; gap: var(--space-6); }
.route-card { background: var(--card); border: .5px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.route-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.route-card:active { transform: translateY(0) scale(.99); transition-duration: .08s; }
.route-header { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-5) var(--space-6); color: var(--text-on-dark, #fff); }
.route-header h2 { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); }
.route-meta { font-size: var(--text-sm); opacity: .9; }
.route-emoji { font-size: var(--text-3xl); }
.route-header.area-vinh-long { background: var(--cat-experience); }
.route-header.area-ben-tre { background: var(--cat-product); }
.route-header.area-tra-vinh { background: var(--cat-attraction); }
.route-body { padding: var(--space-5) var(--space-6); }
.route-body p { margin: 0 0 var(--space-3); line-height: var(--leading-relaxed); color: var(--ink); }
.route-body h3 { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: var(--space-4) 0 var(--space-2); }
.route-stops { margin: 0 0 var(--space-3); padding-inline-start: var(--space-5); }
.route-stops li { margin-bottom: var(--space-2); line-height: var(--leading-normal); transition: transform .3s var(--ease-out); }
.route-stops li:hover { transform: translateX(2px); }
.route-stops strong { color: var(--ink); }
.route-stops span { color: var(--muted); font-size: var(--text-sm); }
.route-tips { background: var(--badge-season-bg); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm); font-size: var(--text-sm); margin-bottom: var(--space-3); line-height: var(--leading-normal); }
.route-links { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.route-links .btn { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.route-links .btn:active { transform: scale(.95); transition-duration: .08s; }
.dark .route-card { background: var(--card); border-color: var(--line); }
.dark .route-card:hover { box-shadow: var(--shadow-lg); border-color: var(--border); }
.dark .route-tips { background: rgba(var(--primary-rgb), .08); }
.dark .route-body p { color: var(--ink); }
.dark .route-stops span { color: var(--ink-tertiary); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .route-card:hover { transform: none; }
  .route-card:active { transform: none; }
  .route-stops li:hover { transform: none; }
  .route-links .btn:active { transform: none; }
}
</style>
