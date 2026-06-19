<template>
  <div class="home">
    <!-- 1. Hero — dynamic tagline + search + quick-pick pills -->
    <section class="hero">
      <HeroIllustration />
      <div class="hero-inner">
        <h1>{{ seasonalTagline }}</h1>
        <p class="hero-sub">Trải nghiệm miệt vườn, đặc sản theo mùa, lễ hội truyền thống — tất cả trong một bản đồ.</p>
        <form class="hero-search" role="search" aria-label="Tìm kiếm trang chủ" @submit.prevent="onHeroSearch">
          <div class="hero-search-field">
            <svg class="hero-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="heroQ" type="search" placeholder="Tìm: chôm chôm, kẹo dừa, cù lao An Bình…" aria-label="Tìm kiếm điểm đến, đặc sản" />
          </div>
          <button type="submit">Tìm</button>
        </form>
        <div class="hero-pills">
          <NuxtLink to="/lich-trinh" class="hero-pill">🗓️ Cuối tuần 2N1Đ</NuxtLink>
          <NuxtLink to="/kham-pha/am-thuc" class="hero-pill">🍲 Ẩm thực</NuxtLink>
          <NuxtLink to="/ocop" class="hero-pill">🎁 Quà OCOP</NuxtLink>
          <NuxtLink to="/du-lich" class="hero-pill">🌿 Miệt vườn</NuxtLink>
          <NuxtLink to="/le-hoi" class="hero-pill">🎭 Lễ hội</NuxtLink>
          <NuxtLink to="/ban-do" class="hero-pill" no-prefetch>🗺️ Bản đồ</NuxtLink>
        </div>
      </div>
    </section>

    <!-- Region selector — first visit prompt -->
    <ClientOnly>
      <section v-if="!hasChosen" class="region-picker reveal">
        <p class="rp-question">Bạn muốn khám phá vùng nào?</p>
        <div class="rp-options">
          <button type="button" v-for="slug in Object.keys(AREA_META)" :key="slug" class="rp-btn" :class="`rp-${slug}`" @click="setRegion(slug as any)">
            <span class="rp-emoji">{{ AREA_META[slug].emoji }}</span>
            <span class="rp-name">{{ AREA_META[slug].name }}</span>
          </button>
          <button type="button" class="rp-btn rp-all" @click="setRegion('all')">
            <span class="rp-emoji">🌏</span>
            <span class="rp-name">Cả 3 vùng</span>
          </button>
        </div>
      </section>
      <div v-else-if="isReturning && region !== 'all'" class="welcome-back reveal">
        <span class="wb-text">Chào mừng trở lại! Đang ưu tiên <strong>{{ AREA_META[region!]?.name || 'khu vực' }}</strong> cho bạn.</span>
        <button type="button" class="wb-change" @click="setRegion('all')">Xem tất cả</button>
      </div>
    </ClientOnly>

    <!-- Stats bar — trust signal -->
    <section v-if="stats" class="stats-bar reveal">
      <div class="stat-item" v-for="s in statsItems" :key="s.label">
        <span class="stat-num">{{ s.value }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </section>

    <!-- 2. "Đang diễn ra" — upcoming events + seasonal merged -->
    <section v-if="upcomingEvents.length || seasonal.length" class="block reveal">
      <div class="section-head">
        <h2>Đang diễn ra</h2>
        <NuxtLink class="see-all" to="/su-kien">Xem lịch →</NuxtLink>
      </div>

      <!-- Upcoming events -->
      <div v-if="upcomingEvents.length" class="happening-scroll" role="region" aria-label="Sự kiện sắp diễn ra">
        <NuxtLink
          v-for="ev in upcomingEvents"
          :key="ev.id"
          :to="`/dia-diem/${ev.id}`"
          class="event-card"
        >
          <div class="ec-date">
            <span class="ec-day">{{ formatEventDay(ev) }}</span>
            <span class="ec-month">{{ formatEventMonth(ev) }}</span>
          </div>
          <div class="ec-info">
            <span class="ec-cat">{{ ev.attributes?.category === 'le-hoi' ? '🎭 Lễ hội' : '📅 Sự kiện' }}</span>
            <h3>{{ ev.name }}</h3>
            <span v-if="ev.attributes?.lunar_date" class="ec-lunar">🌙 {{ ev.attributes.lunar_date }}</span>
            <span v-if="ev.days_until != null" class="ec-countdown" :class="{ 'ec-today': ev.days_until === 0 }">
              <span v-if="ev.days_until === 0" class="ec-live-dot" aria-hidden="true"></span>
              {{ ev.days_until === 0 ? 'Hôm nay!' : ev.days_until === 1 ? 'Ngày mai' : `Còn ${ev.days_until} ngày` }}
            </span>
          </div>
        </NuxtLink>
      </div>

      <!-- Seasonal products/experiences -->
      <div v-if="seasonal.length" class="happening-section">
        <p class="happening-label">🔥 Đang vào mùa tháng {{ currentMonth }}</p>
        <div class="scroll-row" role="region" aria-label="Đặc sản theo mùa">
          <EntityCard v-for="e in seasonal" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
        </div>
      </div>
    </section>

    <!-- 3. Lịch trình gợi ý (đẩy lên sớm — 25% user là Planner) -->
    <section v-if="itineraries.length" class="block reveal">
      <div class="section-head">
        <h2>Lịch trình gợi ý</h2>
        <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Lịch trình gợi ý">
        <ItineraryCard v-for="it in itineraries" :key="it.id" :itinerary="it" />
      </div>
      <div class="block-cta">
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">📋 Tạo lịch trình riêng</NuxtLink>
      </div>
    </section>

    <!-- 4. 3 Vùng -->
    <section class="block reveal">
      <div class="section-head">
        <h2>Khám phá 3 vùng</h2>
        <NuxtLink class="see-all" to="/ban-do" no-prefetch>Xem bản đồ →</NuxtLink>
      </div>
      <div class="regions">
        <NuxtLink
          v-for="slug in areaKeys"
          :key="slug"
          :to="`/khu-vuc/${slug}`"
          class="region-tile"
          :class="[`region-${slug}`, { 'region-active': region === slug }]"
          :style="{ backgroundImage: `url(/img/cat/${REGION_IMG[slug] || 'place'}.jpg)` }"
        >
          <div class="region-tile-in">
            <span class="region-emoji">{{ AREA_META[slug].emoji }}</span>
            <h3>{{ AREA_META[slug].name }}</h3>
            <p>{{ AREA_META[slug].blurb }}</p>
            <div class="region-footer">
              <span class="region-count">{{ areaCounts[slug] || 0 }} điểm</span>
              <span class="region-cta">Khám phá →</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- 5. Trải nghiệm nổi bật -->
    <section v-if="topExperiences.length" class="block reveal">
      <div class="section-head">
        <h2>Trải nghiệm nổi bật</h2>
        <NuxtLink class="see-all" to="/du-lich">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Trải nghiệm nổi bật">
        <EntityCard v-for="e in topExperiences" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- 6. Đặc sản & Quà OCOP — always visible -->
    <section v-if="products.length" class="block reveal">
      <div class="section-head">
        <h2>Đặc sản &amp; Quà OCOP</h2>
        <NuxtLink class="see-all" to="/san-pham">Xem tất cả →</NuxtLink>
      </div>
      <div class="scroll-row" role="region" aria-label="Đặc sản và quà OCOP">
        <EntityCard v-for="e in products" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- 7. Cá nhân hóa — client-only (saved + AI recommendations) -->
    <ClientOnly>
      <section v-if="recentSaved.length" class="block">
        <div class="section-head">
          <h2>Đã lưu gần đây</h2>
          <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
        </div>
        <div class="scroll-row" role="region" aria-label="Đã lưu gần đây">
          <NuxtLink v-for="fav in recentSaved" :key="fav.id" :to="`/dia-diem/${fav.id}`" class="card">
            <div v-if="fav.image" class="cover cover-img">
              <img :src="fav.image" :alt="fav.name" loading="lazy" decoding="async" width="480" height="192" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getFavTypeMeta(fav.type).label }}</span>
              <h3>{{ fav.name }}</h3>
              <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
            </div>
          </NuxtLink>
        </div>
        <div class="block-cta">
          <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">Tạo lịch trình từ danh sách đã lưu</NuxtLink>
        </div>
      </section>
      <NuxtErrorBoundary>
        <AIRecommendations title="Có thể bạn quan tâm" :limit="4" />
      </NuxtErrorBoundary>
    </ClientOnly>

    <!-- Region mini-switcher — sticky, visible after first choice -->
    <ClientOnly>
      <div v-if="hasChosen" class="region-mini-bar">
        <button type="button"
          v-for="slug in Object.keys(AREA_META)"
          :key="slug"
          class="rmb-btn"
          :class="{ active: region === slug }"
          @click="setRegion(slug as any)"
        >{{ AREA_META[slug].emoji }} {{ AREA_META[slug].name }}</button>
        <button type="button" class="rmb-btn" :class="{ active: region === 'all' }" @click="setRegion('all')">🌏 Tất cả</button>
      </div>
    </ClientOnly>

    <!-- 8. Quick links + Chatbot CTA -->
    <section class="block block-compact reveal">
      <div class="section-head">
        <h2>Khám phá thêm</h2>
      </div>
      <div class="quick-grid">
        <NuxtLink to="/kham-pha/am-thuc" class="quick-link"><span class="ql-icon">🍲</span><span class="ql-text">Ẩm thực</span></NuxtLink>
        <NuxtLink to="/kham-pha/thien-nhien" class="quick-link"><span class="ql-icon">🌿</span><span class="ql-text">Thiên nhiên</span></NuxtLink>
        <NuxtLink to="/kham-pha/van-hoa" class="quick-link"><span class="ql-icon">🛕</span><span class="ql-text">Văn hóa</span></NuxtLink>
        <NuxtLink to="/kham-pha/lang-nghe" class="quick-link"><span class="ql-icon">🏺</span><span class="ql-text">Làng nghề</span></NuxtLink>
        <NuxtLink to="/kham-pha/mua-sam" class="quick-link"><span class="ql-icon">🛍️</span><span class="ql-text">Mua sắm</span></NuxtLink>
        <NuxtLink to="/tuyen-duong?vung=vinh-long" class="quick-link"><span class="ql-icon">🍊</span><span class="ql-text">Vòng trái cây VL</span></NuxtLink>
        <NuxtLink to="/tuyen-duong?vung=ben-tre" class="quick-link"><span class="ql-icon">🥥</span><span class="ql-text">Vòng dừa BT</span></NuxtLink>
        <NuxtLink to="/tuyen-duong?vung=tra-vinh" class="quick-link"><span class="ql-icon">🛕</span><span class="ql-text">Chùa Khmer TV</span></NuxtLink>
      </div>

      <!-- Chatbot CTA -->
      <div class="chatbot-cta">
        <div class="chatbot-cta-inner">
          <p class="chatbot-cta-text">Chưa biết đi đâu?</p>
          <p class="chatbot-cta-sub">Trợ lý AI sẵn sàng gợi ý lịch trình, món ăn, điểm đến phù hợp với bạn.</p>
        </div>
        <button type="button" class="chatbot-cta-btn" @click="openChat">💬 Hỏi ngay</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META } from '~/composables/useConstants'

