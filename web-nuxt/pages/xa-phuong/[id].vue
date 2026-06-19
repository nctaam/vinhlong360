<template>
  <div v-if="fetchFailed" class="page">
    <EmptyState icon="⚠️" title="Không thể tải trang" message="Lỗi kết nối. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`ward-${id}`)">Thử lại</button>
    </EmptyState>
  </div>

  <div v-else-if="!data?.place" class="page">
    <EmptyState message="Không tìm thấy xã/phường này." />
  </div>

  <div v-else class="wp">
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li><NuxtLink to="/">Trang chủ</NuxtLink></li>
        <li v-if="data.place.area"><NuxtLink :to="`/khu-vuc/${data.place.area}`">{{ areaMeta.name }}</NuxtLink></li>
        <li aria-current="page">{{ data.place.name }}</li>
      </ol>
    </nav>

    <!-- Hero -->
    <header class="wp-hero" :class="`area-${data.place.area}`">
      <div class="wp-hero-inner">
        <span class="wp-level">{{ data.place.level === 'phuong' ? 'Phường' : 'Xã' }}</span>
        <h1>{{ data.place.name }}</h1>
        <p class="wp-region">
          <span class="wp-region-emoji">{{ areaMeta.emoji }}</span>
          <NuxtLink :to="`/khu-vuc/${data.place.area}`">{{ areaMeta.name }}</NuxtLink>
        </p>
        <div v-if="hasStats" class="wp-stats">
          <div v-if="attrs.area_km2" class="wp-stat">
            <span class="wp-stat-val">{{ attrs.area_km2 }} km²</span>
            <span class="wp-stat-label">Diện tích</span>
          </div>
          <div v-if="attrs.population" class="wp-stat">
            <span class="wp-stat-val">{{ formatPop(attrs.population) }}</span>
            <span class="wp-stat-label">Dân số</span>
          </div>
          <div class="wp-stat">
            <span class="wp-stat-val">{{ totalContent }}</span>
            <span class="wp-stat-label">Địa điểm</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Summary -->
    <p v-if="data.place.summary" class="wp-summary">{{ data.place.summary }}</p>

    <!-- Map -->
    <ClientOnly>
      <section v-if="data.place.coordinates" class="wp-map-sec">
        <div ref="mapEl" class="wp-map-container"></div>
      </section>
    </ClientOnly>

    <!-- Main content -->
    <div class="wp-body">
      <div class="wp-main">
        <!-- Tham quan nổi bật -->
        <section v-if="data.tourism?.length" class="wp-sec">
          <h2><span class="sec-icon">🗺️</span> Địa điểm tham quan <span class="cnt">({{ data.tourism.length }})</span></h2>
          <div class="wp-grid">
            <EntityCard v-for="e in data.tourism" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Lưu trú -->
        <section v-if="data.lodging?.length" class="wp-sec reveal">
          <h2><span class="sec-icon">🏡</span> Lưu trú <span class="cnt">({{ data.lodging.length }})</span></h2>
          <div class="wp-grid">
            <EntityCard v-for="e in data.lodging" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Sản phẩm -->
        <section v-if="data.products?.length" class="wp-sec reveal">
          <h2><span class="sec-icon">🍊</span> Đặc sản &amp; sản phẩm <span class="cnt">({{ data.products.length }})</span></h2>
          <div class="wp-grid">
            <EntityCard v-for="e in data.products" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Empty state -->
        <p v-if="!totalContent" class="wp-empty">Chưa có dữ liệu địa điểm cho {{ data.place.name }}. Đang bổ sung.</p>
      </div>

      <!-- Sidebar -->
      <aside class="wp-aside">
        <!-- Liên hệ cơ quan -->
        <div class="wp-card">
          <h3>📞 Liên hệ khẩn cấp</h3>
          <div class="wp-contact">
            <div class="wp-contact-item wp-contact-main">
              <span class="wp-contact-label">👮 Công an {{ data.place.name }}</span>
              <a v-if="attrs.police_phone" :href="`tel:${attrs.police_phone.replace(/\\./g, '')}`" class="wp-phone" :aria-label="`Gọi công an ${data.place.name}`">{{ attrs.police_phone }}</a>
              <span v-else class="wp-phone-na">Đang cập nhật</span>
            </div>
          </div>
        </div>

        <!-- Danh bạ hành chính -->
        <div v-if="data.facilities?.length" class="wp-card">
          <h3>🏛️ Danh bạ hành chính</h3>
          <ul class="wp-fac-list">
            <li v-for="f in data.facilities" :key="f.id" class="wp-fac">
              <span class="wp-fac-kind">{{ kindMeta(f).emoji }} {{ kindMeta(f).label }}</span>
              <strong>{{ f.name }}</strong>
              <div v-if="attr(f,'address')" class="wp-fac-row">📍 {{ attr(f,'address') }}</div>
              <div v-if="attr(f,'phone')" class="wp-fac-row">📞 <a :href="`tel:${attr(f,'phone')}`" :aria-label="`Gọi ${f.name}`">{{ attr(f,'phone') }}</a></div>
            </li>
          </ul>
        </div>

        <!-- Map link -->
        <NuxtLink v-if="data.place.coordinates" :to="mapUrl" class="wp-map-btn">
          🗺️ Xem trên bản đồ
        </NuxtLink>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AREA_META, OFFICE_KIND, TYPE_META } from '~/composables/useConstants'

