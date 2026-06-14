<template>
  <div>
    <!-- Hero -->
    <section class="hero">
      <HeroIllustration />
      <div class="hero-inner">
        <h1>Khám phá Vĩnh Long <br>theo cách của người bản địa</h1>
        <p>Trải nghiệm miệt vườn, đặc sản theo mùa, làng nghề và lịch trình gợi ý — tất cả trong một bản đồ.</p>
        <form class="hero-search" @submit.prevent="onHeroSearch">
          <input v-model="heroQ" type="search" placeholder="Tìm: chôm chôm, kẹo dừa, cù lao An Bình…" />
          <button type="submit">Tìm</button>
        </form>
        <div v-if="stats" class="hero-stats">
          <span>{{ stats.total }} điểm dữ liệu</span>
          <span>{{ stats.places }} xã/phường</span>
          <span>{{ stats.itineraries }} lịch trình</span>
        </div>
      </div>
    </section>
    <WeatherBar />

    <!-- Saved recently (client-side) -->
    <ClientOnly>
      <section v-if="recentSaved.length" class="block">
        <div class="section-head">
          <h2>❤️ Đã lưu gần đây</h2>
          <NuxtLink class="see-all" to="/hanh-trinh">Xem tất cả →</NuxtLink>
        </div>
        <div class="grid">
          <NuxtLink v-for="fav in recentSaved" :key="fav.id" :to="`/dia-diem/${fav.id}`" class="card" style="cursor: pointer">
            <div v-if="fav.image" class="cover cover-img">
              <img :src="fav.image" :alt="fav.name" loading="lazy" />
            </div>
            <div class="card-b">
              <span class="card-type">{{ getFavTypeMeta(fav.type).label }}</span>
              <h3>{{ fav.name }}</h3>
              <p v-if="fav.place_name" class="place">{{ fav.place_name }}</p>
            </div>
          </NuxtLink>
        </div>
        <div style="text-align: center; margin-top: 16px">
            <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-outline">Tạo lịch trình từ danh sách đã lưu</NuxtLink>
        </div>
      </section>
    </ClientOnly>

    <!-- Seasonal -->
    <section v-if="seasonal.length" class="block">
      <div class="section-head">
        <h2>🔥 Đang vào mùa tháng {{ currentMonth }}</h2>
        <NuxtLink class="see-all" to="/san-pham">Xem tất cả →</NuxtLink>
      </div>
      <div class="grid">
        <EntityCard v-for="e in seasonal" :key="e.id" :entity="e" :season-filter="String(currentMonth)" />
      </div>
    </section>

    <!-- Featured experiences -->
    <section class="block">
      <div class="section-head">
        <h2>🌾 Trải nghiệm nổi bật</h2>
        <NuxtLink class="see-all" to="/du-lich">Xem tất cả →</NuxtLink>
      </div>
      <div class="grid">
        <EntityCard v-for="e in experiences" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Products -->
    <section class="block">
      <div class="section-head">
        <h2>🍊 Đặc sản &amp; OCOP</h2>
        <NuxtLink class="see-all" to="/san-pham">Xem tất cả →</NuxtLink>
      </div>
      <div class="grid">
        <EntityCard v-for="e in products" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Itineraries -->
    <section v-if="itineraries.length" class="block">
      <div class="section-head">
        <h2>🗺️ Lịch trình gợi ý</h2>
        <NuxtLink class="see-all" to="/lich-trinh">Xem tất cả →</NuxtLink>
      </div>
      <div class="grid itin">
        <ItineraryCard v-for="it in itineraries" :key="it.id" :itinerary="it" />
      </div>
    </section>

    <!-- Recommendations -->
    <ClientOnly>
      <AIRecommendations title="Có thể bạn quan tâm" :limit="6" />
    </ClientOnly>

    <!-- Explore by interest -->
    <section class="block">
      <div class="section-head">
        <h2>🎯 Khám phá theo sở thích</h2>
      </div>
      <div class="interest-grid">
        <NuxtLink to="/kham-pha/am-thuc" class="interest-card">
          <span class="ic-emoji">🍲</span>
          <strong>Ẩm thực</strong>
          <span class="ic-desc">Món ngon miền Tây</span>
        </NuxtLink>
        <NuxtLink to="/kham-pha/thien-nhien" class="interest-card">
          <span class="ic-emoji">🌿</span>
          <strong>Thiên nhiên</strong>
          <span class="ic-desc">Miệt vườn sông nước</span>
        </NuxtLink>
        <NuxtLink to="/kham-pha/van-hoa" class="interest-card">
          <span class="ic-emoji">🛕</span>
          <strong>Văn hóa</strong>
          <span class="ic-desc">Di tích & chùa Khmer</span>
        </NuxtLink>
        <NuxtLink to="/kham-pha/lang-nghe" class="interest-card">
          <span class="ic-emoji">🏺</span>
          <strong>Làng nghề</strong>
          <span class="ic-desc">Gốm, kẹo dừa, chiếu</span>
        </NuxtLink>
        <NuxtLink to="/kham-pha/mua-sam" class="interest-card">
          <span class="ic-emoji">🛍️</span>
          <strong>Mua sắm</strong>
          <span class="ic-desc">OCOP & đặc sản</span>
        </NuxtLink>
      </div>
    </section>

    <!-- Routes -->
    <section class="block">
      <div class="section-head">
        <h2>🛤️ Tuyến đường gợi ý</h2>
        <NuxtLink class="see-all" to="/tuyen-duong">Xem tất cả →</NuxtLink>
      </div>
      <div class="route-preview-grid">
        <NuxtLink to="/tuyen-duong?vung=vinh-long" class="route-preview">
          <span>🍊</span> Vòng trái cây Vĩnh Long
        </NuxtLink>
        <NuxtLink to="/tuyen-duong?vung=ben-tre" class="route-preview">
          <span>🥥</span> Vòng dừa Bến Tre
        </NuxtLink>
        <NuxtLink to="/tuyen-duong?vung=tra-vinh" class="route-preview">
          <span>🛕</span> Vòng chùa Khmer Trà Vinh
        </NuxtLink>
      </div>
    </section>

    <!-- Areas -->
    <section class="block">
      <div class="section-head">
        <h2>📍 Khám phá theo khu vực</h2>
      </div>
      <div class="region-grid">
        <AreaCard v-for="ak in areaKeys" :key="ak" :area-key="ak" :count="areaCounts[ak] || 0" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META, CARD_TYPES, TOURISM_TYPES } from '~/composables/useConstants'