useReveal()
const { region, isReturning, hasChosen, setRegion, sortByRegion, orderedAreaKeys } = useRegionPref()
const { favorites } = useFavorites()
const recentSaved = computed(() => favorites.value.slice(0, 4))
function getFavTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

const heroQ = ref('')

const { data: homeData } = await useAsyncData('homepage', () => $fetch<any>('/api/homepage'))

const currentMonth = computed(() => homeData.value?.month || (new Date().getMonth() + 1))
const seasonal = computed(() => homeData.value?.seasonal || [])
const experiences = computed(() => sortByRegion(homeData.value?.experiences || []))
const topExperiences = computed(() => experiences.value.slice(0, 6))
const products = computed(() => sortByRegion(homeData.value?.products || []))
const itineraries = computed(() => sortByRegion(homeData.value?.itineraries || []))
const upcomingEvents = computed(() => homeData.value?.upcoming_events || [])
const seasonalTagline = computed(() => homeData.value?.seasonal_tagline || 'Khám phá Vĩnh Long theo cách của người bản địa')

const areaKeys = computed(() => orderedAreaKeys(Object.keys(AREA_META)))
const REGION_IMG: Record<string, string> = { 'vinh-long': 'attraction', 'ben-tre': 'nature', 'tra-vinh': 'history' }

