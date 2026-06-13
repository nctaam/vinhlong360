<template>
  <NuxtLink :to="`/lich-trinh/${itinerary.id}`" class="card cat-itinerary">
    <div class="cover cat-itinerary">
      <CategoryIcon cat="itinerary" />
    </div>
    <div class="card-b">
      <span class="card-type">{{ areaEmoji }} {{ areaName }} · {{ itinerary.duration }}</span>
      <h3>{{ itinerary.title || itinerary.name }}</h3>
      <p class="summary">{{ itinerary.summary || itinerary.description || '' }}</p>
      <p class="place">{{ itinerary.stops?.length || 0 }} điểm dừng</p>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'

const props = defineProps<{
  itinerary: Record<string, any>
}>()

const areaMeta = computed(() => AREA_META[props.itinerary.area] || { emoji: '📍', name: props.itinerary.area })
const areaEmoji = computed(() => areaMeta.value.emoji)
const areaName = computed(() => areaMeta.value.name)
</script>
