<template>
  <NuxtLink :to="`/dia-diem/${entity.id}`" :class="['card', `cat-${typeMeta.cat}`]">
    <div v-if="coverImage && !imgError" class="cover cover-img">
      <NuxtImg v-if="isRemote" :src="coverImage" :alt="entity.name" loading="lazy" width="400" height="240" sizes="sm:100vw md:50vw lg:400px" decoding="async" @load="($event.target as HTMLElement)?.classList.add('loaded')" @error="imgError = true" />
      <img v-else :src="coverImage" :alt="entity.name" loading="lazy" width="400" height="240" decoding="async" @load="($event.target as HTMLElement)?.classList.add('loaded')" @error="imgError = true" />
      <span class="cover-tag" :class="`cat-${typeMeta.cat}`">{{ typeMeta.emoji }} {{ typeMeta.label }}</span>
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <div v-else class="cover cover-img cover-generated" :class="`cat-${typeMeta.cat}`" :style="{ backgroundImage: placeholderBg }">
      <span class="cover-svg-icon" v-html="placeholderSvg" />
      <span class="cover-tag" :class="`cat-${typeMeta.cat}`">{{ typeMeta.emoji }} {{ typeMeta.label }}</span>
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <div class="card-b">
      <span class="card-type">{{ typeMeta.label }}</span>
      <h3>{{ entity.name }}</h3>
      <p class="summary">{{ cardSummary }}</p>
      <p v-if="placeName" class="place">{{ placeName }}</p>
      <div v-if="cardMeta" class="card-meta">
        <span v-if="cardMeta.price" class="cm-item">💰 {{ cardMeta.price }}</span>
        <span v-if="cardMeta.hours" class="cm-item">🕒 {{ cardMeta.hours }}</span>
      </div>
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
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

const props = defineProps<{
  entity: Record<string, any>
  seasonFilter?: string | null
}>()

const imgError = ref(false)
const typeMeta = computed(() => TYPE_META[props.entity.type] || { emoji: '•', label: props.entity.type, cat: 'place' })
// Deterministic per-entity placeholder (no real photos exist yet) — seeded by id.
const placeholderBg = computed(() => generateCategoryPlaceholder(props.entity.id, typeMeta.value.cat))
const placeholderSvg = computed(() => generateCategoryIcon(typeMeta.value.cat))
const coverImage = computed(() => {
  const imgs = props.entity.images
  if (Array.isArray(imgs) && imgs.length > 0) return imgs[0]
  return null
})
const isRemote = computed(() => typeof coverImage.value === 'string' && /^https?:\/\//.test(coverImage.value))
const isYearRoundSeason = computed(() => !props.entity.season || isYearRound(props.entity.season))
const seasonLabel = computed(() => seasonText(props.entity.season))
const placeName = computed(() => props.entity.placeName || props.entity.place_name || '')
const isPeak = computed(() => props.seasonFilter && relevanceScore(props.entity, props.seasonFilter) === 4)
const cardSummary = computed(() => {
  const desc = props.entity.description
  if (desc && typeof desc === 'string') {
    const first = desc.split(/\n\s*\n/)[0]?.trim()
    if (first && first.length > 20) return first
  }
  return props.entity.summary || ''
})
const cardMeta = computed(() => {
  const a = props.entity.attributes
  if (!a) return null
  const t = props.entity.type
  if (t !== 'product' && t !== 'dish' && t !== 'experience') return null
  const price = a.price || a.fee || null
  const hours = a.hours || null
  return (price || hours) ? { price, hours } : null
})
</script>
