<template>
  <div
    class="dossier-line-item"
    :class="`dossier-line-item--${emphasis}`"
    data-dossier-line="true"
    role="listitem"
  >
    <span class="dossier-line-item__label">{{ label }}</span>
    <NuxtLink
      v-if="href"
      class="dossier-line-item__value"
      :to="href"
      data-dossier-line="true"
    >
      {{ value }}
    </NuxtLink>
    <span v-else class="dossier-line-item__value">{{ value }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  value: string
  href?: string
  emphasis?: 'muted' | 'normal'
}>(), {
  href: undefined,
  emphasis: 'normal',
})
</script>
