<template>
  <section v-if="fetchFailed" class="page">
    <EmptyState icon="⚠️" title="Không thể tải trang" message="Lỗi kết nối. Vui lòng thử lại.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`ward-${id}`)">Thử lại</button>
    </EmptyState>
  </section>

  <section v-else-if="!data?.place" class="page">
    <EmptyState icon="🔍" title="Không tìm thấy xã/phường" message="Có thể đơn vị hành chính đã được sắp xếp lại hoặc đường dẫn chưa đúng.">
      <template #actions>
        <NuxtLink to="/danh-ba" class="btn btn-primary">Danh bạ hành chính</NuxtLink>
        <NuxtLink to="/" class="btn btn-ghost">Về trang chủ</NuxtLink>
      </template>
    </EmptyState>
  </section>

  <section v-else class="wp">
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <button type="button" class="bc-back" aria-label="Quay lại" @click="goBack">
        <span aria-hidden="true">←</span>
      </button>
      <ol>
        <li><NuxtLink to="/">Trang chủ</NuxtLink></li>
        <li v-if="data.place.area"><NuxtLink :to="`/khu-vuc/${data.place.area}`">{{ areaMeta.name }}</NuxtLink></li>
        <li aria-current="page">{{ data.place.name }}</li>
      </ol>
    </nav>

    <!-- Hero -->
    <header class="wp-hero" :class="`area-${data.place.area}`">
      <div class="wp-hero-motif" aria-hidden="true" v-html="heroMotif"></div>
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
        <EmptyState v-if="mapLoadError" tone="error" icon="🗺️" message="Không tải được bản đồ. Kiểm tra kết nối và thử lại." />
        <div v-show="!mapLoadError" ref="mapEl" class="wp-map-container" :class="{ 'wp-map-loading': !mapReady }" role="application" aria-roledescription="bản đồ tương tác" :aria-label="`Bản đồ ${data.place.name}. Dùng chuột hoặc cảm ứng để di chuyển.`"></div>
      </section>
    </ClientOnly>

    <!-- Main content -->
    <div class="wp-body">
      <div class="wp-main">
        <!-- Tham quan nổi bật -->
        <section v-if="data.tourism?.length" class="wp-sec">
          <p class="wp-eyebrow">📍 Tham quan</p>
          <h2><span class="sec-icon" aria-hidden="true">🗺️</span> Địa điểm tham quan <span class="cnt">({{ data.tourism.length }})</span></h2>
          <div class="wp-grid grid">
            <EntityCard v-for="e in data.tourism" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Lưu trú -->
        <section v-if="data.lodging?.length" class="wp-sec reveal">
          <div class="wp-divider" aria-hidden="true"></div>
          <p class="wp-eyebrow">🏨 Nghỉ ngơi</p>
          <h2><span class="sec-icon" aria-hidden="true">🏡</span> Lưu trú <span class="cnt">({{ data.lodging.length }})</span></h2>
          <div class="wp-grid grid">
            <EntityCard v-for="e in data.lodging" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Sản phẩm -->
        <section v-if="data.products?.length" class="wp-sec reveal">
          <div class="wp-divider" aria-hidden="true"></div>
          <p class="wp-eyebrow">🛍️ Đặc sản</p>
          <h2><span class="sec-icon" aria-hidden="true">🍊</span> Đặc sản &amp; sản phẩm <span class="cnt">({{ data.products.length }})</span></h2>
          <div class="wp-grid grid">
            <EntityCard v-for="e in data.products" :key="e.id" :entity="e" />
          </div>
        </section>

        <!-- Empty state -->
        <div v-if="!totalContent" class="wp-empty-card">
          <div class="wp-empty-motif" aria-hidden="true"></div>
          <span class="wp-empty-icon" aria-hidden="true">🗺️</span>
          <p class="wp-empty-title">Trang đang được xây dựng</p>
          <p class="wp-empty-msg">Chưa có dữ liệu địa điểm cho {{ data.place.name }}. Du lịch, lưu trú và đặc sản của khu vực này đang được bổ sung.</p>
          <p class="wp-empty-hint">Quay lại sau hoặc khám phá các xã/phường lân cận qua trang khu vực.</p>
        </div>
      </div>

      <!-- Sidebar -->
      <aside class="wp-aside">
        <!-- Liên hệ cơ quan -->
        <div class="wp-card">
          <h3>📞 Liên hệ khẩn cấp</h3>
          <div class="wp-contact">
            <div class="wp-contact-item wp-contact-main">
              <span class="wp-contact-label">👮 Công an {{ data.place.name }}</span>
              <a v-if="attrs.police_phone" :href="telHref(attrs.police_phone)" class="wp-phone" :aria-label="`Gọi công an ${data.place.name}`">{{ attrs.police_phone }}</a>
              <span v-else class="wp-phone-na">Đang cập nhật</span>
            </div>
          </div>
        </div>

        <!-- Danh bạ hành chính -->
        <div v-if="data.facilities?.length" class="wp-card">
          <h3>🏛️ Danh bạ hành chính</h3>
          <ul class="wp-fac-list">
            <li v-for="f in data.facilities" :key="f.id" class="wp-fac">
              <span class="wp-fac-kind"><span class="wp-fac-emoji" aria-hidden="true">{{ kindMeta(f).emoji }}</span> {{ kindMeta(f).label }}</span>
              <strong>{{ f.name }}</strong>
              <div v-if="attr(f,'address')" class="wp-fac-row">📍 {{ attr(f,'address') }}</div>
              <div v-if="attr(f,'phone')" class="wp-fac-row">📞 <a :href="telHref(attr(f,'phone'))" :aria-label="`Gọi ${f.name}`">{{ attr(f,'phone') }}</a></div>
            </li>
          </ul>
        </div>

        <!-- Map link -->
        <NuxtLink v-if="data.place.coordinates" :to="mapUrl" class="wp-map-btn">
          🗺️ Xem trên bản đồ
        </NuxtLink>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META, OFFICE_KIND, TYPE_META } from '~/composables/useConstants'