const areaCounts = computed(() => homeData.value?.area_counts || {})
const stats = computed(() => homeData.value?.stats || null)
const statsItems = computed(() => {
  const s = stats.value
  if (!s) return []
  const items = []
  if (s.entities) items.push({ value: s.entities + '+', label: 'Điểm đến & Đặc sản' })
  if (s.places) items.push({ value: s.places, label: 'Xã phường' })
  if (s.itineraries) items.push({ value: s.itineraries, label: 'Lịch trình' })
  const totalAreas = Object.values(areaCounts.value).reduce((a: number, b: any) => a + (Number(b) || 0), 0)
  if (totalAreas) items.push({ value: '3', label: 'Vùng đất' })
  return items
})

function formatEventDay(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return '?'
  return ds.split('-')[2]?.replace(/^0/, '') || '?'
}
function formatEventMonth(ev: any) {
  const ds = ev.attributes?.date_start
  if (!ds) return ''
  const m = parseInt(ds.split('-')[1], 10)
  return `Th${m}`
}

function onHeroSearch() {
  if (heroQ.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(heroQ.value.trim())}`)
  }
}

function openChat() {
  if (import.meta.client) {
    const fab = document.querySelector('.chat-fab') as HTMLElement
    if (fab) fab.click()
  }
}

useSeoMeta({
  title: 'vinhlong360 — Du lịch & Sản phẩm địa phương',
  description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.',
  ogTitle: 'vinhlong360 — Du lịch & Sản phẩm địa phương',
  ogDescription: 'Khám phá Vĩnh Long theo cách của người bản địa.',
  ogImage: 'https://vinhlong360.vn/img/og-default.jpg',
})
const itemListSchema = computed(() => {
  const items = topExperiences.value.map((e: any, i: number) => ({
    '@type': 'ListItem',
    position: i + 1,
    url: `https://vinhlong360.vn/dia-diem/${e.id}`,
    name: e.name,
  }))
  return items.length ? JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Trải nghiệm nổi bật tại Vĩnh Long',
    numberOfItems: items.length,
    itemListElement: items,
  }) : ''
})

