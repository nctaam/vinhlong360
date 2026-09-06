<template>
  <button
    v-if="show"
    type="button"
    class="new-post-thread-hint"
    @click="$emit('scroll')"
  >Vừa có chuyện mới — cuộn lên xem ↑</button>
</template>

<script setup lang="ts">
defineProps<{
  show: boolean
}>()

defineEmits<{
  (e: 'scroll'): void
}>()
</script>

<style scoped>
/* ── Vệt phù sa mới — hairline river→amber, click-to-scroll, session-only ── */
.new-post-thread-hint {
  display: block; width: 100%; margin: 0 0 var(--space-4); padding: var(--space-2) var(--space-3);
  border: none; border-radius: var(--radius-surface); cursor: pointer; text-align: center;
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: 600;
  letter-spacing: .02em; color: var(--muted);
  background:
    linear-gradient(90deg, transparent, var(--river-600) 15%, var(--amber-600) 85%, transparent) bottom/100% 1.5px no-repeat,
    rgba(var(--accent-rgb), .05);
  transition: color .25s var(--ease-out), background-color .25s var(--ease-out);
  animation: hint-settle .4s var(--ease-out-expo) both;
}
.new-post-thread-hint:hover { color: var(--ink); background-color: rgba(var(--accent-rgb), .09); }
.new-post-thread-hint:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
@keyframes hint-settle { from { opacity: 0; transform: translateY(-4px); } }
.dark .new-post-thread-hint { background-color: rgba(var(--accent-rgb), .08); }
.dark .new-post-thread-hint:hover { background-color: rgba(var(--accent-rgb), .13); }
@media (prefers-reduced-motion: reduce) {
  .new-post-thread-hint { animation: none; }
}
</style>