useReveal()

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

function goBack() {
  if (import.meta.client && window.history.length > 1) {
    router.back()
  } else {
    navigateTo('/danh-ba')
  }
}

const fetchFailed = ref(false)
const { data } = await useAsyncData(() => `ward-${id.value}`, async () => {
  try {
    fetchFailed.value = false
    return await apiFetch<Record<string, unknown>>(`/api/places/${id.value}/overview`)
  } catch {
    fetchFailed.value = true
    return null
  }
})
if (import.meta.server && !data.value?.place && !fetchFailed.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy xã/phường' })
}

const areaMeta = computed(() => AREA_META[data.value?.place?.area] || { name: '', emoji: '📍', blurb: '' })

// Region-keyed decorative hero motif (inline SVG, no external/copyrighted assets)
const MOTIFS: Record<string, string> = {
  'vinh-long': '<svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"><path d="M0 60 Q25 45 50 60 T100 60 T150 60 T200 60" fill="none" stroke="#fff" stroke-width="2"/><path d="M0 75 Q25 60 50 75 T100 75 T150 75 T200 75" fill="none" stroke="#fff" stroke-width="2"/><path d="M0 45 Q25 30 50 45 T100 45 T150 45 T200 45" fill="none" stroke="#fff" stroke-width="2"/></svg>',
  'ben-tre': '<svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M150 95 V40"/><path d="M150 42 Q120 30 95 36"/><path d="M150 42 Q180 30 200 38"/><path d="M150 45 Q125 48 105 62"/><path d="M150 45 Q178 50 195 64"/><path d="M150 40 Q150 22 152 8"/></g></svg>',
  'tra-vinh': '<svg viewBox="0 0 200 100" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="#fff" stroke-width="2"><ellipse cx="100" cy="60" rx="10" ry="26"/><ellipse cx="100" cy="60" rx="10" ry="26" transform="rotate(40 100 60)"/><ellipse cx="100" cy="60" rx="10" ry="26" transform="rotate(-40 100 60)"/><ellipse cx="100" cy="60" rx="10" ry="26" transform="rotate(75 100 60)"/><ellipse cx="100" cy="60" rx="10" ry="26" transform="rotate(-75 100 60)"/></g></svg>',
}
const heroMotif = computed(() => MOTIFS[data.value?.place?.area as string] || MOTIFS['vinh-long'])
const attrs = computed(() => data.value?.place?.attributes || {})
const hasStats = computed(() => !!(attrs.value.area_km2 || attrs.value.population))
const totalContent = computed(() => {
  const c = data.value?.counts || {}
  return (c.tourism || 0) + (c.lodging || 0) + (c.products || 0)
})

const mapUrl = computed(() => {
  const c = normalizeCoords(data.value?.place?.coordinates)
  if (!c) return '/ban-do'
  return `/ban-do?lat=${c[0]}&lng=${c[1]}&zoom=15`
})

