<template>
  <NuxtLink :to="`/lich-trinh/${itinerary.id}`" class="card cat-itinerary">
    <div
      v-if="coverSrc && !imgErr"
      class="cover cover-img cat-itinerary"
    >
      <img
        :src="coverSrc"
        :alt="itinerary.title || itinerary.name"
        loading="lazy" width="400" height="240" decoding="async"
        @load="($event.target as HTMLElement)?.classList.add('loaded')"
        @error="imgErr = true"
      />
      <span class="cover-tag cat-itinerary">🗺️ Lịch trình</span>
    </div>
    <div
      v-else
      class="cover cover-img cover-generated cat-itinerary"
      :style="{ backgroundImage: placeholderBg }"
    >
      <span class="cover-svg-icon" v-html="placeholderSvg" />
      <span class="cover-tag cat-itinerary">🗺️ Lịch trình</span>
    </div>
    <div class="card-b">
      <span class="card-type">{{ areaEmoji }} {{ areaName }}</span>
      <h3>{{ itinerary.title || itinerary.name }}</h3>
      <div class="itinerary-badge-row">
        <span v-if="itinerary.duration" class="itinerary-duration-badge">🕐 {{ itinerary.duration }}</span>
        <span class="itinerary-stops-badge">🗺️ {{ stopCount }} điểm dừng</span>
      </div>
      <p class="summary">{{ itinerary.summary || itinerary.description || '' }}</p>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

const props = defineProps<{
  itinerary: Record<string, any>
}>()

const imgErr = ref(false)
// thumbnail theo vùng (tái dùng minh họa category) — đa dạng + hợp chủ đề từng tỉnh
const AREA_IMG: Record<string, string> = { 'vinh-long': 'place', 'ben-tre': 'nature', 'tra-vinh': 'history' }
const coverSrc = computed(() => `/img/cat/${AREA_IMG[props.itinerary.area] || 'itinerary'}.jpg`)
// Deterministic per-itinerary placeholder fallback — seeded by id.
const placeholderBg = computed(() => generateCategoryPlaceholder(props.itinerary.id, 'itinerary'))
const placeholderSvg = computed(() => generateCategoryIcon('itinerary'))

const areaMeta = computed(() => AREA_META[props.itinerary.area] || { emoji: '📍', name: props.itinerary.area })
const areaEmoji = computed(() => areaMeta.value.emoji)
const areaName = computed(() => areaMeta.value.name)
// stop count drives the curated-trip indicator badge (duration + stops)
const stopCount = computed(() => props.itinerary.stops?.length ?? props.itinerary.days?.reduce((n: number, d: any) => n + (d.stops?.length || 0), 0) ?? 0)
</script>
