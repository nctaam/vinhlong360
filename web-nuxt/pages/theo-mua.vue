<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Theo mùa' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-season">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" :key="seasonEmoji" aria-hidden="true">{{ seasonEmoji }}</span>
        <div>
          <h1>{{ pc('hero_title', 'Tháng ' + month + ' — đi đâu, ăn gì?') }}</h1>
          <p>{{ pc('hero_subtitle', heroSubtitle) }}</p>
        </div>
      </div>

      <!-- Signature: season moment indicator -->
      <div class="season-moment">
        <div class="season-ring" :class="'q-' + seasonQuarter.key" aria-hidden="true">
          <span class="season-ring-emoji">{{ seasonEmoji }}</span>
        </div>
        <div class="season-moment-text">
          <strong>Tháng {{ month }} — {{ seasonQuarter.tag }}</strong>
          <p>{{ seasonQuarter.note }}</p>
        </div>
        <div v-if="inSeasonItems.length" class="season-moment-pill">
          <span class="smp-num">{{ inSeasonItems.length }}</span>
          <span class="smp-label">mục đang mùa</span>
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
          :style="{ '--month-tone': monthTone(m) }"
          :aria-pressed="m === month"
          @click="month = m"
        >
          <span class="quick-pick-label">Tháng {{ m }}</span>
          <span class="quick-pick-count">{{ countByMonth(m) }} mục</span>
        </button>
      </div>
    </section>

    <EmptyState v-if="fetchError" icon="⚠️" tone="error" title="Không thể tải dữ liệu" message="Mạng có thể đang chập chờn. Thử tải lại nhé.">
      <template #actions>
        <button type="button" class="btn btn-outline" @click="refreshNuxtData('season-entities')">Thử lại</button>
      </template>
    </EmptyState>
    <ClientOnly>
      <SkeletonGrid v-if="!data && !fetchError" :count="12" />
      <template #fallback>
        <SkeletonGrid v-if="!data && !fetchError" :count="12" />
      </template>
    </ClientOnly>

    <!-- Peak highlights (honor row) -->
    <section v-if="peakItems.length" class="block reveal">
      <div class="seasonal-banner peak-banner">
        <span class="seasonal-banner-icon">🔥</span>
        <div>
          <strong>Cao điểm tháng {{ month }}</strong>
          <p>Những mục chính vụ, thời điểm ngon nhất — không nên bỏ lỡ.</p>
        </div>
      </div>
      <div class="scroll-row" role="region" aria-label="Cao điểm tháng này">
        <div
          v-for="(e, i) in peakItems" :key="e.id"
          class="season-item is-peak"
          :style="{ animationDelay: `${i * 50}ms` }"
        >
          <span class="season-badge peak">Cao điểm</span>
          <EntityCard :entity="e" />
        </div>
      </div>
    </section>

    <!-- Type sections -->
    <template v-for="(cat, ci) in typeSections" :key="cat.type">
      <div v-if="ci > 0" class="type-section-divider" aria-hidden="true" />
      <section class="block reveal">
        <div class="section-eyebrow">{{ cat.emoji }} {{ cat.eyebrow }}</div>
        <div class="section-head">
          <h2>{{ cat.emoji }} {{ cat.label }}</h2>
          <span class="see-all-count">{{ cat.items.length }} mục</span>
        </div>
        <p class="section-desc">{{ cat.desc }}</p>
        <div class="scroll-row" role="region" :aria-label="cat.label + ' đang mùa'">
          <div
            v-for="(e, i) in cat.items.slice(0, 8)" :key="e.id"
            class="season-item"
            :style="{ animationDelay: `${i * 50}ms` }"
          >
            <span v-if="isPeak(e)" class="season-badge peak">Cao điểm</span>
            <span v-else class="season-badge">Đang mùa</span>
            <EntityCard :entity="e" />
            <small class="season-when"><span aria-hidden="true">📅</span>{{ seasonText(e.season) }}</small>
          </div>
        </div>
      </section>
    </template>

    <!-- Per-type empty states (when data is loaded but a wedge type has nothing this month) -->
    <section v-if="data && emptyTypes.length" class="block reveal">
      <div class="empty-type-grid">
        <div v-for="t in emptyTypes" :key="t.type" class="empty-type-card">
          <span class="empty-type-icon" aria-hidden="true">{{ t.emoji }}</span>
          <strong>Chưa có {{ t.label.toLowerCase() }} vào mùa tháng {{ month }}</strong>
          <p>Dữ liệu đang được cập nhật. Thử chọn tháng khác để tìm mục phù hợp.</p>
        </div>
      </div>
    </section>

    <!-- B2B callout (§1.4: liên hệ/hỏi-giá only, no order form) -->
    <aside class="b2b-callout">
      <span class="b2b-callout-icon" aria-hidden="true">🤝</span>
      <div class="b2b-callout-text">
        Cần <strong>mua sỉ nông sản theo mùa</strong> hoặc kết nối HTX / nhà vườn?
        Liên hệ trực tiếp cơ sở ở mỗi mục.
      </div>
      <NuxtLink to="/lien-he" class="b2b-callout-link">Gửi yêu cầu <span aria-hidden="true">→</span></NuxtLink>
    </aside>

    <!-- Editorial -->
    <section class="page-article reveal">
      <h2>Khí hậu miền Tây và du lịch theo mùa</h2>
      <p>Vùng đồng bằng sông Cửu Long có khí hậu nhiệt đới gió mùa với hai mùa rõ rệt. <strong>Mùa khô</strong> (tháng 12–4) trời nắng ấm, ít mưa, nhiệt độ 25–32°C — đây là thời gian lý tưởng nhất để du lịch, đạp xe và tham quan làng nghề. <strong>Mùa mưa</strong> (tháng 5–11) có những cơn mưa rào buổi chiều nhưng sáng thường còn nắng đẹp, và đây lại là mùa trái cây rộ nhất.</p>

      <h2>Mùa nước nổi — trải nghiệm độc đáo</h2>
      <p>Từ tháng 8 đến tháng 11, nước từ thượng nguồn Mekong đổ về làm mực nước sông dâng cao, tràn vào đồng ruộng. Đây không phải thiên tai mà là nhịp sống tự nhiên mang phù sa màu mỡ cho vụ lúa kế tiếp. Mùa nước nổi mang đến những đặc sản mùa vụ không đâu có: cá linh non kho mía, bông điên điển xào tỏi, lẩu mắm bông súng, chuột đồng quay lu.</p>
      <p>Đi xuồng giữa đồng nước mênh mông, hái bông điên điển vàng rực hay tát mương bắt cá là trải nghiệm chỉ có trong vài tháng ngắn ngủi mỗi năm — và chỉ ở miền Tây.</p>

      <h2>Lịch mùa vụ tóm tắt</h2>
      <p><strong>Tháng 1–3:</strong> Dưa hấu, quýt, mùa khô đẹp trời. <strong>Tháng 4–5:</strong> Đầu mùa mưa, xoài, mít bắt đầu chín. <strong>Tháng 5–7:</strong> Cao điểm trái cây — sầu riêng, măng cụt, chôm chôm, vú sữa. <strong>Tháng 8–11:</strong> Mùa nước nổi, cá linh, bông điên điển. <strong>Tháng 12:</strong> Mùa khô trở lại, bưởi Năm Roi chín vàng, thời tiết mát mẻ nhất năm.</p>
    </section>

    <!-- Divider -->
    <div v-if="ranked.length" class="catalog-divider">
      <span class="catalog-divider-text">Tất cả đang mùa</span>
    </div>

    <!-- Full grid -->
    <section v-if="ranked.length" class="block reveal">
      <div class="grid">
        <div
          v-for="(e, i) in ranked" :key="e.id"
          class="season-item"
          :style="{ animationDelay: `${Math.min(i, 11) * 50}ms` }"
        >
          <span v-if="isPeak(e)" class="season-badge peak">Cao điểm</span>
          <span v-else-if="isInSeason(e)" class="season-badge">Đang mùa</span>
          <EntityCard :entity="e" />
          <small class="season-when"><span aria-hidden="true">📅</span>{{ seasonText(e.season) }}</small>
        </div>
      </div>
    </section>
    <EmptyState
      v-else-if="data"
      icon="📅"
      :title="`Chưa có dữ liệu mùa tháng ${month}`"
      message="Dữ liệu mùa đang được bổ sung cho tháng này. Những tháng khác có nội dung phong phú hơn nhé."
      hint="Chọn một tháng khác ở trên, hoặc khám phá theo chủ đề bên dưới."
    >
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

