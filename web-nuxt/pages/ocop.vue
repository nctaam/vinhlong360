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
          <div class="hero-creds">
            <span class="hero-cred hero-cred-seal">🏅 Chuẩn OCOP <em>Nhà nước</em></span>
            <span class="hero-cred">✓ Kiểm chứng</span>
            <span v-if="allOcop.length" class="hero-cred">📊 {{ allOcop.length }} sản phẩm</span>
          </div>
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
      <div class="honor-banner">
        <span class="honor-banner-icon" aria-hidden="true">👑</span>
        <span class="honor-banner-text">Danh sách vinh dự</span>
      </div>
      <div class="scroll-row honor-roll" role="region" aria-label="Sản phẩm OCOP 5 sao">
        <EntityCard v-for="e in fiveStarHighlights" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Region quick-picks -->
    <section class="block reveal">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks region-quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', 'region-pick', { active: areaFilter === key }]"
          :style="{ '--AREA-rgb': REGION_RGB[key as string] || 'var(--primary-rgb)' }"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string); scrollToGrid()"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span v-if="REGION_TAGLINE[key as string]" class="region-tagline">{{ REGION_TAGLINE[key as string] }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} sản phẩm</span>
        </button>
      </div>
    </section>

    <!-- Editorial -->
    <section class="page-article reveal">
      <h2>OCOP là gì?</h2>
      <p>OCOP (One Commune One Product — Mỗi xã Một sản phẩm) là chương trình quốc gia nhằm phát triển kinh tế nông thôn thông qua việc nâng cao chất lượng và giá trị sản phẩm địa phương. Mỗi xã, phường xác định một hoặc vài sản phẩm thế mạnh, được hỗ trợ chuẩn hoá quy trình sản xuất, bao bì, truy xuất nguồn gốc và kết nối thị trường.</p>

      <h2>Hệ thống xếp hạng sao</h2>
      <p>Sản phẩm OCOP được đánh giá theo thang 5 sao bởi hội đồng cấp tỉnh và trung ương. <strong>3 sao</strong> là mức cơ bản — sản phẩm đạt tiêu chuẩn an toàn thực phẩm, có nhãn mác rõ ràng. <strong>4 sao</strong> yêu cầu chất lượng cao hơn, bao bì chuyên nghiệp, có câu chuyện sản phẩm và khả năng mở rộng thị trường. <strong>5 sao</strong> là cấp quốc gia — rất hiếm, dành cho sản phẩm xuất sắc có tiềm năng xuất khẩu.</p>
      <p>Khi bạn thấy nhãn OCOP trên sản phẩm, bạn biết sản phẩm đó đã qua quy trình đánh giá nghiêm ngặt, có nguồn gốc rõ ràng và chất lượng được kiểm chứng — không phải tự phong hay tự gắn nhãn.</p>

      <h2>OCOP vùng Vĩnh Long, Bến Tre, Trà Vinh</h2>
      <p>Ba tỉnh thuộc top đầu cả nước về số lượng sản phẩm OCOP, nhờ lợi thế nông nghiệp phong phú. Bến Tre dẫn đầu với các sản phẩm từ dừa: dầu dừa nguyên chất, kẹo dừa, thạch dừa, mỹ phẩm từ dừa. Vĩnh Long nổi bật với bưởi Năm Roi, nem chua Lai Vung, gạch gốm Mang Thít. Trà Vinh đóng góp các đặc sản Khmer như bánh tét lá cẩm, dừa sáp và mắm prohok.</p>
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

// Per-region accent + tagline for the premium region quick-picks (geo-provenance).
// Colors reuse the existing area→token convention (see catalog.css .cat-area-*).
const REGION_RGB: Record<string, string> = {
  'vinh-long': 'var(--primary-rgb)',
  'ben-tre': 'var(--secondary-rgb)',
  'tra-vinh': 'var(--river-rgb)',
}
const REGION_TAGLINE: Record<string, string> = {
  'vinh-long': 'Miệt vườn cam sành',
  'ben-tre': 'Xứ dừa ngọt lành',
  'tra-vinh': 'Đặc sản dừa sáp',
}

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
  apiFetch<{ entities: Entity[] }>('/api/entities?type=product&limit=200')
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
    list = [...list].sort((a: Entity, b: Entity) => (relevanceScore(b, seasonFilter.value) || 0) - (relevanceScore(a, seasonFilter.value) || 0))
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

<style scoped>
/* Hero provenance / trust signals (OCOP official seal credibility) */
.hero-creds {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-6);
  font-size: var(--text-xs);
  padding: var(--space-4) 0 0;
  margin-top: var(--space-4);
  border-top: .5px solid var(--line);
}
.hero-cred {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--muted);
  font-weight: var(--weight-medium);
}
.hero-cred-seal {
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: .03em;
  color: var(--primary-fg);
}
.hero-cred-seal em { font-style: normal; color: var(--muted); text-transform: none; letter-spacing: 0; }

/* Honor roll banner above the 5-star carousel */
.honor-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  border-left: 3px solid var(--secondary);
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, rgba(var(--secondary-rgb), .08), transparent);
}
.honor-banner-icon { font-size: 1.25rem; }
.honor-banner-text {
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  color: var(--secondary-fg, var(--secondary));
  letter-spacing: var(--tracking-tight);
}
/* Curated-collection lift + glow for honor-roll cards */
.honor-roll :deep(.card:hover) {
  box-shadow: var(--shadow-lg), 0 0 0 1px rgba(var(--secondary-rgb), .2), 0 18px 40px -18px rgba(var(--secondary-rgb), .35);
  transform: translateY(-8px);
}

/* Premium region quick-picks with geo-provenance accent + tagline */
.region-quick-picks .region-pick {
  background: linear-gradient(135deg, rgba(var(--AREA-rgb), .06), transparent);
}
.region-quick-picks .region-pick:hover {
  border-color: rgba(var(--AREA-rgb), .55);
  box-shadow: var(--shadow-md), 0 0 0 1px rgba(var(--AREA-rgb), .3);
}
.region-quick-picks .region-pick.active {
  border-color: rgba(var(--AREA-rgb), .9);
  background: linear-gradient(135deg, rgba(var(--AREA-rgb), .12), transparent);
}
.region-tagline {
  font-size: var(--text-xs);
  color: var(--muted);
  font-style: italic;
}

/* Filter panel labeled sections — clearer scannable groups (OCOP page only) */
.controls .control-label {
  position: relative;
  font-size: .8rem;
  padding-left: var(--space-3);
}
.controls .control-label::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: .85em;
  border-radius: 2px;
  background: var(--primary-fg);
}

.dark .hero-cred-seal { color: var(--primary-fg); }
.dark .honor-banner { background: linear-gradient(90deg, rgba(var(--secondary-rgb), .12), transparent); }

@media (prefers-reduced-motion: reduce) {
  .honor-roll :deep(.card:hover) { transform: none; }
}

@media (max-width: 640px) {
  .hero-creds { gap: var(--space-4); }
}
</style>
