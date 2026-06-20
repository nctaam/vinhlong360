<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Du lịch' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-experience">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🌿</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats">
        <div class="stat-item" v-for="s in stats" :key="s.label">
          <span class="stat-num">{{ s.count }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Featured -->
    <section v-if="featured.length" class="block reveal">
      <div class="section-head">
        <h2>Nổi bật</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Trải nghiệm nổi bật">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Category sections -->
    <section v-for="cat in categories" :key="cat.type" class="block reveal">
      <div class="section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <button type="button" class="see-all" @click="typeFilter = cat.type; scrollToGrid()">{{ cat.items.length }} kết quả →</button>
      </div>
      <p class="section-desc">{{ cat.desc }}</p>
      <div class="scroll-row" role="region" :aria-label="cat.label">
        <EntityCard v-for="e in cat.items.slice(0, 8)" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm trong du lịch…" aria-label="Tìm kiếm" />
        </div>
        <p class="control-label">Loại</p>
        <div class="chip-row" role="group" aria-label="Lọc theo loại">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" :aria-pressed="typeFilter === 'all'" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button" v-for="t in typeChips" :key="t.value" :class="['chip', { active: typeFilter === t.value }]" :aria-pressed="typeFilter === t.value" @click="typeFilter = t.value">
            {{ t.label }}
          </button>
        </div>
        <p class="control-label">Theo tháng</p>
        <div class="chip-row" role="group" aria-label="Lọc theo tháng">
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'all' }]" :aria-pressed="seasonFilter === 'all'" @click="seasonFilter = 'all'">Tất cả</button>
          <button type="button" v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" :aria-pressed="seasonFilter === String(m)" @click="seasonFilter = String(m)">
            T{{ m }}
          </button>
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'flood' }]" :aria-pressed="seasonFilter === 'flood'" @click="seasonFilter = 'flood'">🌊 Mùa nước nổi</button>
        </div>
      </div>
      <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả</p>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Mạng có thể đang chập chờn. Thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-tourism')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🌿" title="Không tìm thấy kết quả" message="Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="typeFilter = 'all'; seasonFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <NuxtLink to="/theo-mua" class="btn btn-outline">Xem theo mùa</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Sản phẩm theo mùa</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META, TOURISM_TYPES } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('du_lich')
const TYPES = TOURISM_TYPES as readonly string[]

const typeChips = TYPES.map(t => ({
  value: t,
  label: `${TYPE_META[t].emoji} ${TYPE_META[t].label}`,
}))

const q = ref('')
const typeFilter = ref('all')
const seasonFilter = ref('all')
const gridSection = ref<HTMLElement | null>(null)

useFilterUrl({ type: typeFilter, mua: seasonFilter }, { type: 'all', mua: 'all' })

const { data, error: fetchError } = await useAsyncData('catalog-tourism', () =>
  $fetch<{ entities: Entity[] }>('/api/entities?limit=200')
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => TYPES.includes(e.type))
})

const stats = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) counts[e.type] = (counts[e.type] || 0) + 1
  return TYPES
    .filter(t => counts[t])
    .map(t => ({ label: TYPE_META[t].label, count: counts[t] }))
})

const featured = computed(() => {
  return allEntities.value
    .filter((e: Entity) => e.images?.length)
    .slice(0, 6)
})

const CATEGORY_DESC: Record<string, string> = {
  experience: 'Chèo xuồng, đạp xe miệt vườn, tát mương bắt cá — trải nghiệm đời sống sông nước Nam Bộ.',
  attraction: 'Chùa cổ, di tích lịch sử, cù lao, vườn trái cây — những điểm đến đáng ghé nhất.',
  craft_village: 'Gốm Mang Thít, kẹo dừa, chiếu lác, bánh tráng — nghề truyền thống hàng trăm năm.',
  dish: 'Bún nước lèo, bánh xèo, hủ tiếu, chả lụi — hương vị chỉ có ở miền Tây.',
  accommodation: 'Homestay nhà vườn, resort sông nước, nhà nghỉ dân dã — nơi lưu lại qua đêm.',
}

const categories = computed(() => {
  return TYPES
    .map(t => ({
      type: t,
      emoji: TYPE_META[t].emoji,
      label: TYPE_META[t].label,
      desc: CATEGORY_DESC[t] || '',
      items: allEntities.value.filter((e: Entity) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const filtered = computed(() => {
  let list = allEntities.value

  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: Entity) => inSeason(e, seasonFilter.value))
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query)
    )
  }

  list.sort((a: Entity, b: Entity) => relevanceScore(b, seasonFilter.value) - relevanceScore(a, seasonFilter.value))
  return list
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/du-lich') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Du lịch Vĩnh Long',
        description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.',
        url: 'https://vinhlong360.vn/du-lich',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Du lịch' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Du lịch Vĩnh Long, Bến Tre, Trà Vinh',
      'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực miền Tây.',
      '/du-lich',
      filtered.value,
    )),
  }],
}))
</script>