const eventListSchema = computed(() => {
  const events = upcomingEvents.value.map((ev: any) => ({
    '@type': 'Event',
    name: ev.name,
    startDate: ev.attributes?.date_start,
    endDate: ev.attributes?.date_end || ev.attributes?.date_start,
    url: `https://vinhlong360.vn/dia-diem/${ev.id}`,
    eventStatus: 'https://schema.org/EventScheduled',
    eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
    location: { '@type': 'Place', name: ev.place_name || 'Vĩnh Long', address: { '@type': 'PostalAddress', addressRegion: ev.place_area || 'Vĩnh Long', addressCountry: 'VN' } },
  }))
  return events.length ? JSON.stringify(events) : ''
})

useHead({
  link: [
    { rel: 'canonical', href: canonicalUrl('/') },
    { rel: 'preload', as: 'image', href: '/img/hero-mobile.jpg', fetchpriority: 'high', media: '(max-width: 640px)' },
    { rel: 'preload', as: 'image', href: '/img/hero.jpg', fetchpriority: 'high', media: '(min-width: 641px)' },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'vinhlong360',
        url: 'https://vinhlong360.vn',
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long, Bến Tre, Trà Vinh.',
        inLanguage: 'vi-VN',
        potentialAction: {
          '@type': 'SearchAction',
          target: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}',
          'query-input': 'required name=search_term_string',
        },
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'vinhlong360',
        url: 'https://vinhlong360.vn',
        logo: 'https://vinhlong360.vn/icons/icon-512.png',
        description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long, Bến Tre, Trà Vinh.',
        inLanguage: 'vi-VN',
        areaServed: [
          { '@type': 'AdministrativeArea', name: 'Vĩnh Long' },
          { '@type': 'AdministrativeArea', name: 'Bến Tre' },
          { '@type': 'AdministrativeArea', name: 'Trà Vinh' },
        ],
        sameAs: [],
      }),
    },
    ...(itemListSchema.value ? [{ type: 'application/ld+json', innerHTML: itemListSchema.value }] : []),
    ...(eventListSchema.value ? [{ type: 'application/ld+json', innerHTML: eventListSchema.value }] : []),
  ],
})
</script>

