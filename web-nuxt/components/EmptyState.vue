<template>
  <div class="empty-state">
    <svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="empty-illust">
      <circle cx="100" cy="70" r="50" fill="var(--bg-warm)" />
      <circle cx="100" cy="70" r="35" fill="var(--bg)" />
      <!-- Magnifying glass -->
      <circle cx="90" cy="65" r="20" stroke="var(--line)" stroke-width="4" fill="none" />
      <line x1="105" y1="80" x2="125" y2="100" stroke="var(--line)" stroke-width="5" stroke-linecap="round" />
      <!-- Sparkles -->
      <g fill="var(--accent)" opacity=".5">
        <path d="M140 35 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" />
        <path d="M55 30 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" />
        <path d="M150 75 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" />
      </g>
    </svg>
    <p class="empty-text">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ message?: string }>()
</script>

<style scoped>
.empty-state { text-align: center; padding: 40px 20px; }
.empty-illust { width: 160px; height: auto; margin: 0 auto 16px; display: block; }
.empty-text { color: var(--muted); font-size: 1rem; margin: 0; }
</style>
