<template>
  <svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg" class="avatar-placeholder" aria-hidden="true">
    <rect width="80" height="80" rx="40" fill="var(--primary-light, #c76a4e)" />
    <circle cx="40" cy="30" r="14" fill="rgba(255,255,255,.35)" />
    <ellipse cx="40" cy="68" rx="22" ry="18" fill="rgba(255,255,255,.25)" />
    <text v-if="initial" x="40" y="38" text-anchor="middle" fill="#fff" font-size="28" font-weight="800" font-family="system-ui">{{ initial }}</text>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ initial?: string }>()
</script>

<style scoped>
.avatar-placeholder { width: 100%; height: 100%; }
</style>