function formatPop(n: number) {
  return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : String(n)
}

function attr(f: Entity, k: string) { return (f.attributes || {})[k] }
function kindMeta(f: Entity) { return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac }

const allWardEntities = computed<Entity[]>(() => {
  const d = data.value
  if (!d) return []
  return [...(d.tourism || []), ...(d.lodging || []), ...(d.products || [])]
})

const placeName = computed(() => data.value?.place?.name || 'Xã/Phường')
useSeoMeta({
  ogType: 'article',
  title: () => `${placeName.value} — du lịch, lưu trú, đặc sản & danh bạ | vinhlong360`,
  description: () => data.value?.place?.summary || `Tổng hợp địa điểm du lịch, cơ sở lưu trú, sản phẩm đặc sản và danh bạ hành chính của ${placeName.value}.`,
  ogTitle: () => `${placeName.value} — vinhlong360`,
  ogDescription: () => data.value?.place?.summary || `Du lịch, đặc sản & danh bạ ${placeName.value}.`,
  ogImage: () => entityOgImage(allWardEntities.value.find(e => e.images?.length)?.images),
})
useHead(() => {
  const place = data.value?.place
  if (!place) return { link: [{ rel: 'canonical', href: canonicalUrl(`/xa-phuong/${id.value}`) }] }

  const adminLd: Record<string, any> = {
    '@context': 'https://schema.org', '@type': 'AdministrativeArea',
    name: place.name,
    ...(place.summary ? { description: place.summary } : {}),
    address: { '@type': 'PostalAddress', addressRegion: areaMeta.value.name, addressCountry: 'VN' },
  }
  const geoCoords = normalizeCoords(place.coordinates)
  if (geoCoords) {
    adminLd.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
  }

  const breadcrumbLd = {
    '@context': 'https://schema.org', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
      ...(place.area ? [{ '@type': 'ListItem', position: 2, name: areaMeta.value.name, item: `https://vinhlong360.vn/khu-vuc/${place.area}` }] : []),
      { '@type': 'ListItem', position: place.area ? 3 : 2, name: place.name, item: `https://vinhlong360.vn/xa-phuong/${id.value}` },
    ],
  }

  const scripts = [
    { type: 'application/ld+json', innerHTML: safeJsonLd(adminLd) },
    { type: 'application/ld+json', innerHTML: safeJsonLd(breadcrumbLd) },
  ]

  const allEnts = allWardEntities.value
  if (allEnts.length) {
    scripts.push({
      type: 'application/ld+json',
      innerHTML: safeJsonLd({
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        name: `Địa điểm tại ${place.name}`,
        numberOfItems: allEnts.length,
        itemListElement: allEnts.slice(0, 30).map((e: any, i: number) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: e.name,
          url: `https://vinhlong360.vn/dia-diem/${e.id}`,
        })),
      }),
    })
  }

  return {
    link: [{ rel: 'canonical', href: canonicalUrl(`/xa-phuong/${id.value}`) }],
    script: scripts,
  }
})

// Map
const mapEl = ref<HTMLElement | null>(null)
const { createMap } = useNDAMap()


const mapLoadError = ref(false)
const mapReady = ref(false)
let mapInstance: any = null
let mapLoadTimer: ReturnType<typeof setTimeout> | undefined
watch(mapEl, async (el) => {
  const center = normalizeCoords(data.value?.place?.coordinates)
  if (!el || !center) return
  const coords = center
  let map: any, maplibregl: any
  try {
    const r = await createMap(el, { center: [coords[1], coords[0]], zoom: 14 })
    map = r.map
    maplibregl = r.maplibregl
    mapInstance = map
  } catch {
    mapLoadError.value = true
    return
  }
  mapLoadTimer = setTimeout(() => { if (!map.isStyleLoaded()) mapLoadError.value = true }, 15000)
  map.on('load', () => { clearTimeout(mapLoadTimer); mapLoadError.value = false; mapReady.value = true })

  map.addControl(new maplibregl.FullscreenControl(), 'top-right')

  // Ward center marker — popup mở mặc định
  const centerPopup = new maplibregl.Popup({ offset: 25, closeOnClick: false })
    .setHTML(`<strong>${escapeHtml(data.value?.place?.name || '')}</strong>`)
  new maplibregl.Marker({ color: '#9C3D22', scale: 1.1 })
    .setLngLat([coords[1], coords[0]])
    .setPopup(centerPopup)
    .addTo(map)
    .togglePopup()

  // Entity markers
  const bounds = new maplibregl.LngLatBounds()
  bounds.extend([coords[1], coords[0]])
  const entities = allWardEntities.value

  for (const ent of entities) {
    const c = normalizeCoords(ent.coordinates)
    if (!c) continue
    const meta = TYPE_META[ent.type] || { emoji: '📍', label: '' }
    const el = document.createElement('div')
    el.className = 'wp-marker'
    el.textContent = meta.emoji
    el.title = ent.name
    new maplibregl.Marker({ element: el })
      .setLngLat([c[1], c[0]])
      .setPopup(new maplibregl.Popup({ offset: 20, maxWidth: '220px' }).setHTML(
        `<a href="/dia-diem/${encodeURIComponent(ent.id)}" class="map-popup-link">${escapeHtml(ent.name)}</a><br><small>${escapeHtml(meta.label)}</small>`
      ))
      .addTo(map)
    bounds.extend([c[1], c[0]])
  }

  if (entities.length && !bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 60, maxZoom: 16 })
  }
}, { once: true })

