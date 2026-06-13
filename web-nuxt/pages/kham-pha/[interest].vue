<template>
  <section class="page">
    <Breadcrumb :items="breadcrumbItems" />
    <div class="page-head">
      <h1>{{ interestMeta.emoji }} {{ interestMeta.label }}</h1>
      <p>{{ interestMeta.description }}</p>
    </div>

    <div class="interest-nav">
      <NuxtLink
        v-for="(meta, key) in INTEREST_META"
        :key="key"
        :to="`/kham-pha/${key}`"
        :class="['chip', { active: key === interest }]"
      >{{ meta.emoji }} {{ meta.label }}</NuxtLink>
    </div>

    <div class="controls">
      <p class="control-label">Khu vực</p>
      <div class="chip-row">
        <button :class="['chip', { active: areaFilter === 'all' }]" @click="areaFilter = 'all'">Tất cả</button>
        <button
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['chip', { active: areaFilter === key }]"
          @click="areaFilter = key as string"
        >{{ meta.emoji }} {{ meta.name }}</button>
      </div>
    </div>

    <p class="result-meta">{{ filtered.length }} kết quả</p>
    <SkeletonGrid v-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
    </div>
    <EmptyState v-else message="Không tìm thấy kết quả phù hợp." />

    <div v-if="interestMeta.relatedRoutes?.length" class="related-section">
      <h2>🛤️ Tuyến đường liên quan</h2>
      <div class="related-links">
        <NuxtLink to="/tuyen-duong" class="btn btn-outline">Xem tất cả tuyến đường →</NuxtLink>
      </div>
    </div>

    <div class="related-section">
      <h2>📂 Khám phá theo chủ đề khác</h2>
      <div class="interest-nav">
        <NuxtLink
          v-for="(meta, key) in INTEREST_META"
          :key="key"
          :to="`/kham-pha/${key}`"
          :class="['chip', { active: key === interest }]"
        >{{ meta.emoji }} {{ meta.label }}</NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

interface InterestDef {
  emoji: string
  label: string
  description: string
  types: string[]
  relatedRoutes?: string[]
}

const INTEREST_META: Record<string, InterestDef> = {
  'am-thuc': {
    emoji: '🍲',
    label: 'Ẩm thực',
    description: 'Món ngon miền Tây — từ bún nước lèo, bánh xèo đến đặc sản trái cây theo mùa.',
    types: ['dish', 'product'],
    relatedRoutes: ['vong-am-thuc-mien-tay'],
  },
  'thien-nhien': {
    emoji: '🌿',
    label: 'Thiên nhiên',
    description: 'Miệt vườn sông nước, cù lao xanh mát, vườn trái cây và đồng lúa bát ngàn.',
    types: ['experience', 'attraction'],
    relatedRoutes: ['vong-trai-cay-vinh-long', 'vong-mua-nuoc-noi'],
  },
  'van-hoa': {
    emoji: '🛕',
    label: 'Văn hóa',
    description: 'Di tích lịch sử, chùa Khmer cổ, lễ hội truyền thống và đời sống bản địa.',
    types: ['attraction', 'craft_village'],
    relatedRoutes: ['vong-chua-khmer-tra-vinh'],
  },
  'lang-nghe': {
    emoji: '🏺',
    label: 'Làng nghề',
    description: 'Gốm Mang Thít, kẹo dừa, chiếu lác, bánh tráng — nghề truyền thống hàng trăm năm.',
    types: ['craft_village', 'organization'],
    relatedRoutes: ['vong-lang-nghe-mang-thit'],
  },
  'mua-sam': {
    emoji: '🛍️',
    label: 'Mua sắm & OCOP',
    description: 'Sản phẩm OCOP, đặc sản làm quà, trái cây tươi và hàng thủ công mỹ nghệ.',
    types: ['product'],
  },
}

const route = useRoute()
const interest = route.params.interest as string
const interestMeta = computed(() => INTEREST_META[interest] || INTEREST_META['am-thuc'])

const breadcrumbItems = computed(() => [
  { label: 'Trang chủ', to: '/' },
  { label: 'Khám phá', to: '/kham-pha/am-thuc' },
  { label: interestMeta.value.label },
])

const areaFilter = ref('all')
useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data } = await useAsyncData(`interest-${interest}`, () =>
  $fetch<any>('/api/entities?limit=200')
)

const filtered = computed(() => {
  const raw = data.value
  if (!raw) return []
  let list = (raw.entities || []).filter((e: any) => interestMeta.value.types.includes(e.type))

  if (areaFilter.value !== 'all') {
    list = list.filter((e: any) => (e.place_area || e.area) === areaFilter.value)
  }

  return list
})

useSeoMeta({
  title: `${interestMeta.value.emoji} ${interestMeta.value.label} — Khám phá miền Tây — vinhlong360`,
  description: interestMeta.value.description,
  ogTitle: `${interestMeta.value.label} — vinhlong360`,
  ogDescription: interestMeta.value.description,
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/kham-pha/${interest}`) }],
})

useHead({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: `${interestMeta.value.label} — Khám phá miền Tây`,
      description: interestMeta.value.description,
      url: `https://vinhlong360.vn/kham-pha/${interest}`,
    }),
  }],
})
</script>

<style scoped>
.interest-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.related-section { margin-top: 32px; }
.related-section h2 { font-size: 1.1rem; margin: 0 0 12px; }
.related-links { display: flex; gap: 8px; }
</style>
