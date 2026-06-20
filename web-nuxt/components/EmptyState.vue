<template>
  <div class="empty-state" :role="tone === 'error' ? 'alert' : 'status'">
    <span v-if="icon" class="empty-icon" aria-hidden="true">{{ icon }}</span>
    <svg v-else viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="empty-illust">
      <circle cx="100" cy="70" r="50" fill="var(--bg-warm)" />
      <circle cx="100" cy="70" r="35" fill="var(--bg)" />
      <circle cx="90" cy="65" r="20" stroke="var(--line)" stroke-width="4" fill="none" />
      <line x1="105" y1="80" x2="125" y2="100" stroke="var(--line)" stroke-width="5" stroke-linecap="round" />
      <g fill="var(--accent)" opacity=".5">
        <path d="M140 35 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" />
        <path d="M55 30 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" />
        <path d="M150 75 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
      </g>
    </svg>
    <h3 v-if="title" class="empty-title">{{ title }}</h3>
    <p class="empty-text">{{ message }}</p>
    <div v-if="$slots.actions" class="empty-actions">
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message?: string
  icon?: string
  title?: string
  tone?: 'empty' | 'error'
}>()
</script>

<style scoped>
.empty-state { animation: emptyIn .5s var(--ease-spring-gentle); }
@keyframes emptyIn { from { opacity: 0; transform: translateY(12px) scale(.96); } }
.empty-icon { display: block; transition: transform .4s var(--ease-spring-gentle); }
.empty-state:hover .empty-icon { transform: scale(1.1) rotate(-4deg); }
.empty-illust { transition: transform .4s var(--ease-spring-gentle); }
.empty-state:hover .empty-illust { transform: scale(1.04); }
@media (prefers-reduced-motion: reduce) {
  .empty-state { animation: none; opacity: 1; transform: none; }
  .empty-icon, .empty-illust { transition: none; }
  .empty-state:hover .empty-icon { transform: none; }
  .empty-state:hover .empty-illust { transform: none; }
}
</style>
