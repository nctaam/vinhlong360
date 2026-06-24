<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lưu trú' }]" :json-ld="true" />

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
      <ul v-if="typeCounts.length" class="catalog-type-breakdown" aria-label="Phân loại nơi lưu trú">
        <li v-for="t in typeCounts" :key="t.label" class="type-pill">
          <span class="type-count">{{ t.count }}</span>
          <span class="type-name">{{ t.label }}</span>
        </li>
      </ul>
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
        <h2>✨ Nơi ở được yêu thích</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Nơi ở được yêu thích">
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
      <EmptyState v-if="fetchError" tone="error" icon="🌊" title="Rất tiếc, chưa tải được" message="Kết nối mạng đang chập chờn. Bạn thử tải lại một lần nữa nhé." hint="Nếu vẫn chưa được, thử lại sau ít phút giúp mình.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-accommodation')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" class="grid">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" />
      </div>
      <EmptyState v-else icon="🏡" title="Chưa thấy nơi ở phù hợp" message="Thử đổi khu vực hoặc từ khóa khác xem sao nhé." hint="Bạn có thể khám phá thêm các nơi ở ở Vĩnh Long, Bến Tre và Trà Vinh.">
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
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Ghép lưu trú vào kế hoạch đi</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm bản địa</p></div>
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
  apiFetch<{ entities: Entity[] }>('/api/entities?type=accommodation&limit=200')
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

// Data-driven accommodation type breakdown for hero confidence (no fabricated values):
// prefer the accommodation_type attribute, fall back to inferring from the name.
const TYPE_LABELS: Record<string, string> = {
  'khách sạn': 'Khách sạn',
  homestay: 'Homestay',
  'nhà vườn': 'Nhà vườn',
  resort: 'Resort',
  'nhà nghỉ': 'Nhà nghỉ',
}
function entityTypeKey(e: Entity): string {
  const raw = (e.attributes?.accommodation_type as string | undefined)?.toString().toLowerCase().trim()
  if (raw && TYPE_LABELS[raw]) return raw
  const n = (e.name || '').toLowerCase()
  if (n.includes('homestay')) return 'homestay'
  if (n.includes('khách sạn') || n.includes('hotel')) return 'khách sạn'
  if (n.includes('nhà vườn')) return 'nhà vườn'
  if (n.includes('resort')) return 'resort'
  if (n.includes('nhà nghỉ')) return 'nhà nghỉ'
  return ''
}
const typeCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) {
    const key = entityTypeKey(e)
    if (key) counts[key] = (counts[key] || 0) + 1
  }
  return Object.entries(counts)
    .map(([key, count]) => ({ label: TYPE_LABELS[key] || key, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

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

<style scoped>
/* Quick-pick supply count rendered as a secondary badge pill (Airbnb-style
   "supply per region" cue). River-blue tint = accommodation category color. */
.quick-pick-count {
  align-self: center;
  margin-top: var(--space-1);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  background: rgba(var(--river-rgb, var(--primary-rgb)), .12);
  color: var(--tertiary, var(--primary-fg));
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  line-height: 1.4;
  transition: background .3s var(--ease-out);
}
.quick-pick.active .quick-pick-count,
.quick-pick:hover .quick-pick-count {
  background: rgba(var(--river-rgb, var(--primary-rgb)), .2);
}
:global(.dark) .quick-pick-count {
  background: rgba(var(--river-rgb, var(--primary-rgb)), .18);
  color: var(--ink);
}
:global(.dark) .quick-pick.active .quick-pick-count,
:global(.dark) .quick-pick:hover .quick-pick-count {
  background: rgba(var(--river-rgb, var(--primary-rgb)), .28);
}

/* Hero accommodation type breakdown — supply-by-category trust cue.
   Data-driven from typeCounts; only renders when data is present. */
.catalog-type-breakdown {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}
.type-pill {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: rgba(var(--river-rgb, var(--primary-rgb)), .1);
  border: .5px solid rgba(var(--river-rgb, var(--primary-rgb)), .2);
  font-size: var(--text-xs);
  transition: background .3s var(--ease-out), transform .3s var(--ease-spring-gentle);
}
.type-pill:hover { transform: translateY(-1px); background: rgba(var(--river-rgb, var(--primary-rgb)), .16); }
.type-count { font-weight: var(--weight-bold); color: var(--tertiary, var(--primary-fg)); }
.type-name { color: var(--muted); font-weight: var(--weight-medium); }
:global(.dark) .type-pill {
  background: rgba(var(--river-rgb, var(--primary-rgb)), .16);
  border-color: rgba(var(--river-rgb, var(--primary-rgb)), .3);
}
:global(.dark) .type-pill:hover { background: rgba(var(--river-rgb, var(--primary-rgb)), .24); }
:global(.dark) .type-count { color: var(--ink); }
:global(.dark) .type-name { color: var(--muted); }

@media (prefers-reduced-motion: reduce) {
  .quick-pick-count,
  .type-pill { transition: none; }
  .type-pill:hover { transform: none; }
}
</style>