const TYPE_EYEBROW: Record<string, string> = {
  experience: 'Trải nghiệm',
  product: 'Nông sản',
  dish: 'Ẩm thực',
}

/* Signature: seasonal emoji keyed to the Mekong year rhythm.
   Generic seasonal mood — no fabricated official crop/harvest calendar (Track-H). */
const SEASON_EMOJIS = ['💧', '🌿', '🌿', '🌻', '🌻', '🌞', '🌞', '🌞', '🌾', '🌾', '💧', '💧']
const seasonEmoji = computed(() => SEASON_EMOJIS[month.value - 1] || '📅')

/* Mekong quarters → mood label + note (evocative, not factual claims). */
const seasonQuarter = computed(() => {
  const m = month.value
  if (m >= 1 && m <= 3) return { key: 'spring', tag: 'mùa xuân miệt vườn', note: 'Tiết trời mát mẻ, hợp đạp xe nhà vườn và chèo xuồng sông nước.' }
  if (m >= 4 && m <= 5) return { key: 'bloom', tag: 'đầu mùa nắng', note: 'Vườn cây rộn ràng vào vụ — thời điểm dạo chơi, ngắm cảnh dễ chịu.' }
  if (m >= 6 && m <= 8) return { key: 'summer', tag: 'cao điểm mùa hè', note: 'Nắng vàng rực rỡ, nhiều đặc sản vào chính vụ nhất trong năm.' }
  if (m >= 9 && m <= 10) return { key: 'harvest', tag: 'mùa thu hoạch', note: 'Đồng quê trĩu quả, hợp trải nghiệm miệt vườn và thưởng thức tại chỗ.' }
  return { key: 'flood', tag: 'mùa nước nổi', note: 'Sông nước mênh mang — mùa của những trải nghiệm đặc trưng miền Tây.' }
})

