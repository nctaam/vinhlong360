<template>
  <div class="skeleton-list" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
    <div v-for="i in count" :key="i" class="skl-row">
      <div class="skl-badge"></div>
      <div class="skl-body">
        <div class="skl-line skl-title"></div>
        <div class="skl-line skl-text"></div>
        <div class="skl-line skl-text short"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Row-shaped loading skeleton — mirrors a horizontal list (badge + text rows),
// so list views don't flash a tall card grid that collapses on load.
withDefaults(defineProps<{ count?: number }>(), { count: 5 })
</script>

<style scoped>
.skeleton-list { display: flex; flex-direction: column; gap: var(--space-3); }
.skl-row {
  display: flex; gap: var(--space-3); align-items: center;
  padding: var(--space-3);
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg);
  animation: sklFade .45s var(--ease-out-expo) both;
}
.skl-row:nth-child(1) { animation-delay: 0s; }
.skl-row:nth-child(2) { animation-delay: .06s; }
.skl-row:nth-child(3) { animation-delay: .12s; }
.skl-row:nth-child(4) { animation-delay: .18s; }
.skl-row:nth-child(5) { animation-delay: .24s; }
.skl-badge {
  width: 56px; height: 56px; flex-shrink: 0; border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--bg-warm, #f0ece2) 25%, var(--line, #e6e0d4) 50%, var(--bg-warm, #f0ece2) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite;
}
.skl-body { flex: 1; display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
.skl-line {
  height: 12px; border-radius: var(--radius-sm, 6px);
  background: linear-gradient(90deg, var(--bg-warm, #f0ece2) 25%, var(--line, #e6e0d4) 50%, var(--bg-warm, #f0ece2) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite;
}
.skl-title { width: 60%; height: 16px; }
.skl-text { width: 100%; }
.skl-text.short { width: 40%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
@keyframes sklFade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
:root .dark .skl-badge,
:root .dark .skl-line {
  background: linear-gradient(90deg, var(--bg-alt) 25%, rgba(255,255,255,.06) 50%, var(--bg-alt) 75%);
  background-size: 200% 100%;
}
@media (prefers-reduced-motion: reduce) {
  .skl-row, .skl-badge, .skl-line { animation: none; }
}
</style>