import { isYearRound, relevanceScore } from '~/composables/useSeason'

const { favorites } = useFavorites()
const recentSaved = computed(() => favorites.value.slice(0, 4))
function getFavTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

const currentMonth = new Date().getMonth() + 1
const heroQ = ref('')

const { data: statsData } = await useAsyncData('stats', () => $fetch('/api/stats'))
const { data: entitiesData } = await useAsyncData('home-entities', () => $fetch<any>('/api/entities?limit=200'))
const { data: itinerariesData } = await useAsyncData('home-itineraries', () => $fetch<any[]>('/api/itineraries'))

const stats = computed(() => {
  const raw = statsData.value as any
  if (!raw) return null
  return {
    total: raw.entities || 0,
    phuong: raw.phuong || 0,
    xa: raw.xa || 0,
    places: raw.places || 0,
    itineraries: raw.itineraries || 0,
  }
})

const allEntities = computed(() => {
  const raw = entitiesData.value
  if (!raw) return []
  return raw.entities || raw || []
})

const seasonal = computed(() => {
  const month = String(currentMonth)
  return allEntities.value
    .filter((e: any) => ['product', 'experience'].includes(e.type))
    .filter((e: any) => relevanceScore(e, month) >= 3)
    .slice(0, 8)
})

const experiences = computed(() => {
  const types = TOURISM_TYPES as readonly string[]
  return allEntities.value
    .filter((e: any) => types.includes(e.type))
    .slice(0, 6)
})

const products = computed(() => {
  return allEntities.value
    .filter((e: any) => e.type === 'product')
    .slice(0, 6)
})

const itineraries = computed(() => {
  return (itinerariesData.value || []).slice(0, 4)
})

const areaKeys = Object.keys(AREA_META)

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  const cardTypes = CARD_TYPES as readonly string[]
  for (const e of allEntities.value) {
    const area = e.place_area || e.area
    if (cardTypes.includes(e.type) && area) {
      counts[area] = (counts[area] || 0) + 1
    }
  }
  return counts
})

function onHeroSearch() {
  if (heroQ.value.trim()) {
    navigateTo(`/tim-kiem?q=${encodeURIComponent(heroQ.value.trim())}`)
  }
}

useSeoMeta({
  title: 'vinhlong360 — Du lịch & Sản phẩm địa phương',
  description: 'Cổng du lịch và sản phẩm địa phương Vĩnh Long: trải nghiệm miệt vườn, đặc sản theo mùa, OCOP, làng nghề và lịch trình gợi ý.',
  ogTitle: 'vinhlong360 — Du lịch & Sản phẩm địa phương',
  ogDescription: 'Khám phá Vĩnh Long theo cách của người bản địa.',
  ogImage: 'https://vinhlong360.vn/img/og-default.jpg',
})
useHead({
  link: [
    { rel: 'canonical', href: canonicalUrl('/') },
    { rel: 'preload', as: 'image', href: '/img/hero.jpg', fetchpriority: 'high' },
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
  ],
})
</script>