<style>
/* ── Homepage-specific overrides (scoped by .home) ── */

/* Typography hierarchy: hero = Large Title tracking, sections = xl semibold */
.home .hero h1 { letter-spacing: -1.05px; }
.home .hero-sub { font-size: var(--text-lg); opacity: .92; max-width: 640px; margin: var(--space-4) 0 0; }

/* Section headings — Apple HIG: xl semibold (not 2xl extrabold) */
.home .section-head h2 {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  letter-spacing: -.01em;
  line-height: var(--leading-snug);
}

/* Breathing room between sections */
.home .block { padding-top: var(--space-16); padding-bottom: var(--space-4); }
.home .block-compact { padding-top: var(--space-8); padding-bottom: var(--space-12); }

/* ── Stats bar ── */
.stats-bar {
  display: flex;
  justify-content: center;
  gap: var(--space-8);
  padding: var(--space-5) var(--space-4);
  margin: calc(-1 * var(--space-4)) auto var(--space-4);
  max-width: var(--maxw);
}
.stats-bar .stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stats-bar .stat-num {
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
  color: var(--primary-fg);
  letter-spacing: var(--tracking-tight);
}
.stats-bar .stat-label {
  font-size: var(--text-xs);
  color: var(--muted);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: .03em;
}
@media (max-width: 480px) {
  .stats-bar { gap: var(--space-5); }
  .stats-bar .stat-num { font-size: var(--text-lg); }
  .stats-bar .stat-label { font-size: .65rem; }
}

/* ── Hero quick-pick pills ── */
.hero-pills {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-5);
  flex-wrap: wrap;
}
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: var(--overlay-light);
  backdrop-filter: saturate(180%) blur(12px);
  -webkit-backdrop-filter: saturate(180%) blur(12px);
  border: .5px solid rgba(255,255,255,.3);
  border-radius: var(--radius-full);
  color: var(--text-on-dark, #fff);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
  min-height: 44px;
}
.hero-pill:hover {
  background: rgba(255,255,255,.3);
  transform: translateY(-2px);
}
.hero-pill:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.hero-pill:focus-visible {
  outline: 2px solid var(--text-on-dark, #fff);
  outline-offset: 2px;
}

/* ── Horizontal scroll row (mobile → scroll, tablet → 2col, desktop → grid) ── */
.scroll-row {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
@media (min-width: 769px) and (max-width: 1024px) {
  .scroll-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .scroll-row {
    display: flex;
    gap: var(--space-3);
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--space-2);
    padding-inline: var(--space-4);
    margin-inline: calc(-1 * var(--space-4));
    scrollbar-width: none;
    mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
    -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 88%, transparent);
  }
  .scroll-row::-webkit-scrollbar { display: none; }
  .scroll-row:hover, .scroll-row:focus-within { mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); -webkit-mask-image: linear-gradient(to right, transparent, #000 var(--space-4), #000 100%); }
  .scroll-row > * {
    flex: 0 0 280px;
    scroll-snap-align: start;
  }
}

/* ── "Đang diễn ra" section ── */
.happening-scroll {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  padding-bottom: var(--space-2);
  scrollbar-width: none;
}
.happening-scroll::-webkit-scrollbar { display: none; }

.event-card {
  flex: 0 0 300px;
  scroll-snap-align: start;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo);
}
.event-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.event-card:active {
  transform: scale(.97);
  transition-duration: .1s;
}
.event-card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
.ec-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: var(--space-2);
  background: var(--primary);
  border-radius: var(--radius-sm);
  color: var(--text-on-dark, #fff);
}
.ec-day { font-size: var(--text-xl); font-weight: var(--weight-extrabold); line-height: 1; }
.ec-month { font-size: var(--text-xs); font-weight: var(--weight-semibold); opacity: .9; }
.ec-info { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.ec-cat { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .04em; color: var(--primary-fg); }
.ec-info h3 { margin: 0; font-size: var(--text-base); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ec-lunar { font-size: var(--text-xs); color: var(--muted); }
.ec-countdown {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--accent-dark);
}
.ec-today {
  color: var(--error);
}
.ec-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--error);
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .4; transform: scale(.7); }
}