useReveal()

const route = useRoute()
const id = computed(() => route.params.id as string)

const fetchFailed = ref(false)
const { data } = await useAsyncData(`ward-${id.value}`, async () => {
  try {
    fetchFailed.value = false
    return await $fetch<any>(`/api/places/${id.value}/overview`)
  } catch {
    fetchFailed.value = true
    return null
  }
})

const areaMeta = computed(() => AREA_META[data.value?.place?.area] || { name: '', emoji: '📍', blurb: '' })
const attrs = computed(() => data.value?.place?.attributes || {})
const hasStats = computed(() => !!(attrs.value.area_km2 || attrs.value.population))
const totalContent = computed(() => {
  const c = data.value?.counts || {}
  return (c.tourism || 0) + (c.lodging || 0) + (c.products || 0)
})

const mapUrl = computed(() => {
  const c = data.value?.place?.coordinates
  if (!c) return '/ban-do'
  return `/ban-do?lat=${c[0]}&lng=${c[1]}&zoom=15`
})

function formatPop(n: number) {
  return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : String(n)
}

function attr(f: any, k: string) { return (f.attributes || {})[k] }
function kindMeta(f: any) { return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac }

const placeName = computed(() => data.value?.place?.name || 'Xã/Phường')
useSeoMeta({
  title: () => `${placeName.value} — du lịch, lưu trú, đặc sản & danh bạ | vinhlong360`,
  description: () => data.value?.place?.summary || `Tổng hợp địa điểm du lịch, cơ sở lưu trú, sản phẩm đặc sản và danh bạ hành chính của ${placeName.value}.`,
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl(`/xa-phuong/${id.value}`) }],
  script: data.value?.place ? [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org', '@type': 'AdministrativeArea',
      name: data.value.place.name,
      ...(data.value.place.summary ? { description: data.value.place.summary } : {}),
      address: { '@type': 'PostalAddress', addressRegion: areaMeta.value.name, addressCountry: 'VN' },
    }),
  }] : [],
}))

// Map
const mapEl = ref<HTMLElement | null>(null)
const { createMap } = useNDAMap()

function allEntities() {
  const d = data.value
  if (!d) return []
  return [...(d.tourism || []), ...(d.lodging || []), ...(d.products || [])]
}