const heroSubtitle = computed(() =>
  `${seasonQuarter.value.note} Khám phá các mục đang mùa, ngon nhất ngay lúc này.`,
)

/* Month color tone for the picker accent (green growing / blue water). */
function monthTone(m: number) {
  if (m >= 1 && m <= 3) return 'var(--secondary)'        // mát mẻ / sinh trưởng
  if (m >= 4 && m <= 8) return 'var(--accent)'           // nắng / chính vụ
  return 'var(--tertiary)'                                // nước nổi
}

const { data, error: fetchError } = await useAsyncData('season-entities', () =>
  apiFetch<{ entities: Entity[]; total: number }>(`/api/entities?type=${WEDGE_TYPES.join(',')}&limit=500`),
)

const wedge = computed(() => data.value?.entities || [])

function score(e: Entity) { return relevanceScore(e, String(month.value)) }
function isInSeason(e: Entity) { return (e.season?.months || []).includes(month.value) }
function isPeak(e: Entity) { return (e.season?.peak || []).includes(month.value) }

const ranked = computed(() =>
  wedge.value
    .filter((e: Entity) => score(e) >= 2)
    .sort((a: Entity, b: Entity) => (score(b) || 0) - (score(a) || 0)),
)
const inSeasonItems = computed(() => wedge.value.filter((e: Entity) => isInSeason(e)))
const allPeakItems = computed(() => wedge.value.filter((e: Entity) => isPeak(e)))
const peakCount = computed(() => allPeakItems.value.length)
const peakItems = computed(() => allPeakItems.value.slice(0, 8))

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
      eyebrow: TYPE_EYEBROW[t] || TYPE_META[t]?.label || t,
      desc: TYPE_DESC[t] || '',
      items: ranked.value.filter((e: Entity) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
)

