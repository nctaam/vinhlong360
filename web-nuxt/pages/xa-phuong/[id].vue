<template>
  <div v-if="!data?.place" class="page">
    <p class="empty" style="padding:40px 0">Không tìm thấy xã/phường này.</p>
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
        <section v-if="data.lodging?.length" class="wp-sec">
          <h2><span class="sec-icon">🏡</span> Lưu trú <span class="cnt">({{ data.lodging.length }})</span></h2>
          <div class="wp-grid">
            <EntityCard v-for="e in data.lodging" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Sản phẩm -->
        <section v-if="data.products?.length" class="wp-sec">
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
              <a v-if="attrs.police_phone" :href="`tel:${attrs.police_phone.replace(/\\./g, '')}`" class="wp-phone">{{ attrs.police_phone }}</a>
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
              <div v-if="attr(f,'phone')" class="wp-fac-row">📞 <a :href="`tel:${attr(f,'phone')}`">{{ attr(f,'phone') }}</a></div>
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

const route = useRoute()
const id = computed(() => route.params.id as string)

const { data } = await useAsyncData(`ward-${id.value}`, () =>
  $fetch<any>(`/api/places/${id.value}/overview`).catch(() => null))

if (!data.value?.place) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy xã/phường', fatal: true })
}

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
        `<a href="/dia-diem/${ent.id}" style="font-weight:700;color:#9C3D22">${ent.name}</a><br><small>${meta.label}</small>`
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
.wp { max-width: var(--maxw, 1100px); margin: 0 auto; padding: 0 16px 64px; }

/* Hero */
.wp-hero { border-radius: 16px; padding: 32px 28px; margin-top: 8px; color: #fff; position: relative; overflow: hidden; }
.wp-hero.area-vinh-long { background: linear-gradient(135deg, #9C3D22 0%, #c0542e 50%, #d4764a 100%); }
.wp-hero.area-ben-tre { background: linear-gradient(135deg, #1b7a3d 0%, #27944e 50%, #4bae6a 100%); }
.wp-hero.area-tra-vinh { background: linear-gradient(135deg, #6b3fa0 0%, #8354b8 50%, #a070d0 100%); }
.wp-hero-inner { position: relative; z-index: 1; }
.wp-level { font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; opacity: .85; font-weight: 700; }
.wp-hero h1 { margin: 4px 0 6px; font-size: 1.8rem; }
.wp-region { margin: 0; opacity: .9; }
.wp-region a { color: #fff; text-decoration: underline; text-underline-offset: 2px; }
.wp-region-emoji { margin-right: 4px; }

.wp-stats { display: flex; gap: 24px; margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.25); }
.wp-stat { text-align: center; }
.wp-stat-val { display: block; font-size: 1.3rem; font-weight: 800; }
.wp-stat-label { font-size: .75rem; opacity: .8; text-transform: uppercase; letter-spacing: .03em; }

/* Summary */
.wp-summary { max-width: 72ch; font-size: 1rem; line-height: 1.65; color: var(--ink); margin: 20px 0 4px; }

/* Map */
.wp-map-sec { margin: 20px 0 8px; }
.wp-map-container { width: 100%; height: 380px; border-radius: 14px; overflow: hidden; border: 1px solid var(--line); }
:deep(.wp-marker) { font-size: 1.6rem; cursor: pointer; filter: drop-shadow(0 1px 3px rgba(0,0,0,.4)); line-height: 1; transition: transform .15s; }
:deep(.wp-marker:hover) { transform: scale(1.3); }

/* Body layout */
.wp-body { display: grid; grid-template-columns: 1fr 320px; gap: 28px; margin-top: 20px; align-items: start; }

/* Sections */
.wp-sec { margin-bottom: 28px; }
.wp-sec h2 { font-size: 1.15rem; margin: 0 0 14px; display: flex; align-items: center; gap: 6px; }
.sec-icon { font-size: 1.2rem; }
.cnt { color: var(--muted); font-weight: 400; font-size: .88rem; }
.wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }
.wp-empty { color: var(--muted); font-size: .92rem; padding: 20px 0; }

/* Sidebar cards */
.wp-aside { display: flex; flex-direction: column; gap: 16px; position: sticky; top: 78px; }
.wp-card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius, 12px); padding: 18px; box-shadow: var(--shadow); }
.wp-card h3 { font-size: 1rem; margin: 0 0 12px; }

/* Contact list */
.wp-contact { display: flex; flex-direction: column; gap: 10px; }
.wp-contact-item { display: flex; flex-direction: column; gap: 2px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.wp-contact-item:last-child { border-bottom: none; padding-bottom: 0; }
.wp-contact-main { background: var(--bg-warm, #faf6f2); border-radius: 8px; padding: 10px 12px; border-bottom: none; margin-bottom: 2px; }
.wp-contact-label { font-size: .82rem; color: var(--muted); }
.wp-phone { font-size: 1.05rem; font-weight: 700; color: var(--primary); }
.wp-phone:hover { text-decoration: underline; }
.wp-phone-na { font-size: .88rem; color: var(--muted); font-style: italic; }

/* Facilities */
.wp-fac-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.wp-fac { padding: 8px 0; border-bottom: 1px solid var(--line); }
.wp-fac:last-child { border-bottom: none; }
.wp-fac-kind { font-size: .75rem; color: var(--primary); display: block; margin-bottom: 2px; }
.wp-fac-row { font-size: .85rem; color: var(--muted); margin-top: 2px; }
.wp-fac-row a { color: var(--primary); }

/* Map button */
.wp-map-btn { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px; border-radius: var(--radius, 12px); background: var(--bg-warm, #faf6f2); border: 1px solid var(--line); font-weight: 700; font-size: .92rem; color: var(--ink); transition: background .12s; }
.wp-map-btn:hover { background: var(--line); }

/* Responsive */
@media (max-width: 840px) {
  .wp-body { grid-template-columns: 1fr; }
  .wp-aside { position: static; }
}
@media (max-width: 480px) {
  .wp-hero { padding: 24px 20px; border-radius: 12px; }
  .wp-hero h1 { font-size: 1.4rem; }
  .wp-stats { gap: 16px; }
  .wp-stat-val { font-size: 1.1rem; }
  .wp-map-container { height: 260px; border-radius: 10px; }
}
</style>