watch(mapEl, async (el) => {
  if (!el || !data.value?.place?.coordinates) return
  const coords = data.value.place.coordinates
  const { map, maplibregl } = await createMap(el, {
    center: [coords[1], coords[0]],
    zoom: 14,
  })

  map.addControl(new maplibregl.FullscreenControl(), 'top-right')

  // Ward center marker — popup mở mặc định
  const centerPopup = new maplibregl.Popup({ offset: 25, closeOnClick: false })
    .setHTML(`<strong>${data.value.place.name}</strong>`)
  new maplibregl.Marker({ color: '#9C3D22', scale: 1.1 })
    .setLngLat([coords[1], coords[0]])
    .setPopup(centerPopup)
    .addTo(map)
    .togglePopup()

  // Entity markers
  const bounds = new maplibregl.LngLatBounds()
  bounds.extend([coords[1], coords[0]])
  const entities = allEntities()

  for (const ent of entities) {
    const c = ent.coordinates
    if (!c || !c[0] || !c[1]) continue
    const meta = TYPE_META[ent.type] || { emoji: '📍', label: '' }
    const el = document.createElement('div')
    el.className = 'wp-marker'
    el.textContent = meta.emoji
    el.title = ent.name
    new maplibregl.Marker({ element: el })
      .setLngLat([c[1], c[0]])
      .setPopup(new maplibregl.Popup({ offset: 20, maxWidth: '220px' }).setHTML(
        `<a href="/dia-diem/${ent.id}" class="map-popup-link">${ent.name}</a><br><small>${meta.label}</small>`
      ))
      .addTo(map)
    bounds.extend([c[1], c[0]])
  }

  if (entities.length && !bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 60, maxZoom: 16 })
  }
}, { once: true })
</script>

<style scoped>
.wp { max-width: var(--maxw, 1100px); margin: 0 auto; padding: 0 var(--space-4) var(--space-16); }

