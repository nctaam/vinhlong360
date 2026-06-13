<template>
  <NuxtLink :to="`/khu-vuc/${areaKey}`" class="region-card">
    <AreaIllustration :area="areaKey" />
    <div class="rc-body">
      <h3>Khu vực {{ meta.name }}</h3>
      <p>{{ meta.blurb }}</p>
      <span class="rc-count">{{ count }} mục →</span>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

const props = defineProps<{
  areaKey: string
  count?: number
}>()

const meta = computed(() => AREA_META[props.areaKey] || { name: props.areaKey, emoji: '📍', blurb: '' })
const count = computed(() => props.count ?? 0)
</script>