.happening-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--primary-fg);
  margin: var(--space-4) 0 var(--space-2);
}
.happening-section { margin-top: var(--space-1); }

/* ── Block CTA ── */
.block-cta { text-align: center; margin-top: var(--space-4); }

/* ── Card grid choreography ── */
.home .grid .card,
.home .scroll-row .card {
  transition:
    transform .18s var(--ease-out),
    box-shadow .25s var(--ease-out);
}

/* ── Region tiles — enhanced ── */
.home .region-tile {
  transition:
    transform .18s var(--ease-out),
    box-shadow .25s var(--ease-out);
}
.region-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-2);
}
.region-count {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  opacity: .95;
}
.region-cta {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  opacity: .85;
  transition: opacity .3s;
}
.region-tile:hover .region-cta { opacity: 1; }
/* Per-region tint overlays */
.region-vinh-long .region-tile-in { background: linear-gradient(135deg, rgba(var(--primary-rgb),.82) 0%, rgba(var(--primary-rgb),.55) 100%); }
.region-ben-tre .region-tile-in { background: linear-gradient(135deg, rgba(var(--secondary-rgb),.82) 0%, rgba(var(--secondary-rgb),.55) 100%); }
.region-tra-vinh .region-tile-in { background: linear-gradient(135deg, rgba(var(--river-rgb),.82) 0%, rgba(var(--river-rgb),.55) 100%); }

/* ── Quick links — grid layout ── */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}
@media (max-width: 640px) {
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
}
.quick-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-3);
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  min-height: 44px;
  text-align: center;
  transition:
    transform .35s var(--ease-spring-gentle),
    box-shadow .35s var(--ease-out-expo),
    border-color .3s var(--ease-out);
}
.quick-link:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-fg);
  color: var(--primary-fg);
}
.quick-link:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.quick-link:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
.ql-icon { font-size: 1.6rem; line-height: 1; }
.ql-text { font-size: var(--text-xs); }

/* ── Chatbot CTA — enhanced ── */
.chatbot-cta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-6);
  padding: var(--space-5) var(--space-6);
  background: linear-gradient(135deg, var(--bg-alt) 0%, var(--bg-warm) 100%);
  border: .5px solid var(--line);
  border-radius: var(--radius);
}
.chatbot-cta-inner { flex: 1; }
.chatbot-cta-text {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
}
.chatbot-cta-sub {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--muted);
  line-height: var(--leading-relaxed);
}
.chatbot-cta-btn {
  padding: var(--space-3) var(--space-6);
  background: var(--primary);
  color: var(--text-on-dark, #fff);
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  min-height: 44px;
  white-space: nowrap;
  transition: background .3s var(--ease-out), transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
}
.chatbot-cta-btn:hover {
  background: var(--primary-dark, var(--primary));
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.chatbot-cta-btn:active {
  transform: scale(.95);
  transition-duration: .1s;
}
.chatbot-cta-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
@media (max-width: 480px) {
  .chatbot-cta { flex-direction: column; text-align: center; }
  .chatbot-cta-btn { width: 100%; }
}

/* ── Region picker (first visit) ── */
.region-picker {
  text-align: center;
  padding: var(--space-5) var(--space-4);
  margin: calc(-1 * var(--space-2)) auto var(--space-2);
  max-width: var(--maxw);
}
.rp-question {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  margin: 0 0 var(--space-3);
}
.rp-options {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
}
.rp-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  background: var(--card);
  border: 1.5px solid var(--line);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  cursor: pointer;
  min-height: 44px;
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), border-color .3s var(--ease-out), background .3s var(--ease-out);
}
.rp-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--primary-fg);
  color: var(--primary-fg);
}
.rp-btn:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.rp-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}
.rp-emoji { font-size: 1.2rem; }

