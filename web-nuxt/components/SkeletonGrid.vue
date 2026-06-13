<template>
  <div class="grid">
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
defineProps<{ count?: number }>()
</script>

<style scoped>
.skeleton-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.sk-cover { height: 96px; background: linear-gradient(90deg, #f0ece2 25%, #e6e0d4 50%, #f0ece2 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-body { padding: 14px 15px; display: flex; flex-direction: column; gap: 8px; }
.sk-line { border-radius: 6px; background: linear-gradient(90deg, #f0ece2 25%, #e6e0d4 50%, #f0ece2 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-type { width: 80px; height: 12px; }
.sk-title { width: 70%; height: 16px; }
.sk-text { width: 100%; height: 12px; }
.sk-text.short { width: 50%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