/* Hero */
.wp-hero { border-radius: var(--radius-lg, 16px); padding: var(--space-8) var(--space-6); margin-top: var(--space-2); color: var(--text-on-dark, #fff); position: relative; overflow: hidden; }
.wp-hero.area-vinh-long { background: linear-gradient(135deg, #9C3D22 0%, #c0542e 50%, #d4764a 100%); }
.wp-hero.area-ben-tre { background: linear-gradient(135deg, #1b7a3d 0%, #27944e 50%, #4bae6a 100%); }
.wp-hero.area-tra-vinh { background: linear-gradient(135deg, #6b3fa0 0%, #8354b8 50%, #a070d0 100%); }
.dark .wp-hero.area-vinh-long { background: linear-gradient(135deg, #6b2815 0%, #8c3a1e 50%, #a35230 100%); }
.dark .wp-hero.area-ben-tre { background: linear-gradient(135deg, #0e4f24 0%, #186332 50%, #30834a 100%); }
.dark .wp-hero.area-tra-vinh { background: linear-gradient(135deg, #42267a 0%, #5c3893 50%, #764fb0 100%); }
.wp-hero-inner { position: relative; z-index: 1; }
.wp-level { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .06em; opacity: .85; font-weight: var(--weight-bold); }
.wp-hero h1 { margin: var(--space-1) 0 var(--space-1); font-size: clamp(1.5rem, 4vw, 1.8rem); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); }
.wp-region { margin: 0; opacity: .9; font-size: var(--text-sm); }
.wp-region a { color: var(--text-on-dark, #fff); text-decoration: underline; text-underline-offset: 3px; border-radius: var(--radius-sm); }
.wp-region a:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 2px; }
.wp-region-emoji { margin-inline-end: var(--space-1); }

.wp-stats { display: flex; gap: var(--space-6); margin-top: var(--space-5); padding-top: var(--space-4); border-top: .5px solid rgba(255,255,255,.25); }
.wp-stat { text-align: center; }
.wp-stat-val { display: block; font-size: var(--text-xl); font-weight: var(--weight-extrabold); }
.wp-stat-label { font-size: var(--text-xs); opacity: .8; text-transform: uppercase; letter-spacing: .03em; }

/* Summary */
.wp-summary { max-width: 72ch; font-size: var(--text-base); line-height: var(--leading-relaxed); color: var(--ink); margin: var(--space-5) 0 var(--space-1); }

/* Map */
.wp-map-sec { margin: var(--space-5) 0 var(--space-2); }
.wp-map-container { width: 100%; height: 380px; border-radius: var(--radius-lg, 16px); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); transition: box-shadow .35s var(--ease-out-expo); }
:deep(.wp-marker) { font-size: 1.6rem; cursor: pointer; filter: drop-shadow(0 1px 3px rgba(0,0,0,.4)); line-height: 1; transition: transform .35s var(--ease-spring-gentle); }
:deep(.wp-marker:hover) { transform: scale(1.25); }

/* Body layout */
.wp-body { display: grid; grid-template-columns: 1fr 320px; gap: var(--space-6); margin-top: var(--space-5); align-items: start; }

/* Sections */
.wp-sec { margin-bottom: var(--space-6); }
.wp-sec h2 { font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0 0 var(--space-4); display: flex; align-items: center; gap: var(--space-2); }
.sec-icon { font-size: var(--text-lg); }
.cnt { color: var(--muted); font-weight: var(--weight-normal); font-size: var(--text-sm); }
.wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: var(--space-4); }
.wp-empty { color: var(--muted); font-size: var(--text-sm); padding: var(--space-5) 0; }

/* Sidebar cards */
.wp-aside { display: flex; flex-direction: column; gap: var(--space-4); position: sticky; top: 78px; }
.wp-card { background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg, 16px); padding: var(--space-5); box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.wp-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.wp-card h3 { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: 0 0 var(--space-3); }

/* Contact list */
.wp-contact { display: flex; flex-direction: column; gap: var(--space-3); }
.wp-contact-item { display: flex; flex-direction: column; gap: 2px; padding: var(--space-2) 0; border-bottom: .5px solid var(--line); }
.wp-contact-item:last-child { border-bottom: none; padding-bottom: 0; }
.wp-contact-main { background: var(--bg-warm, #faf6f2); border-radius: var(--radius-sm); padding: var(--space-3); border-bottom: none; margin-bottom: 2px; }
.wp-contact-label { font-size: var(--text-xs); color: var(--muted); }
.wp-phone { font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--primary); min-height: 44px; display: inline-flex; align-items: center; }
.wp-phone:hover { text-decoration: underline; }
.wp-phone:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.wp-phone-na { font-size: var(--text-sm); color: var(--muted); font-style: italic; }

/* Facilities */
.wp-fac-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-3); }
.wp-fac { padding: var(--space-2) 0; border-bottom: .5px solid var(--line); transition: background .3s var(--ease-out); border-radius: var(--radius-sm); }
.wp-fac:hover { background: var(--bg-warm); }
.wp-fac:last-child { border-bottom: none; }
.wp-fac-kind { font-size: var(--text-xs); color: var(--primary); display: block; margin-bottom: 2px; }
.wp-fac-row { font-size: var(--text-sm); color: var(--muted); margin-top: 2px; }
.wp-fac-row a { color: var(--primary); }
.wp-fac-row a:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* Map button */
.wp-map-btn { display: flex; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-3); border-radius: var(--radius-lg, 16px); background: var(--bg-warm, #faf6f2); border: .5px solid var(--line); font-weight: var(--weight-bold); font-size: var(--text-sm); color: var(--ink); min-height: 44px; transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out); }
.wp-map-btn:hover { background: var(--line); transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.wp-map-btn:active { transform: scale(.97); transition-duration: .08s; }
.wp-map-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* Responsive */
@media (max-width: 840px) {
  .wp-body { grid-template-columns: 1fr; }
  .wp-aside { position: static; }
}
@media (max-width: 480px) {
  .wp-hero { padding: var(--space-6) var(--space-5); border-radius: var(--radius-md); }
  .wp-hero h1 { font-size: 1.4rem; }
  .wp-stats { gap: var(--space-4); }
  .wp-stat-val { font-size: 1.1rem; }
  .wp-map-container { height: 260px; border-radius: var(--radius-sm); }
}

/* Dark mode */
.dark .wp-card { background: var(--card); border-color: var(--line); }
.dark .wp-card:hover { box-shadow: var(--shadow-lg); }
.dark .wp-contact-main { background: var(--glass-subtle); }
.dark .wp-phone { color: var(--primary-fg); }
.dark .wp-fac:hover { background: var(--glass-subtle); }
.dark .wp-fac-row a { color: var(--primary-fg); }
.dark .wp-map-btn { background: var(--glass-subtle); border-color: var(--line); color: var(--ink); }
.dark .wp-map-btn:hover { background: var(--glass-light); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .wp-card:hover { transform: none; }
  .wp-map-btn:hover { transform: none; }
  .wp-map-btn:active { transform: none; }
  :deep(.wp-marker:hover) { transform: none; }
}
</style>
