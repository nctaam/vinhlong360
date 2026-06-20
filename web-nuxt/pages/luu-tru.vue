<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lưu trú' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-accommodation">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🏡</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ allEntities.length }}</span>
          <span class="stat-label">nơi lưu trú</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <span class="stat-num">{{ a.count }}</span>
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
    </section>

    <!-- Quick picks by region -->
    <section class="block">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META"
          :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string); scrollToGrid()"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} chỗ ở</span>
        </button>
      </div>
    </section>

    <!-- Featured -->
    <section v-if="featured.length" class="block reveal">
      <div class="section-head">
        <h2>Được gợi ý</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Lưu trú được gợi ý">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block reveal">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm nơi lưu trú…" aria-label="Tìm nơi lưu trú" />
        </div>
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

      <p class="result-meta" aria-live="polite">{{ filtered.length }} nơi lưu trú</p>
      <EmptyState v-if="fetchError" icon="⚠️" title="Chưa tải được nơi lưu trú" message="Có thể do kết nối mạng. Bạn thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-accommodation')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
      </div>
      <EmptyState v-else icon="🏡" title="Không tìm thấy nơi lưu trú" message="Thử thay đổi khu vực hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="areaFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm bản địa</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Mua quà miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'

useReveal()
const { f: pc } = usePageContent('luu_tru')

const q = ref('')
const areaFilter = ref('all')
const gridSection = ref<HTMLElement | null>(null)
useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data, error: fetchError } = await useAsyncData('catalog-accommodation', () =>
  $fetch<{ entities: Entity[] }>('/api/entities?type=accommodation&limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) {
    const area = e.place_area || e.area || ''
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return Object.entries(AREA_META)
    .filter(([key]) => counts[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: counts[key] }))
})

function countByArea(key: string) {
  return allEntities.value.filter((e: Entity) => (e.place_area || e.area) === key).length
}

const featured = computed(() => {
  return allEntities.value
    .filter((e: Entity) => e.images?.length)
    .slice(0, 6)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const filtered = computed(() => {
  let list = allEntities.value

  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => (e.place_area || e.area) === areaFilter.value)
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query) ||
      (e.place_name || '').toLowerCase().includes(query)
    )
  }

  return list
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/luu-tru') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: 'Lưu trú Vĩnh Long',
      description: 'Homestay, nhà vườn, khách sạn và nơi nghỉ ở Vĩnh Long, Bến Tre, Trà Vinh.',
      url: 'https://vinhlong360.vn/luu-tru',
    }),
  }],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Lưu trú Vĩnh Long, Bến Tre, Trà Vinh',
      'Homestay, nhà vườn, khách sạn và nơi nghỉ ở miền Tây.',
      '/luu-tru',
      filtered.value,
    )),
  }],
}))
</script>