onUnmounted(() => {
  if (mapLoadTimer) clearTimeout(mapLoadTimer)
  if (mapInstance) { mapInstance.remove(); mapInstance = null }
})
</script>

<!-- detail.css nạp theo route (bỏ khỏi global entry.css; phần dùng-chung ở detail-shared.css) -->
<style src="~/assets/css/detail.css"></style>

<style scoped>
.wp { max-width: var(--maxw, 1100px); margin: 0 auto; padding: 0 var(--space-4) var(--space-16); }

/* Hero */
.wp-hero { border-radius: var(--radius-lg, 16px); padding: var(--space-8) var(--space-6); margin-top: var(--space-2); color: var(--text-on-dark, #fff); position: relative; overflow: hidden; }
.wp-hero.area-vinh-long { background: linear-gradient(135deg, #9C3D22 0%, #c0542e 50%, #d4764a 100%); }
.wp-hero.area-ben-tre { background: linear-gradient(135deg, #1b7a3d 0%, #27944e 50%, #4bae6a 100%); }
.wp-hero.area-tra-vinh { background: linear-gradient(135deg, #6b3fa0 0%, #8354b8 50%, #a070d0 100%); }
/* Dark mode: darken bottom stop for 4.5:1 AA on white text */
.dark .wp-hero.area-vinh-long { background: linear-gradient(135deg, #5e2212 0%, #7a3119 50%, #7a2d1d 100%); }
.dark .wp-hero.area-ben-tre { background: linear-gradient(135deg, #0b4520 0%, #135a2c 50%, #0d4921 100%); }
.dark .wp-hero.area-tra-vinh { background: linear-gradient(135deg, #3a2070 0%, #4f3088 50%, #4a2763 100%); }

/* Cinematic scrim: lift text legibility + add owned-by-region radial glow */
.wp-hero::before {
  content: ''; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(circle at 12% 0%, rgba(255,255,255,.16), transparent 55%),
    linear-gradient(to bottom, transparent 0%, rgba(0,0,0,.12) 100%);
}
.dark .wp-hero::before {
  background:
    radial-gradient(circle at 12% 0%, rgba(255,255,255,.10), transparent 55%),
    linear-gradient(to bottom, transparent 0%, rgba(0,0,0,.28) 100%);
}
/* Region-keyed decorative motif */
.wp-hero-motif {
  position: absolute; inset: 0; z-index: 0; opacity: .12; pointer-events: none;
  overflow: hidden; mix-blend-mode: soft-light;
}
.wp-hero-motif :deep(svg) { width: 100%; height: 100%; display: block; }
.dark .wp-hero-motif { opacity: .08; }
.wp-hero-inner { position: relative; z-index: 1; }
.wp-level { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .06em; opacity: .85; font-weight: var(--weight-bold); }
.wp-hero h1 { margin: var(--space-1) 0 var(--space-1); font-size: clamp(1.5rem, 4vw, 1.8rem); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); }
.wp-region { margin: 0; opacity: .9; font-size: var(--text-sm); }
.wp-region a { color: var(--text-on-dark, #fff); text-decoration: underline; text-underline-offset: 3px; border-radius: var(--radius-sm); }
.wp-region a:focus-visible { outline: 2px solid var(--text-on-dark, #fff); outline-offset: 2px; }
.wp-region-emoji { margin-inline-end: var(--space-1); }

.wp-stats { display: flex; flex-wrap: wrap; gap: var(--space-6); margin-top: var(--space-5); padding-top: var(--space-4); border-top: .5px solid rgba(255,255,255,.25); }
.dark .wp-stats { border-top-color: rgba(255,255,255,.12); }
.wp-stat { text-align: center; min-height: 44px; }
.wp-stat-val { display: block; font-size: var(--text-xl); font-weight: var(--weight-extrabold); }
.wp-stat-label { font-size: var(--text-xs); opacity: .8; text-transform: uppercase; letter-spacing: .03em; }

/* Summary */
.wp-summary { max-width: 72ch; font-size: var(--text-base); line-height: var(--leading-relaxed); color: var(--ink); margin: var(--space-5) 0 var(--space-1); display: -webkit-box; -webkit-line-clamp: 4; line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }

/* Map */
.wp-map-sec { margin: var(--space-5) 0 var(--space-2); }
.wp-map-container { width: 100%; height: 380px; border-radius: var(--radius-lg, 16px); overflow: hidden; border: .5px solid var(--line); box-shadow: var(--shadow-sm); transition: box-shadow .35s var(--ease-out-expo); }
.wp-map-loading { background: linear-gradient(100deg, var(--bg-warm) 30%, var(--line) 50%, var(--bg-warm) 70%); background-size: 200% 100%; animation: wp-shimmer 1.4s var(--ease-out) infinite; }
@keyframes wp-shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
:deep(.wp-marker) { font-size: 1.6rem; cursor: pointer; filter: drop-shadow(0 1px 3px rgba(0,0,0,.4)); line-height: 1; transition: transform .35s var(--ease-spring-gentle); }
:deep(.wp-marker:hover) { transform: scale(1.25); }

/* Body layout */
.wp-body { display: grid; grid-template-columns: 1fr 320px; gap: var(--space-6); margin-top: var(--space-5); align-items: start; }

/* Sections */
.wp-sec { margin-bottom: var(--space-6); }
.wp-divider { height: 0; border-top: .5px dashed var(--line); margin: var(--space-8) 0 var(--space-6); }
.wp-eyebrow { font-size: var(--text-xs); font-weight: var(--weight-semibold); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--primary-fg); margin: 0 0 var(--space-1); }
.wp-sec h2 { font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); margin: 0 0 var(--space-4); display: flex; align-items: center; gap: var(--space-2); }
.sec-icon { font-size: var(--text-lg); }
.cnt { color: rgba(var(--primary-rgb), .6); font-weight: var(--weight-medium); font-size: var(--text-sm); }
.dark .cnt { color: rgba(var(--primary-rgb), .85); }
.wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: var(--space-4); }

/* Designed empty-state card */
.wp-empty-card {
  position: relative; overflow: hidden; text-align: center;
  background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-lg, 16px); padding: var(--space-10) var(--space-6) var(--space-8);
  margin-top: var(--space-2);
  background-image: radial-gradient(circle at 50% 0%, rgba(var(--primary-rgb), .06), transparent 60%);
}
.wp-empty-motif {
  position: absolute; inset: auto 0 0 0; height: 60px; pointer-events: none; opacity: .06;
  background:
    radial-gradient(circle at 20% 100%, var(--primary) 0 2px, transparent 3px),
    radial-gradient(circle at 50% 100%, var(--primary) 0 2px, transparent 3px),
    radial-gradient(circle at 80% 100%, var(--primary) 0 2px, transparent 3px);
}
.wp-empty-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 72px; height: 72px; font-size: 2.2rem; border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--primary-rgb), .12), rgba(var(--primary-rgb), .04) 70%, transparent);
  margin-bottom: var(--space-3); position: relative; z-index: 1;
}
.wp-empty-title { font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); margin: 0 0 var(--space-2); position: relative; z-index: 1; }
.wp-empty-msg { color: var(--ink-secondary, var(--muted)); font-size: var(--text-sm); line-height: var(--leading-relaxed); max-width: 46ch; margin: 0 auto var(--space-2); position: relative; z-index: 1; }
.wp-empty-hint { color: var(--muted); font-size: var(--text-xs); max-width: 44ch; margin: 0 auto; position: relative; z-index: 1; }

/* Sidebar cards */
.wp-aside { display: flex; flex-direction: column; gap: var(--space-4); position: sticky; top: 78px; }
.wp-card { position: relative; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg, 16px); padding: var(--space-5); box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.wp-card::before {
  content: ''; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,.6) 0%, transparent 55%);
  mix-blend-mode: overlay; opacity: 0; transition: opacity .35s var(--ease-out-expo);
}
.wp-card:hover { transform: translateY(-2px); box-shadow: 0 0 0 1px rgba(var(--primary-rgb), .14), 0 18px 40px -18px rgba(var(--primary-rgb), .35); }
.wp-card:hover::before { opacity: .9; }
.dark .wp-card::before { background: linear-gradient(180deg, rgba(255,255,255,.08) 0%, transparent 55%); }
.dark .wp-card:hover::before { opacity: .5; }
.wp-card h3 { font-size: var(--text-base); font-weight: var(--weight-semibold); margin: 0 0 var(--space-3); position: relative; z-index: 1; }
.wp-card .wp-contact, .wp-card .wp-fac-list { position: relative; z-index: 1; }

/* Contact list */
.wp-contact { display: flex; flex-direction: column; gap: var(--space-3); }
.wp-contact-item { display: flex; flex-direction: column; gap: 2px; padding: var(--space-2) 0; border-bottom: .5px solid var(--line); }
.wp-contact-item:last-child { border-bottom: none; padding-bottom: 0; }
.wp-contact-main { background: linear-gradient(90deg, rgba(var(--primary-rgb), .07) 0%, rgba(var(--accent-rgb), .07) 100%); border-radius: var(--radius-md); padding: var(--space-3); border-bottom: none; margin-bottom: 2px; }
.wp-contact-label { font-size: var(--text-xs); color: var(--muted); }
.wp-phone { font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--primary-fg); min-height: 44px; padding: var(--space-2) var(--space-3); margin-inline-start: calc(var(--space-3) * -1); display: inline-flex; align-items: center; border-radius: var(--radius-sm); }
.wp-phone:hover { text-decoration: underline; }
.wp-phone:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.wp-phone-na { font-size: var(--text-sm); color: var(--muted); font-style: italic; }

/* Facilities */
.wp-fac-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-3); }
.wp-fac { padding: var(--space-2) var(--space-2); border-bottom: .5px solid var(--line); transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle); border-radius: var(--radius-sm); margin: 0 calc(var(--space-2) * -1); }
.wp-fac:hover { background: rgba(var(--primary-rgb), .04); transform: translateX(2px); }
.wp-fac:last-child { border-bottom: none; }
.wp-fac-kind { font-size: var(--text-xs); color: var(--primary-fg); display: inline-flex; align-items: center; gap: var(--space-1); margin-bottom: 2px; }
.wp-fac-emoji { font-size: 1.1rem; line-height: 1; flex-shrink: 0; }
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
  .wp-body { grid-template-columns: 1fr; gap: var(--space-4); }
  .wp-aside { position: static; margin-top: var(--space-6); }
  .wp-stats { gap: var(--space-4); }
}
@media (max-width: 480px) {
  .wp-hero { padding: var(--space-6) var(--space-5); border-radius: var(--radius-md); }
  .wp-hero h1 { font-size: 1.4rem; }
  .wp-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); justify-items: center; }
  .wp-stat-val { font-size: 1.1rem; }
  .wp-map-container { height: 260px; border-radius: var(--radius-sm); }
  .wp-empty-card { padding: var(--space-8) var(--space-5) var(--space-6); }
}

