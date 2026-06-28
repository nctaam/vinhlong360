<template>
  <div class="review-stats">
    <div class="reviews-header">
      <h2>Đánh giá cộng đồng</h2>
      <div v-if="rating.count" class="reviews-summary">
        <span class="star-rating-inline" role="img" :aria-label="`${rating.avg} trên 5 sao`">
          <span v-for="s in 5" :key="s" class="star" :class="{ active: s <= Math.round(rating.avg) }" aria-hidden="true">★</span>
        </span>
        <strong>{{ rating.avg }}</strong>
        <span class="review-count">({{ rating.count }} đánh giá)</span>
      </div>
    </div>

    <div v-if="rating.count && hasReviews" class="er-distribution" aria-label="Phân bố đánh giá">
      <div v-for="star in 5" :key="star" class="er-dist-row">
        <span class="er-dist-label">{{ 6 - star }}★</span>
        <div class="er-dist-track">
          <div class="er-dist-fill" :style="{ width: distPercent(6 - star) + '%' }" />
        </div>
        <span class="er-dist-count">{{ distCount(6 - star) }}</span>
      </div>
    </div>

    <div v-if="rating.count" class="er-categories">
      <div v-for="cat in REVIEW_CATEGORIES" :key="cat.key" class="er-cat-item">
        <span class="er-cat-label">{{ cat.label }}</span>
        <div class="er-cat-track"><div class="er-cat-fill er-cat-placeholder" /></div>
        <span class="er-cat-score">—</span>
      </div>
      <p class="er-cat-hint">Sắp có đánh giá chi tiết theo từng chiều</p>
    </div>

    <div v-if="mentionChips.length" class="er-mentions">
      <h3 class="er-mentions-title">Mọi người hay nhắc đến</h3>
      <FilterChips :filters="mentionChips" v-model="selectedMentions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Review } from '~/types'

const REVIEW_CATEGORIES = [
  { key: 'atmosphere', label: 'Không khí' },
  { key: 'quality', label: 'Chất lượng' },
  { key: 'value', label: 'Giá trị' },
  { key: 'service', label: 'Phục vụ' },
]

const props = defineProps<{
  rating: { avg: number; count: number }
  reviews: Review[]
}>()

const selectedMentions = defineModel<string[]>('selectedMentions', { default: () => [] })
const hasReviews = computed(() => props.reviews.length > 0)

const ratingDistribution = computed(() => {
  const counts = [0, 0, 0, 0, 0]
  for (const r of props.reviews) {
    const s = Math.round(r.rating || 0)
    if (s >= 1 && s <= 5) counts[s - 1]++
  }
  return counts
})
const maxDistCount = computed(() => Math.max(1, ...ratingDistribution.value))
function distCount(star: number) { return ratingDistribution.value[star - 1] || 0 }
function distPercent(star: number) { return (distCount(star) / maxDistCount.value) * 100 }

const STOP_WORDS = new Set(['và', 'là', 'của', 'cho', 'với', 'được', 'này', 'đã', 'có', 'không', 'rất', 'các', 'một', 'những', 'trong', 'ở', 'tại', 'cũng', 'nhưng', 'nên', 'thì', 'mà'])
const mentionChips = computed(() => {
  const freq = new Map<string, number>()
  for (const r of props.reviews) {
    const text = (r.content || '').toLowerCase()
    const words = text.split(/[\s,.!?;:()]+/).filter((w: string) => w.length >= 2 && !STOP_WORDS.has(w))
    const seen = new Set<string>()
    for (const w of words) {
      if (!seen.has(w)) { seen.add(w); freq.set(w, (freq.get(w) || 0) + 1) }
    }
  }
  return [...freq.entries()]
    .filter(([, c]) => c >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([word, count]) => ({ key: word, label: word, count }))
})
</script>

<style scoped>
.er-distribution {
  display: flex; flex-direction: column;
  gap: var(--space-1h, 6px); margin-bottom: var(--space-5); max-width: 320px;
}
.er-dist-row { display: grid; grid-template-columns: 28px 1fr 28px; align-items: center; gap: var(--space-2); }
.er-dist-label { font-size: var(--text-xs); font-weight: var(--weight-medium, 500); color: var(--muted); text-align: right; }
.er-dist-track { height: 8px; border-radius: 4px; background: var(--bg-warm, var(--bg-alt)); overflow: hidden; }
.er-dist-fill { height: 100%; border-radius: 4px; background: var(--secondary); transition: width 400ms var(--ease-out, ease); min-width: 2px; }
.er-dist-count { font-size: var(--text-xs); color: var(--muted); font-variant-numeric: tabular-nums; }

.er-categories { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); margin-bottom: var(--space-5); max-width: 400px; }
.er-cat-item { display: flex; flex-direction: column; gap: var(--space-1); }
.er-cat-label { font-size: var(--text-xs); font-weight: var(--weight-medium, 500); color: var(--ink); }
.er-cat-track { height: 6px; border-radius: 3px; background: var(--bg-warm, var(--bg-alt)); overflow: hidden; }
.er-cat-fill { height: 100%; border-radius: 3px; background: var(--secondary); }
.er-cat-placeholder { width: 0%; }
.er-cat-score { font-size: var(--text-xs); color: var(--muted); }
.er-cat-hint { grid-column: 1 / -1; font-size: var(--text-xs); color: var(--muted); font-style: italic; margin: 0; }

.er-mentions { margin-bottom: var(--space-5); }
.er-mentions-title { font-size: var(--text-sm); font-weight: var(--weight-semibold, 600); color: var(--ink); margin: 0 0 var(--space-2); }
</style>
