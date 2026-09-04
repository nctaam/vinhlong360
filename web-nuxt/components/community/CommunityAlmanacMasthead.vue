<template>
  <section class="almanac-masthead" aria-label="Cộng đồng vinhlong360">
    <p class="almanac-eyebrow">
      <span v-if="hasFreshPost" class="almanac-pulse" aria-hidden="true"></span>
      CỘNG ĐỒNG · SỔ TAY VĨNH LONG HÔM NAY · {{ todayLabel }}
    </p>
    <h1 class="almanac-title">{{ title }}</h1>
    <p v-if="stats" class="almanac-stats">
      <CountUp :value="stats.posts || 0" class="almanac-num" />&nbsp;CHUYỆN ĐÃ KỂ
      <span class="almanac-dot" aria-hidden="true">·</span>
      <CountUp :value="stats.reviews || 0" class="almanac-num" />&nbsp;ĐÁNH GIÁ THẬT
      <span class="almanac-dot" aria-hidden="true">·</span>
      <CountUp :value="stats.members || 0" class="almanac-num" />&nbsp;NGƯỜI VĨNH LONG
    </p>
    <div class="sediment-divider" aria-hidden="true"></div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  hasFreshPost: boolean
  todayLabel: string
  title: string
  stats: { posts: number; reviews: number; members: number } | null
}>()
</script>

<style scoped>
.almanac-masthead { padding-top: var(--space-2); padding-bottom: var(--space-5); }
.almanac-eyebrow {
  display: flex; align-items: center; gap: var(--space-2);
  margin: 0 0 var(--space-3);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--muted);
}
.almanac-pulse {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  background: var(--leaf-600);
  animation: almanac-pulse-once 1.6s var(--ease-out-expo) 1;
}
@keyframes almanac-pulse-once {
  0% { box-shadow: 0 0 0 0 rgba(var(--secondary-rgb), .5); }
  70% { box-shadow: 0 0 0 6px rgba(var(--secondary-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--secondary-rgb), 0); }
}
.dark .almanac-pulse { background: var(--secondary); }
.almanac-title {
  font-family: var(--font-editorial); font-weight: 600;
  font-size: var(--text-3xl); line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight); text-wrap: balance;
  margin: 0 0 var(--space-4); color: var(--ink);
  max-width: 42ch;
}
.almanac-stats {
  margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: .1em .5em;
  font-family: var(--font-sans); font-size: var(--text-sm); font-weight: 600;
  letter-spacing: .03em; text-transform: uppercase; color: var(--muted);
}
.almanac-num {
  font-family: var(--font-editorial); font-variant-numeric: oldstyle-nums tabular-nums;
  font-size: var(--text-lg); font-weight: 600; letter-spacing: 0; text-transform: none;
  color: var(--ink);
}
.almanac-dot { color: var(--clay-600); font-weight: 700; }
.dark .almanac-dot { color: var(--clay-400); }
.sediment-divider {
  position: relative; margin-top: var(--space-5); height: 7px;
  background:
    linear-gradient(90deg, transparent, var(--river-600) 26%, var(--river-600) 74%, transparent) top/100% 1px no-repeat,
    linear-gradient(90deg, transparent, var(--amber-600) 30%, var(--amber-600) 70%, transparent) center/100% 1px no-repeat,
    linear-gradient(90deg, transparent, var(--clay-600) 26%, var(--clay-600) 74%, transparent) bottom/100% 1.5px no-repeat;
  opacity: .5;
}
.dark .sediment-divider { opacity: .62; }
@media (prefers-reduced-motion: reduce) {
  .almanac-pulse { animation: none; box-shadow: none; }
}
@media (max-width: 640px) {
  .almanac-title { font-size: var(--text-2xl); }
  .almanac-stats { font-size: var(--text-xs); }
}
</style>
