<template>
  <NuxtLink :to="`/lich-trinh/${itinerary.id}`" class="card cat-itinerary">
    <div class="cover cover-img cat-itinerary">
      <img
        v-if="!imgErr"
        :src="coverSrc"
        :alt="itinerary.title || itinerary.name"
        loading="lazy" width="400" height="240" decoding="async"
        @error="imgErr = true"
      />
      <CategoryIcon v-else cat="itinerary" />
      <span class="cover-tag cat-itinerary">🗺️ Lịch trình</span>
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

const imgErr = ref(false)
// thumbnail theo vùng (tái dùng minh họa category) — đa dạng + hợp chủ đề từng tỉnh
const AREA_IMG: Record<string, string> = { 'vinh-long': 'place', 'ben-tre': 'nature', 'tra-vinh': 'history' }
const coverSrc = computed(() => `/img/cat/${AREA_IMG[props.itinerary.area] || 'itinerary'}.jpg`)

const areaMeta = computed(() => AREA_META[props.itinerary.area] || { emoji: '📍', name: props.itinerary.area })
const areaEmoji = computed(() => areaMeta.value.emoji)
const areaName = computed(() => areaMeta.value.name)
</script>