/* Designed empty-per-type: wedge types that have nothing in season this month. */
const emptyTypes = computed(() =>
  WEDGE_TYPES
    .filter(t => ranked.value.filter((e: Entity) => e.type === t).length === 0)
    .map(t => ({
      type: t,
      emoji: TYPE_META[t]?.emoji || '🌿',
      label: TYPE_META[t]?.label || t,
    }))
)

const monthCountMap = computed(() => {
  const counts = new Map<number, number>()
  for (const e of wedge.value) {
    for (const m of (e.season?.months || [])) {
      counts.set(m, (counts.get(m) || 0) + 1)
    }
  }
  return counts
})

function countByMonth(m: number) {
  return monthCountMap.value.get(m) || 0
}

useSeoMeta({
  title: () => pc('seo_title', `Tháng ${month.value}: đi đâu, ăn gì ở Vĩnh Long — vinhlong360`),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/theo-mua') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'CollectionPage',
      name: `Tháng ${month.value}: đi đâu, ăn gì ở Vĩnh Long`,
      description: `Những mục đang mùa, ngon nhất vào tháng ${month.value} — trái cây, nông sản, ẩm thực, trải nghiệm miệt vườn.`,
      url: canonicalUrl('/theo-mua'),
    }),
  }, {
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Theo mùa' },
      ],
    }),
  }],
}))
</script>

<style scoped>
.month-grid { position: relative; display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: var(--space-2); }
.month-grid .quick-pick { border-left: 2px solid color-mix(in srgb, var(--month-tone, var(--primary)) 55%, transparent); }
.month-grid .quick-pick.active {
  box-shadow: 0 2px 8px rgba(var(--primary-rgb), .28), inset 0 1px 0 rgba(255, 255, 255, .15);
}
.quick-pick-count { color: var(--muted); font-size: var(--text-xs); }

.season-item { position: relative; display: flex; flex-direction: column; }
/* Peak items in the honor row read a touch more premium */
.season-item.is-peak :deep(.card) { box-shadow: 0 0 0 1px rgba(var(--accent-rgb), .18), var(--shadow-sm); }
.season-item.is-peak:hover :deep(.card) { box-shadow: 0 0 0 1px rgba(var(--accent-rgb), .3), 0 14px 32px -16px rgba(var(--accent-rgb), .4); }

/* Signature: season moment indicator in hero */
.season-moment {
  position: relative; z-index: 1;
  display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-4);
  align-items: center;
  margin-top: var(--space-4); padding-top: var(--space-4);
  border-top: .5px solid rgba(var(--primary-rgb), .15);
}
.season-ring {
  width: 80px; height: 80px; border-radius: 50%;
  position: relative; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(var(--primary-rgb), .12);
}
.season-ring::after {
  content: ''; position: absolute; inset: 9px; border-radius: 50%;
  background: var(--card);
}
.season-ring-emoji { position: relative; z-index: 1; font-size: 2.2rem; line-height: 1; }
.season-ring.q-spring  { background: conic-gradient(var(--secondary), color-mix(in srgb, var(--secondary) 35%, transparent), var(--secondary)); }
.season-ring.q-bloom   { background: conic-gradient(var(--accent), var(--secondary), var(--accent)); }
.season-ring.q-summer  { background: conic-gradient(var(--accent), color-mix(in srgb, var(--accent) 35%, transparent), var(--accent)); }
.season-ring.q-harvest { background: conic-gradient(var(--accent), var(--tertiary), var(--accent)); }
.season-ring.q-flood   { background: conic-gradient(var(--tertiary), color-mix(in srgb, var(--tertiary) 35%, transparent), var(--tertiary)); }
.season-moment-text strong { display: block; font-size: var(--text-base); font-weight: var(--weight-semibold); color: var(--ink); }
.season-moment-text p { margin: var(--space-1) 0 0; font-size: var(--text-sm); color: var(--muted); line-height: var(--leading-relaxed); }
.season-moment-pill {
  display: inline-flex; flex-direction: column; align-items: center;
  padding: var(--space-2) var(--space-4); border-radius: var(--radius-md);
  background: rgba(var(--accent-rgb), .12); flex-shrink: 0;
}
.smp-num { font-size: 1.5rem; font-weight: var(--weight-bold); color: var(--ink); line-height: 1.1; }
.smp-label { font-size: var(--text-xs); color: var(--muted); white-space: nowrap; }