/* Dark mode */
.dark .wp-card { background: var(--card); border-color: var(--line); }
.dark .wp-card:hover { box-shadow: 0 0 0 1px rgba(var(--primary-rgb), .22), 0 18px 40px -18px rgba(0,0,0,.6); }
.dark .wp-contact-main { background: linear-gradient(90deg, rgba(var(--primary-rgb), .12) 0%, rgba(var(--accent-rgb), .10) 100%); }
.dark .wp-phone { color: var(--primary-fg); }
.dark .wp-fac:hover { background: var(--glass-subtle); }
.dark .wp-fac-kind { color: var(--primary-fg); }
.dark .wp-fac-row a { color: var(--primary-fg); }
.dark .wp-map-btn { background: var(--glass-subtle); border-color: var(--line); color: var(--ink); }
.dark .wp-map-btn:hover { background: var(--glass-light); }
.dark .wp-empty-card { background-image: radial-gradient(circle at 50% 0%, rgba(var(--primary-rgb), .10), transparent 60%); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .wp-card:hover { transform: none; }
  .wp-card::before { transition: none; }
  .wp-map-btn:hover { transform: none; }
  .wp-map-btn:active { transform: none; }
  .wp-fac:hover { transform: none; }
  .wp-map-loading { animation: none; }
  :deep(.wp-marker:hover) { transform: none; }
}
</style>
