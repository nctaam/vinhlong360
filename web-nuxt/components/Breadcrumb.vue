<template>
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <ol>
      <li v-for="(item, i) in items" :key="i">
        <NuxtLink v-if="item.to" :to="item.to">{{ item.label }}</NuxtLink>
        <span v-else aria-current="page">{{ item.label }}</span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
defineProps<{
  items: Array<{ label: string; to?: string }>
}>()
</script>

<style scoped>
.breadcrumb ol { display: flex; flex-wrap: wrap; gap: 0; list-style: none; margin: 0 0 12px; padding: 0; font-size: .84rem; }
.breadcrumb li + li::before { content: "›"; margin: 0 8px; color: var(--muted); }
.breadcrumb a { color: var(--primary); text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb span { color: var(--muted); }
</style>
