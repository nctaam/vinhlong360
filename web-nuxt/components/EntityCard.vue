<template>
  <NuxtLink :to="`/dia-diem/${entity.id}`" :class="['card', `cat-${typeMeta.cat}`]">
    <div v-if="coverImage && !imgError" class="cover cover-img">
      <img :src="coverImage" :alt="entity.name" loading="lazy" width="400" height="240" decoding="async" @error="imgError = true" />
      <span class="cover-tag" :class="`cat-${typeMeta.cat}`">{{ typeMeta.emoji }} {{ typeMeta.label }}</span>
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <div v-else :class="['cover', `cat-${typeMeta.cat}`]">
      <CategoryIcon :cat="typeMeta.cat" />
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <div class="card-b">
      <span class="card-type">{{ typeMeta.label }}</span>
      <h3>{{ entity.name }}</h3>
      <p class="summary">{{ entity.summary || '' }}</p>
      <p v-if="placeName" class="place">{{ placeName }}</p>
      <div class="badges">
        <span v-if="isPeak" class="badge peak">🔥 Đang rộ</span>
        <span v-if="isYearRoundSeason" class="badge year">Quanh năm</span>
        <span v-else class="badge season">{{ seasonLabel }}</span>
        <span v-if="entity.attributes?.ocop" class="badge ocop">⭐ {{ entity.attributes.ocop }}</span>
      </div>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
import { isYearRound, seasonText, relevanceScore } from '~/composables/useSeason'

const props = defineProps<{
  entity: Record<string, any>
  seasonFilter?: string | null
}>()

const imgError = ref(false)
const typeMeta = computed(() => TYPE_META[props.entity.type] || { emoji: '•', label: props.entity.type, cat: 'place' })
const coverImage = computed(() => {
  const imgs = props.entity.images
  if (Array.isArray(imgs) && imgs.length > 0) return imgs[0]
  return null
})
const isYearRoundSeason = computed(() => !props.entity.season || isYearRound(props.entity.season))
const seasonLabel = computed(() => seasonText(props.entity.season))
const placeName = computed(() => props.entity.placeName || props.entity.place_name || '')
const isPeak = computed(() => props.seasonFilter && relevanceScore(props.entity, props.seasonFilter) === 4)
</script>