/* ── Welcome back banner ── */
.welcome-back {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  max-width: var(--maxw);
  margin: calc(-1 * var(--space-2)) auto var(--space-2);
  font-size: var(--text-sm);
  color: var(--muted);
}
.wb-text strong { color: var(--primary-fg); font-weight: var(--weight-semibold); }
.wb-change {
  background: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
  transition: border-color .3s var(--ease-out), color .3s var(--ease-out);
}
.wb-change:hover { border-color: var(--primary-fg); color: var(--primary-fg); }
@media (max-width: 480px) {
  .welcome-back { flex-direction: column; text-align: center; }
}

/* ── Region active highlight ── */
.region-active {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
.region-active .region-tile-in {
  outline: 3px solid rgba(255,255,255,.4);
  outline-offset: -3px;
}

/* ── Region mini-switcher bar ── */
.region-mini-bar {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  max-width: var(--maxw);
  margin: 0 auto var(--space-4);
  flex-wrap: wrap;
}
.rmb-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  cursor: pointer;
  min-height: 32px;
  transition: background .3s var(--ease-out), border-color .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.rmb-btn:hover {
  border-color: var(--primary-fg);
  color: var(--primary-fg);
  transform: translateY(-1px);
}
.rmb-btn:active {
  transform: scale(.95);
  transition-duration: .08s;
}
.rmb-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--text-on-dark, #fff);
}

/* Dark mode: hero gradient */
.dark .home .hero {
  background-image:
    linear-gradient(105deg, rgba(26,26,26,.82) 0%, rgba(26,26,26,.48) 46%, rgba(26,26,26,.08) 100%),
    url('/img/hero.jpg');
}
@media (max-width: 640px) {
  .dark .home .hero {
    background-image:
      linear-gradient(105deg, rgba(26,26,26,.82) 0%, rgba(26,26,26,.48) 46%, rgba(26,26,26,.08) 100%),
      url('/img/hero-mobile.jpg');
  }
}

/* Dark mode */
.dark .event-card { background: var(--card); }
.dark .chatbot-cta { background: linear-gradient(135deg, var(--card) 0%, rgba(255,255,255,.03) 100%); }
.dark .hero-pill { background: var(--glass-medium); border-color: var(--border); }
.dark .quick-link { background: var(--card); }
.dark .stat-num { color: var(--primary-fg-strong); }
.dark .rp-btn { background: var(--bg-alt); border-color: var(--border); }
.dark .rp-btn:hover { background: var(--card); }
.dark .rmb-btn { background: var(--card); border-color: var(--border); }
.dark .rmb-btn.active { background: var(--primary); border-color: var(--primary); }
.dark .wb-change { border-color: var(--border); }

/* Reduce transparency */
@media (prefers-reduced-transparency: reduce) {
  .quick-link { backdrop-filter: none; }
  .hero-pill { backdrop-filter: none; background: rgba(255,255,255,.3); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .hero-pill:hover { transform: none; }
  .hero-pill:active { transform: none; }
  .event-card:hover { transform: none; }
  .event-card:active { transform: none; }
  .quick-link:hover { transform: none; }
  .quick-link:active { transform: none; }
  .chatbot-cta-btn:hover { transform: none; }
  .chatbot-cta-btn:active { transform: none; }
  .home .region-tile:hover { transform: none; }
  .home .region-tile:active { transform: none; }
  .ec-live-dot { animation: none; }
  .rp-btn:hover { transform: none; }
  .rp-btn:active { transform: none; }
  .rmb-btn:hover { transform: none; }
  .rmb-btn:active { transform: none; }
}
</style>
