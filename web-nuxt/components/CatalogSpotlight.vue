<template>
  <section v-if="pick" class="block reveal">
    <div class="cspot">
      <NuxtLink :to="`/dia-diem/${pick.id}`" class="cspot-visual" :style="{ backgroundImage: bg }" :aria-label="pick.name">
        <span v-if="region" class="cspot-region">📍 {{ region }}</span>
        <span class="cspot-icon" v-html="icon" aria-hidden="true" />
      </NuxtLink>
      <div class="cspot-body">
        <span class="cspot-kicker">{{ meta?.emoji }} {{ meta?.label }} · Nổi bật</span>
        <h2>{{ pick.name }}</h2>
        <div class="cspot-badges">
          <span v-if="isPeak" class="cspot-badge cspot-badge-peak">Đang mùa</span>
          <span v-else-if="isAllYear" class="cspot-badge cspot-badge-year">Quanh năm</span>
          <span v-if="relCount >= 3" class="cspot-badge cspot-badge-pop">{{ relCount }} liên kết</span>
        </div>
        <p v-if="pick.summary" class="cspot-sum">{{ pick.summary }}</p>
        <NuxtLink :to="`/dia-diem/${pick.id}`" class="btn btn-primary cspot-cta">Khám phá ngay →</NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// Spotlight magazine dùng-chung cho trang catalog (du-lịch/sản-phẩm…) — cùng "ngôn-ngữ"
// với spotlight trang chủ: panel THIẾT-KẾ (gradient mã-màu + motif + badge vùng), KHÔNG
// ô-ảnh-trống. Chọn entity có summary GIÀU nhất (deterministic, SSR-safe). Ẩn nếu không đủ.
import type { Entity } from '~/types'
import { TYPE_META, AREA_META } from '~/composables/useConstants'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import { inSeason, isYearRound } from '~/composables/useSeason'

const props = defineProps<{ items: Entity[] }>()

const pick = computed<any>(() => {
  const pool = (props.items || []).filter((e: any) => (e?.summary || '').trim().length >= 80)
  if (!pool.length) return null
  return pool.reduce((best: any, cur: any) =>
    (cur?.summary || '').length > (best?.summary || '').length ? cur : best
  )
})
const meta = computed(() => pick.value ? (TYPE_META[pick.value.type] || { emoji: '📍', label: pick.value.type, cat: 'place' }) : null)
const bg = computed(() => pick.value && meta.value ? generateCategoryPlaceholder(pick.value.id, meta.value.cat) : '')
const icon = computed(() => meta.value ? generateCategoryIcon(meta.value.cat) : '')
const region = computed(() => {
  const a = pick.value?.area || pick.value?.attributes?.area || pick.value?.attributes?.province
  if (!a) return ''
  const m = (AREA_META as Record<string, { name: string }>)[String(a)]
  return m ? m.name : String(a)
})

const currentMonth = String(new Date().getMonth() + 1)
const isPeak = computed(() => pick.value && inSeason(pick.value, currentMonth))
const isAllYear = computed(() => pick.value && isYearRound(pick.value?.season))
const relCount = computed(() => pick.value?.relationship_total || 0)
</script>

<style scoped>
.cspot {
  display: grid; grid-template-columns: 1.05fr 1fr; gap: var(--space-6);
  align-items: stretch; background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius-xl); overflow: hidden; box-shadow: var(--shadow-sm);
  contain: layout style paint;
}
@media (max-width: 760px) { .cspot { grid-template-columns: 1fr; } }
.cspot-visual {
  position: relative; min-height: 260px;
  background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; text-decoration: none; isolation: isolate;
}
@media (max-width: 760px) { .cspot-visual { min-height: 170px; } }
.cspot-visual::before {
  content: ""; position: absolute; inset: -18%; z-index: 0; pointer-events: none;
  background: radial-gradient(46% 46% at 34% 30%, rgba(255,255,255,.22) 0%, transparent 68%);
  animation: cspot-glow 13s ease-in-out infinite alternate;
  will-change: transform;
}
@keyframes cspot-glow { 0% { transform: translate3d(0,0,0) scale(1); } 100% { transform: translate3d(7%,5%,0) scale(1.12); } }
.cspot-region, .cspot-icon { position: relative; z-index: 1; }
.cspot-icon { width: 112px; height: 112px; opacity: .86; color: var(--text-on-dark, #fff); filter: drop-shadow(0 4px 14px rgba(0,0,0,.26)); }
@media (max-width: 760px) { .cspot-icon { width: 84px; height: 84px; } }
.cspot-icon :deep(svg) { width: 100%; height: 100%; display: block; }
.cspot-region {
  position: absolute; top: var(--space-4); left: var(--space-4);
  padding: var(--space-1) var(--space-3); background: rgba(0,0,0,.5); color: #fff;
  border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--weight-semibold);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
}
.cspot-body {
  padding: var(--space-8) var(--space-8) var(--space-8) 0;
  display: flex; flex-direction: column; justify-content: center; gap: var(--space-3); min-width: 0;
}
@media (max-width: 760px) { .cspot-body { padding: var(--space-5); } }
.cspot-kicker { font-size: var(--text-xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: .05em; color: var(--primary-fg-strong); }
.cspot-body h2 { margin: 0; font-size: clamp(1.4rem, 3vw, 2rem); line-height: var(--leading-snug); letter-spacing: -.01em; }
.cspot-sum { margin: 0; color: var(--text-muted); line-height: var(--leading-relaxed); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.cspot-badges { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.cspot-badge { font-size: var(--text-xs); font-weight: var(--weight-semibold); padding: var(--space-1) var(--space-2); border-radius: var(--radius-full); }
.cspot-badge-peak { background: rgba(239,68,68,.12); color: #dc2626; }
.cspot-badge-year { background: rgba(16,185,129,.12); color: #059669; }
.cspot-badge-pop { background: rgba(59,130,246,.1); color: #2563eb; }
.dark .cspot-badge-peak { background: rgba(239,68,68,.2); color: #fca5a5; }
.dark .cspot-badge-year { background: rgba(16,185,129,.2); color: #6ee7b7; }
.dark .cspot-badge-pop { background: rgba(59,130,246,.2); color: #93c5fd; }
.cspot-cta { align-self: flex-start; margin-top: var(--space-2); }
@media (prefers-reduced-motion: reduce) { .cspot-visual::before { animation: none; } }
</style>
