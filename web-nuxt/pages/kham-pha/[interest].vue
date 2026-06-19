<template>
  <section class="page">
    <Breadcrumb :items="breadcrumbItems" />

    <!-- Hero -->
    <section class="catalog-hero cat-interest">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">{{ interestMeta.emoji }}</span>
        <div>
          <h1>{{ interestMeta.label }}</h1>
          <p>{{ interestMeta.description }}</p>
        </div>
      </div>
      <div v-if="filtered.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ filtered.length }}</span>
          <span class="stat-label">mục</span>
        </div>
      </div>
    </section>

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

    <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả</p>
    <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau." />
    <SkeletonGrid v-else-if="!data" :count="6" />
    <div v-else-if="filtered.length" class="grid">
      <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
    </div>
    <EmptyState v-else message="Không tìm thấy kết quả phù hợp." />

    <!-- Cross-links -->
    <section class="block catalog-cross reveal">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink v-if="interestMeta.relatedRoutes?.length" to="/tuyen-duong" class="cross-card">
          <span class="cross-icon">🛤️</span>
          <div><strong>Tuyến đường</strong><p>Vòng khám phá gợi ý</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm sao</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

useReveal()

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

if (!INTEREST_META[interest]) {
  throw createError({ statusCode: 404, statusMessage: 'Chủ đề không tồn tại' })
}

const interestMeta = computed(() => INTEREST_META[interest])

const breadcrumbItems = computed(() => [
  { label: 'Trang chủ', to: '/' },
  { label: 'Khám phá', to: '/kham-pha/am-thuc' },
  { label: interestMeta.value.label },
])

const areaFilter = ref('all')
useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data, error: fetchError } = await useAsyncData(`interest-${interest}`, () =>
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

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      `${interestMeta.value.label} — Khám phá miền Tây`,
      interestMeta.value.description,
      `/kham-pha/${interest}`,
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
.interest-nav { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-5); }
.interest-nav .chip { transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out), background .3s var(--ease-out), border-color .3s var(--ease-out); }
.interest-nav .chip:hover { transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.interest-nav .chip:active { transform: scale(.95); transition-duration: .08s; }
.interest-nav .chip.active { box-shadow: var(--shadow-sm); }

@media (max-width: 840px) { .interest-nav { flex-wrap: wrap; overflow-x: visible; } }

.result-meta { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-3); }

/* Dark mode */
.dark .interest-nav .chip { background: var(--bg-alt); border-color: var(--line); }
.dark .interest-nav .chip:hover { border-color: rgba(255,255,255,.15); }
.dark .interest-nav .chip.active { background: rgba(var(--primary-rgb), .12); border-color: var(--primary-fg); }
.dark .result-meta { color: var(--ink-tertiary); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .interest-nav .chip:hover { transform: none; }
  .interest-nav .chip:active { transform: none; }
}
</style>