/* Signature: animated seasonal hero emoji */
.catalog-hero-icon { animation: seasonal-bob 2.8s var(--ease-out) infinite; will-change: transform; }
@keyframes seasonal-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }

/* Section eyebrow + dividers */
.section-eyebrow {
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--muted); margin-bottom: var(--space-1);
}
.type-section-divider {
  height: .5px; margin: var(--space-8) 0;
  background: linear-gradient(to right, transparent, var(--line), transparent);
}

/* Signature: promote + premium peak banner glow */
.peak-banner { position: relative; }
.peak-banner::after {
  content: ''; position: absolute; inset: -1px; border-radius: inherit;
  background: radial-gradient(circle at 50% 0%, rgba(var(--accent-rgb), .08), transparent 80%);
  z-index: -1; pointer-events: none;
}
.peak-banner .seasonal-banner-icon { animation: honor-spark 3s var(--ease-out) infinite; }
@keyframes honor-spark {
  0% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.12) rotate(180deg); }
  100% { transform: scale(1) rotate(360deg); }
}

/* Stagger on month change / reveal */
.scroll-row > .season-item,
.grid > .season-item { animation: seasonItemIn .5s var(--ease-out-expo) both; }
@keyframes seasonItemIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* Badges — gradient + gloss */
.season-badge {
  position: absolute; top: var(--space-2); left: var(--space-2); z-index: 2;
  background: linear-gradient(135deg, rgba(0, 0, 0, .65), rgba(0, 0, 0, .78));
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  color: var(--text-on-dark, #fff);
  font-size: .72rem; font-weight: var(--weight-semibold);
  padding: 3px var(--space-3); border-radius: var(--radius-full);
  box-shadow: 0 1px 3px rgba(0, 0, 0, .35), inset 0 1px 0 rgba(255, 255, 255, .08);
}
.season-badge.peak {
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  color: var(--ink); font-weight: var(--weight-semibold);
  box-shadow: 0 1px 3px rgba(var(--accent-rgb), .4), inset 0 1px 0 rgba(255, 255, 255, .25);
}
.season-item:hover .season-badge.peak { animation: season-badge-pulse 2.4s var(--ease-out) infinite; }
@keyframes season-badge-pulse {
  0%, 100% { box-shadow: 0 1px 3px rgba(var(--accent-rgb), .4), 0 0 0 0 rgba(var(--accent-rgb), 0); }
  50%      { box-shadow: 0 1px 3px rgba(var(--accent-rgb), .4), 0 0 0 4px rgba(var(--accent-rgb), .14); }
}

.season-when {
  color: var(--muted); margin-top: var(--space-1); font-size: var(--text-xs);
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-weight: var(--weight-medium); letter-spacing: .01em;
}

/* Per-type empty states */
.empty-type-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-4); }
.empty-type-card {
  text-align: center; padding: var(--space-6) var(--space-4);
  background: rgba(var(--secondary-rgb), .04);
  border: .5px dashed rgba(var(--secondary-rgb), .25);
  border-radius: var(--radius-lg);
}
.empty-type-icon { display: block; font-size: 2rem; margin-bottom: var(--space-2); opacity: .85; }
.empty-type-card strong { display: block; font-size: var(--text-sm); color: var(--ink); }
.empty-type-card p { margin: var(--space-2) 0 0; font-size: var(--text-xs); color: var(--muted); line-height: var(--leading-relaxed); }

