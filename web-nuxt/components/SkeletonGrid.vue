<template>
  <div class="grid" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
    <div v-for="i in count" :key="i" class="skeleton-card">
      <div class="sk-cover"></div>
      <div class="sk-body">
        <div class="sk-line sk-type"></div>
        <div class="sk-line sk-title"></div>
        <div class="sk-rule" aria-hidden="true"></div>
        <div class="sk-line sk-text"></div>
        <div class="sk-line sk-text short"></div>
        <div class="sk-badges">
          <div class="sk-line sk-badge sk-badge-1"></div>
          <div class="sk-line sk-badge sk-badge-2"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ count?: number }>(), { count: 6 })
</script>

<style scoped>
.skeleton-card {
  background: var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius-lg, 16px);
  overflow: hidden;
  animation: skFadeIn .45s var(--ease-out-expo) both;
}
.skeleton-card:nth-child(1) { animation-delay: 0s; }
.skeleton-card:nth-child(2) { animation-delay: .06s; }
.skeleton-card:nth-child(3) { animation-delay: .12s; }
.skeleton-card:nth-child(4) { animation-delay: .18s; }
.skeleton-card:nth-child(5) { animation-delay: .24s; }
.skeleton-card:nth-child(6) { animation-delay: .3s; }
@keyframes skFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
/* Cover carries the same faint grain as the real Story Card's phù-sa placeholder
   (.cover-grain) — so the loading moment forecasts "editorial illustration",
   not a generic shimmering rectangle. */
.sk-cover { position: relative; height: 160px; background: linear-gradient(90deg, rgba(var(--primary-rgb),.08) 25%, rgba(var(--primary-rgb),.15) 50%, rgba(var(--primary-rgb),.08) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-cover::after {
  content: ""; position: absolute; inset: 0;
  background-image: var(--grain); background-size: 120px 120px; opacity: .05;
}
.sk-body { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-2); }
.sk-line { border-radius: var(--radius-sm, 6px); background: linear-gradient(90deg, var(--bg-warm, #f0ece2) 25%, var(--line, #e6e0d4) 50%, var(--bg-warm, #f0ece2) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-type { width: 80px; height: 10px; margin-bottom: 2px; }
.sk-title { width: 70%; height: 18px; }
/* Static tri-province rule — mirrors .card-rule exactly (river→amber→clay,
   26×2px). This is the card's constant design signature, not unknown data,
   so it doesn't shimmer like the text placeholders around it. */
.sk-rule { width: 26px; height: 2px; border-radius: 2px; margin: 3px 0 4px; background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%); }
.dark .sk-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.sk-text { width: 100%; height: 12px; }
.sk-text.short { width: 50%; }
/* Badge-cluster placeholders — mirror card's season/ocop badge row for better load anticipation. */
.sk-badges { display: flex; gap: var(--space-2); margin-top: var(--space-2); }
.sk-badge { height: 10px; border-radius: var(--radius-full, 999px); }
.sk-badge-1 { width: 60px; }
.sk-badge-2 { width: 50px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
:root .dark .sk-cover {
  background: linear-gradient(90deg, rgba(255,255,255,.08) 25%, rgba(255,255,255,.15) 50%, rgba(255,255,255,.08) 75%);
  background-size: 200% 100%;
}
:root .dark .sk-line {
  background: linear-gradient(90deg, var(--bg-alt) 25%, rgba(255,255,255,.1) 50%, var(--bg-alt) 75%);
  background-size: 200% 100%;
}
.dark .sk-cover::after { opacity: .08; }
@media (prefers-reduced-motion: reduce) {
  .skeleton-card { animation: none; }
  .sk-cover, .sk-line { animation: none; }
}
@media (forced-colors: active) {
  .skeleton-card { border: 1px solid CanvasText; }
  .sk-cover, .sk-line { background: Canvas; border: 1px solid GrayText; }
  .sk-cover::after { display: none; }
  .sk-rule { background: CanvasText; }
}
</style>
