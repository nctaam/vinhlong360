<template>
  <div class="grid" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
    <div v-for="i in count" :key="i" class="skeleton-card">
      <div class="sk-cover"></div>
      <div class="sk-body">
        <div class="sk-line sk-type"></div>
        <div class="sk-line sk-title"></div>
        <div class="sk-line sk-text"></div>
        <div class="sk-line sk-text short"></div>
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
.sk-cover { height: 160px; background: linear-gradient(90deg, var(--bg-warm, #f0ece2) 25%, var(--line, #e6e0d4) 50%, var(--bg-warm, #f0ece2) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-body { padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-2); }
.sk-line { border-radius: var(--radius-sm, 6px); background: linear-gradient(90deg, var(--bg-warm, #f0ece2) 25%, var(--line, #e6e0d4) 50%, var(--bg-warm, #f0ece2) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-type { width: 80px; height: 12px; }
.sk-title { width: 70%; height: 16px; }
.sk-text { width: 100%; height: 12px; }
.sk-text.short { width: 50%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
:root .dark .sk-cover,
:root .dark .sk-line {
  background: linear-gradient(90deg, var(--bg-alt) 25%, rgba(255,255,255,.06) 50%, var(--bg-alt) 75%);
  background-size: 200% 100%;
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-card { animation: none; }
  .sk-cover, .sk-line { animation: none; }
}
</style>
