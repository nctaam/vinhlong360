<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Theo mùa' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-season">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">📅</span>
        <div>
          <h1>{{ pc('hero_title', 'Tháng ' + month + ' — đi đâu, ăn gì?') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="inSeasonItems.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ inSeasonItems.length }}</span>
          <span class="stat-label">đang mùa</span>
        </div>
        <div v-if="peakCount" class="stat-item">
          <span class="stat-num">{{ peakCount }}</span>
          <span class="stat-label">cao điểm</span>
        </div>
        <div v-for="t in typeStats" :key="t.type" class="stat-item">
          <span class="stat-num">{{ t.count }}</span>
          <span class="stat-label">{{ t.label }}</span>
        </div>
      </div>
    </section>

    <!-- Month selector -->
    <section class="block">
      <div class="section-head">
        <h2>Chọn tháng</h2>
      </div>
      <div class="month-grid">
        <button type="button"
          v-for="m in 12" :key="m"
          :class="['quick-pick', { active: m === month }]"
          :aria-pressed="m === month"
          @click="month = m"
        >
          <span class="quick-pick-label">Tháng {{ m }}</span>
          <span class="quick-pick-count">{{ countByMonth(m) }} mục</span>
        </button>
      </div>
    </section>

    <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau." />
    <ClientOnly>
      <SkeletonGrid v-if="!data && !fetchError" />
      <template #fallback>
        <SkeletonGrid v-if="!data && !fetchError" />
      </template>
    </ClientOnly>

    <!-- Peak highlights -->
    <section v-if="peakItems.length" class="block reveal">
      <div class="seasonal-banner">
        <span class="seasonal-banner-icon">🔥</span>
        <div>
          <strong>Cao điểm tháng {{ month }}</strong>
          <p>Những mục chính vụ, thời điểm ngon nhất — không nên bỏ lỡ.</p>
        </div>
      </div>
      <div class="scroll-row" role="region" aria-label="Cao điểm tháng này">
        <div v-for="e in peakItems" :key="e.id" class="season-item">
          <span class="season-badge peak">Cao điểm</span>
          <EntityCard :entity="e" />
        </div>
      </div>
    </section>

    <!-- Type sections -->
    <section v-for="cat in typeSections" :key="cat.type" class="block reveal">
      <div class="section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <span class="see-all-count">{{ cat.items.length }} mục</span>
      </div>
      <p class="section-desc">{{ cat.desc }}</p>
      <div class="scroll-row" role="region" :aria-label="cat.label + ' đang mùa'">
        <div v-for="e in cat.items.slice(0, 8)" :key="e.id" class="season-item">
          <span v-if="isPeak(e)" class="season-badge peak">Cao điểm</span>
          <span v-else class="season-badge">Đang mùa</span>
          <EntityCard :entity="e" />
          <small class="season-when">🗓️ {{ seasonText(e.season) }}</small>
        </div>
      </div>
    </section>

    <!-- B2B note -->
    <p class="b2b-note">
      🤝 Cần <strong>mua sỉ nông sản theo mùa</strong> hoặc kết nối HTX/nhà vườn? Liên hệ trực tiếp cơ sở ở mỗi mục,
      hoặc <NuxtLink to="/lien-he">gửi yêu cầu nguồn sỉ</NuxtLink>.
    </p>

    <!-- Divider -->
    <div v-if="ranked.length" class="catalog-divider">
      <span class="catalog-divider-text">Tất cả đang mùa</span>
    </div>

    <!-- Full grid -->
    <section v-if="ranked.length" class="block reveal">
      <div class="grid">
        <div v-for="e in ranked" :key="e.id" class="season-item">
          <span v-if="isPeak(e)" class="season-badge peak">Cao điểm</span>
          <span v-else-if="isInSeason(e)" class="season-badge">Đang mùa</span>
          <EntityCard :entity="e" />
          <small class="season-when">🗓️ {{ seasonText(e.season) }}</small>
        </div>
      </div>
    </section>
    <EmptyState v-else-if="data" icon="📅" title="Chưa có dữ liệu mùa" message="Chưa có mục nào gắn mùa cho tháng này. Dữ liệu mùa đang được bổ sung.">
      <template #actions>
        <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
        <NuxtLink to="/san-pham" class="btn btn-outline">Xem sản phẩm</NuxtLink>
      </template>
    </EmptyState>

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Tất cả sản phẩm</p></div>
        </NuxtLink>
        <NuxtLink to="/ocop" class="cross-card">
          <span class="cross-icon">⭐</span>
          <div><strong>OCOP</strong><p>Sản phẩm đạt chuẩn</p></div>
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
import { TYPE_META } from '~/composables/useConstants'

useReveal()
const { f: pc } = usePageContent('theo_mua')
const { relevanceScore, seasonText } = useSeason()

const month = ref(new Date().getMonth() + 1)

const WEDGE_TYPES = ['experience', 'product', 'dish']

const TYPE_DESC: Record<string, string> = {
  experience: 'Chèo xuồng, đạp xe, tát mương — trải nghiệm đúng mùa đẹp nhất.',
  product: 'Trái cây, nông sản chính vụ — tươi ngon, giá hợp lý nhất thời điểm này.',
  dish: 'Món ăn theo mùa — nguyên liệu tươi, đúng vị nhất trong năm.',
}

const { data, error: fetchError } = await useAsyncData('season-entities', () =>
  $fetch<{ entities: Entity[] }>('/api/entities?limit=300'),
)

const wedge = computed(() =>
  (data.value?.entities || []).filter((e: Entity) => WEDGE_TYPES.includes(e.type)),
)

function score(e: Entity) { return relevanceScore(e, String(month.value)) }
function isInSeason(e: Entity) { return (e.season?.months || []).includes(month.value) }
function isPeak(e: Entity) { return (e.season?.peak || []).includes(month.value) }

const ranked = computed(() =>
  wedge.value
    .filter((e: Entity) => score(e) >= 2)
    .sort((a: Entity, b: Entity) => score(b) - score(a)),
)
const inSeasonItems = computed(() => wedge.value.filter((e: Entity) => isInSeason(e)))
const peakCount = computed(() => wedge.value.filter((e: Entity) => isPeak(e)).length)
const peakItems = computed(() =>
  wedge.value.filter((e: Entity) => isPeak(e)).slice(0, 8)
)

const typeStats = computed(() =>
  WEDGE_TYPES
    .map(t => ({
      type: t,
      label: TYPE_META[t]?.label || t,
      count: inSeasonItems.value.filter((e: Entity) => e.type === t).length,
    }))
    .filter(s => s.count > 0)
)

const typeSections = computed(() =>
  WEDGE_TYPES
    .map(t => ({
      type: t,
      emoji: TYPE_META[t]?.emoji || '',
      label: TYPE_META[t]?.label || t,
      desc: TYPE_DESC[t] || '',
      items: ranked.value.filter((e: Entity) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
)

function countByMonth(m: number) {
  return wedge.value.filter((e: Entity) => (e.season?.months || []).includes(m)).length
}

useSeoMeta({
  title: () => pc('seo_title', `Tháng ${month.value}: đi đâu, ăn gì ở Vĩnh Long — vinhlong360`),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/theo-mua') }] })
</script>

<style scoped>
.month-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: var(--space-2); }
.season-item { position: relative; display: flex; flex-direction: column; }
.season-badge { position: absolute; top: var(--space-2); left: var(--space-2); z-index: 2; background: var(--overlay-dark); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: var(--text-on-dark, #fff); font-size: .72rem; font-weight: var(--weight-semibold); padding: 3px var(--space-3); border-radius: var(--radius-full); }
.season-badge.peak { background: var(--accent); color: var(--ink); font-weight: var(--weight-bold); }
.season-when { color: var(--muted); margin-top: var(--space-1); font-size: var(--text-xs); }
.b2b-note { background: rgba(46, 125, 91, .06); border: .5px solid rgba(46, 125, 91, .2); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--text-sm); margin: 0 0 var(--space-5); line-height: var(--leading-relaxed); }
.b2b-note a { color: var(--primary-fg); font-weight: var(--weight-semibold); }
.see-all-count { font-size: var(--text-sm); color: var(--muted); }

/* Dark mode */
.dark .season-badge { background: rgba(255,255,255,.12); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.dark .season-badge.peak { background: var(--accent); color: var(--ink); }
.dark .b2b-note { background: rgba(46, 125, 91, .08); border-color: rgba(46, 125, 91, .15); }
.dark .month-grid .quick-pick { background: var(--bg-alt); border-color: var(--line); }
.dark .month-grid .quick-pick:hover { border-color: rgba(255,255,255,.15); }
</style>
