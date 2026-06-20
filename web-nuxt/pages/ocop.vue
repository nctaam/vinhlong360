<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sản phẩm', to: '/san-pham' }, { label: 'OCOP' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-ocop">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">⭐</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allOcop.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ allOcop.length }}</span>
          <span class="stat-label">sản phẩm OCOP</span>
        </div>
        <div v-for="s in starStats" :key="s.stars" class="stat-item">
          <span class="stat-num">{{ s.count }}</span>
          <span class="stat-label">{{ s.stars }} sao</span>
        </div>
      </div>
    </section>

    <!-- Star breakdown quick-picks -->
    <section v-if="starStats.length" class="block">
      <div class="section-head">
        <h2>Xếp hạng sao</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="s in starStats" :key="s.stars"
          :class="['quick-pick', { active: starFilter === s.stars }]"
          :aria-pressed="starFilter === s.stars"
          @click="starFilter = starFilter === s.stars ? 0 : s.stars; scrollToGrid()"
        >
          <span class="quick-pick-icon">{{ '⭐'.repeat(s.stars) }}</span>
          <span class="quick-pick-label">{{ s.stars }} sao</span>
          <span class="quick-pick-count">{{ s.count }} sản phẩm</span>
        </button>
      </div>
    </section>

    <!-- Featured 5-star -->
    <section v-if="fiveStarHighlights.length" class="block reveal">
      <div class="section-head">
        <h2>⭐ Nổi bật 5 sao</h2>
        <button type="button" class="see-all" @click="starFilter = 5; scrollToGrid()">Xem tất cả →</button>
      </div>
      <p class="section-desc">Sản phẩm đạt chuẩn cao nhất — 5 sao OCOP, chất lượng vượt trội.</p>
      <div class="scroll-row" role="region" aria-label="Sản phẩm OCOP 5 sao">
        <EntityCard v-for="e in fiveStarHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Region quick-picks -->
    <section class="block reveal">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string); scrollToGrid()"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} sản phẩm</span>
        </button>
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
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm sản phẩm OCOP…" aria-label="Tìm sản phẩm OCOP" />
        </div>
        <p class="control-label">Hạng sao</p>
        <div class="chip-row" role="group" aria-label="Lọc theo hạng sao">
          <button type="button" :class="['chip', { active: starFilter === 0 }]" :aria-pressed="starFilter === 0" @click="starFilter = 0">Tất cả</button>
          <button type="button" :class="['chip', { active: starFilter === 5 }]" :aria-pressed="starFilter === 5" @click="starFilter = 5">⭐⭐⭐⭐⭐ 5 sao</button>
          <button type="button" :class="['chip', { active: starFilter === 4 }]" :aria-pressed="starFilter === 4" @click="starFilter = 4">⭐⭐⭐⭐ 4 sao</button>
          <button type="button" :class="['chip', { active: starFilter === 3 }]" :aria-pressed="starFilter === 3" @click="starFilter = 3">⭐⭐⭐ 3 sao</button>
        </div>
        <p class="control-label">Khu vực</p>
        <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
          <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả</button>
          <button type="button"
            v-for="(meta, key) in AREA_META" :key="key"
            :class="['chip', { active: areaFilter === key }]"
            :aria-pressed="areaFilter === key"
            @click="areaFilter = key as string"
          >{{ meta.emoji }} {{ meta.name }}</button>
        </div>
        <p class="control-label">Theo tháng</p>
        <div class="chip-row" role="group" aria-label="Lọc theo tháng">
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'all' }]" :aria-pressed="seasonFilter === 'all'" @click="seasonFilter = 'all'">Tất cả</button>
          <button type="button" v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" :aria-pressed="seasonFilter === String(m)" @click="seasonFilter = String(m)">
            T{{ m }}
          </button>
        </div>
      </div>

      <p class="result-meta" aria-live="polite">{{ filtered.length }} sản phẩm OCOP</p>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải sản phẩm OCOP" message="Mạng có thể đang chập chờn. Thử lại giúp mình nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-ocop')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="⭐" title="Không tìm thấy sản phẩm OCOP" message="Thử thay đổi hạng sao, khu vực hoặc tháng mùa vụ.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="starFilter = 0; areaFilter = 'all'; seasonFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <NuxtLink to="/san-pham" class="btn btn-outline">Xem tất cả sản phẩm</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Tất cả sản phẩm</p></div>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="cross-card">
          <span class="cross-icon">📅</span>
          <div><strong>Theo mùa</strong><p>Lịch mùa vụ</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/kham-pha/am-thuc" class="cross-card">
          <span class="cross-icon">🍲</span>
          <div><strong>Ẩm thực</strong><p>Món ngon miền Tây</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('ocop')

const q = ref('')
const starFilter = ref(0)
const areaFilter = ref('all')
const seasonFilter = ref('all')
const gridSection = ref<HTMLElement | null>(null)

const starFilterStr = computed({
  get: () => String(starFilter.value),
  set: (v: string) => { starFilter.value = parseInt(v) || 0 },
})
useFilterUrl({ sao: starFilterStr, vung: areaFilter, mua: seasonFilter }, { sao: '0', vung: 'all', mua: 'all' })

const { data, error: fetchError } = await useAsyncData('catalog-ocop', () =>
  $fetch<{ entities: Entity[] }>('/api/entities?type=product&limit=200')
)

const allOcop = computed(() => {
  const raw = data.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => e.attributes?.ocop)
})

function getStars(e: Entity): number {
  return parseInt(e.attributes?.ocop) || 0
}

const starStats = computed(() => {
  const counts: Record<number, number> = {}
  for (const e of allOcop.value) {
    const s = getStars(e)
    if (s >= 3) counts[s] = (counts[s] || 0) + 1
  }
  return [5, 4, 3].filter(s => counts[s]).map(s => ({ stars: s, count: counts[s] }))
})

const fiveStarHighlights = computed(() =>
  allOcop.value.filter(e => getStars(e) >= 5).slice(0, 8)
)

function countByArea(key: string) {
  return allOcop.value.filter((e: Entity) => (e.place_area || e.area) === key).length
}

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const filtered = computed(() => {
  let list = allOcop.value

  if (starFilter.value > 0) {
    list = list.filter((e: Entity) => getStars(e) >= starFilter.value)
  }

  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => (e.place_area || e.area) === areaFilter.value)
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

  if (seasonFilter.value !== 'all') {
    list.sort((a: Entity, b: Entity) => relevanceScore(b, seasonFilter.value) - relevanceScore(a, seasonFilter.value))
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
  link: [{ rel: 'canonical', href: canonicalUrl('/ocop') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Sản phẩm OCOP Vĩnh Long',
        description: 'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre, Trà Vinh.',
        url: 'https://vinhlong360.vn/ocop',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Sản phẩm', item: 'https://vinhlong360.vn/san-pham' },
          { '@type': 'ListItem', position: 3, name: 'OCOP' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Sản phẩm OCOP Vĩnh Long, Bến Tre, Trà Vinh',
      'Sản phẩm đạt chuẩn OCOP từ Vĩnh Long, Bến Tre và Trà Vinh.',
      '/ocop',
      filtered.value,
    )),
  }],
}))
</script>