/* B2B callout (§1.4: contact only, no order form) */
.b2b-callout {
  display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-4);
  align-items: center; position: relative; overflow: hidden;
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .06), transparent);
  border: .5px solid rgba(var(--secondary-rgb), .2);
  border-radius: var(--radius-lg); padding: var(--space-4) var(--space-5);
  margin: var(--space-6) 0;
}
.b2b-callout::before {
  content: ''; position: absolute; inset: -1px; z-index: -1;
  background: radial-gradient(circle at 100% 0%, rgba(var(--secondary-rgb), .08), transparent 70%);
}
.b2b-callout-icon { font-size: 1.6rem; flex-shrink: 0; }
.b2b-callout-text { font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.b2b-callout-text strong { color: var(--secondary-fg); }
.b2b-callout-link {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm);
  background: var(--secondary); color: var(--text-on-dark, #fff);
  font-weight: var(--weight-semibold); font-size: var(--text-sm); white-space: nowrap;
  min-height: 44px; transition: background .3s var(--ease-out), transform .3s var(--ease-out);
}
.b2b-callout-link:hover { background: var(--secondary-dark); transform: translateX(2px); }
.b2b-callout-link:focus-visible { outline: 2px solid var(--secondary); outline-offset: 3px; }

.see-all-count { font-size: var(--text-sm); color: var(--muted); }

/* ── Dark mode ─────────────────────────────── */
.dark .season-moment { border-top-color: rgba(255, 255, 255, .1); }
.dark .season-ring { box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .12); }
.dark .season-moment-pill { background: rgba(var(--accent-rgb), .18); }
.dark .season-badge {
  background: linear-gradient(135deg, rgba(0, 0, 0, .72), rgba(0, 0, 0, .82));
  color: var(--text-on-dark, #fff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, .5), inset 0 1px 0 rgba(255, 255, 255, .06);
}
.dark .season-badge.peak {
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(var(--accent-rgb), .6), 0 0 12px rgba(var(--accent-rgb), .25);
}
.dark .empty-type-card { background: rgba(var(--secondary-rgb), .07); border-color: rgba(var(--secondary-rgb), .22); }
.dark .b2b-callout { background: linear-gradient(135deg, rgba(var(--secondary-rgb), .1), transparent); border-color: rgba(var(--secondary-rgb), .25); }
.dark .month-grid .quick-pick { background: var(--bg-alt); border-color: var(--line); }
.dark .month-grid .quick-pick:hover { border-color: rgba(255, 255, 255, .15); }

/* ── Responsive ────────────────────────────── */
@media (max-width: 700px) {
  .season-moment { grid-template-columns: auto 1fr; }
  .season-ring { width: 64px; height: 64px; }
  .season-ring-emoji { font-size: 1.8rem; }
  .season-moment-pill { grid-column: 1 / -1; flex-direction: row; gap: var(--space-2); justify-content: center; }
}
@media (max-width: 640px) {
  .month-grid { grid-template-columns: repeat(3, 1fr); }
  .month-grid .quick-pick { padding: var(--space-5) var(--space-2); min-height: 48px; }
  .b2b-callout { grid-template-columns: auto 1fr; }
  .b2b-callout-link { grid-column: 1 / -1; justify-content: center; }
}
@media (max-width: 480px) {
  .season-badge { font-size: .65rem; padding: 2px var(--space-2); top: var(--space-1); left: var(--space-1); }
}

/* ── Reduced motion ────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .catalog-hero-icon { animation: none; }
  .peak-banner .seasonal-banner-icon { animation: none; }
  .scroll-row > .season-item,
  .grid > .season-item { animation: none; }
  .season-item:hover .season-badge.peak { animation: none; }
  .b2b-callout-link { transition: none; }
  .b2b-callout-link:hover { transform: none; }
}
</style>
