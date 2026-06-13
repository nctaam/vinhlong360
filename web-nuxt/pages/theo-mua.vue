<template>
  <main class="season-page">
    <header class="season-head">
      <h1>Tháng này đi đâu, ăn gì?</h1>
      <p class="muted">Trải nghiệm, đặc sản &amp; món ăn <strong>đang vào mùa</strong> ở Vĩnh Long · Bến Tre · Trà Vinh.</p>
      <div class="month-chips" role="tablist" aria-label="Chọn tháng">
        <button
          v-for="m in 12" :key="m"
          role="tab" :aria-selected="m === month"
          :class="['month-chip', { active: m === month }]"
          @click="month = m"
        >T{{ m }}</button>
      </div>
    </header>

    <p class="season-count">
      <strong>{{ inSeasonItems.length }}</strong> mục đang vào mùa tháng {{ month }}
      <span v-if="peakCount"> · trong đó <strong>{{ peakCount }}</strong> cao điểm</span>
    </p>

    <!-- GĐ13.7: lead B2B nhẹ (chỉ liên hệ — KHÔNG đặt hàng on-site) -->
    <p class="b2b-note">
      🤝 Cần <strong>mua sỉ nông sản theo mùa</strong> hoặc kết nối HTX/nhà vườn? Liên hệ trực tiếp cơ sở ở mỗi mục,
      hoặc <NuxtLink to="/lien-he">gửi yêu cầu nguồn sỉ</NuxtLink>.
    </p>

    <ClientOnly>
      <SkeletonGrid v-if="!data" />
    </ClientOnly>

    <div v-if="ranked.length" class="card-grid">
      <div v-for="e in ranked" :key="e.id" class="season-item">
        <span v-if="isPeak(e)" class="season-badge peak">Cao điểm</span>
        <span v-else-if="isInSeason(e)" class="season-badge">Đang mùa</span>
        <EntityCard :entity="e" />
        <small class="season-when">🗓️ {{ seasonText(e.season) }}</small>
      </div>
    </div>
    <EmptyState v-else message="Chưa có mục nào gắn mùa cho tháng này. Dữ liệu mùa đang được bổ sung." />
  </main>
</template>

<script setup lang="ts">
const { relevanceScore, seasonText } = useSeason()
const { canonicalUrl } = useSeoHelpers()

// Tháng mặc định = tháng hiện tại (runtime browser/SSR; nhất quán trong 1 lần render).
const month = ref(new Date().getMonth() + 1)

const WEDGE_TYPES = ['experience', 'product', 'dish']

const { data } = await useAsyncData('season-entities', () =>
  $fetch<any>('/api/entities?limit=300'),
)

const wedge = computed(() =>
  (data.value?.entities || []).filter((e: any) => WEDGE_TYPES.includes(e.type)),
)

function score(e: any) { return relevanceScore(e, String(month.value)) }
function isInSeason(e: any) { return (e.season?.months || []).includes(month.value) }
function isPeak(e: any) { return (e.season?.peak || []).includes(month.value) }

// Chỉ hiện mục CÓ liên quan mùa: cao điểm(4)/đang mùa(3)/quanh năm(2).
// Bỏ mục không có dữ liệu mùa (score 1) và trái mùa (-1) — chúng thuộc /du-lich, /san-pham.
const ranked = computed(() =>
  wedge.value
    .filter((e: any) => score(e) >= 2)
    .sort((a: any, b: any) => score(b) - score(a)),
)
const inSeasonItems = computed(() => wedge.value.filter((e: any) => isInSeason(e)))
const peakCount = computed(() => wedge.value.filter((e: any) => isPeak(e)).length)

useSeoMeta({
  title: () => `Tháng ${month.value}: đi đâu, ăn gì ở Vĩnh Long — vinhlong360`,
  description: 'Trải nghiệm, đặc sản và món ăn đang vào mùa theo từng tháng tại Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: 'Bản đồ trải nghiệm theo mùa — vinhlong360',
  ogDescription: 'Tháng này miền Tây có gì? Khám phá đặc sản & trải nghiệm đúng mùa.',
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/theo-mua') }] })
</script>

<style scoped>
.season-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
.season-head h1 { font-size: 1.6rem; }
.muted { color: var(--muted, #888); }
.month-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 16px 0; }
.month-chip { padding: 6px 12px; border: 1px solid rgba(0,0,0,.12); border-radius: 999px; background: var(--surface, #fff); cursor: pointer; font-size: .9rem; }
.month-chip.active { background: var(--primary, #9C3D22); color: #fff; border-color: var(--primary, #9C3D22); }
.season-count { color: var(--muted, #666); margin: 8px 0 12px; }
.b2b-note { background: #f0f9f0; border: 1px solid #cce8cc; border-radius: 8px; padding: 10px 12px; font-size: .88rem; margin: 0 0 20px; }
.b2b-note a { color: var(--primary, #9C3D22); }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.season-item { position: relative; display: flex; flex-direction: column; }
.season-badge { position: absolute; top: 8px; left: 8px; z-index: 2; background: rgba(0,0,0,.6); color: #fff; font-size: .72rem; padding: 2px 8px; border-radius: 999px; }
.season-badge.peak { background: var(--accent, #E8A33D); color: #1a1a1a; font-weight: 600; }
.season-when { color: var(--muted, #888); margin-top: 4px; }
</style>
