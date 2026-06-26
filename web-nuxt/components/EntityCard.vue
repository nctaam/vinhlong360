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
      <h3 class="card-name">{{ entity.name }}</h3>
      <p class="summary">{{ cardSummary }}</p>
      <p v-if="placeName" class="place">{{ placeName }}</p>
      <div v-if="cardMeta" class="card-meta">
        <span v-if="cardMeta.price" class="cm-item">💰 {{ cardMeta.price }}</span>
        <span v-if="cardMeta.hours" class="cm-item">🕒 {{ cardMeta.hours }}</span>
      </div>
      <div v-if="ratingDisplay" class="card-rating">
        <span class="cr-stars">{{ ratingDisplay.stars }}</span>
        <span class="cr-score">{{ ratingDisplay.score }}</span>
        <span class="cr-count">({{ ratingDisplay.count }})</span>
      </div>
      <div v-if="amenityIcons.length" class="card-amenities" :aria-label="amenityIcons.map(a => a.label).join(', ') + (amenityExtra > 0 ? ` và ${amenityExtra} tiện ích khác` : '')">
        <span v-for="a in amenityIcons" :key="a.key" class="ca-icon" :title="a.label">{{ a.icon }}</span>
        <span v-if="amenityExtra > 0" class="ca-more" :title="`${amenityExtra} tiện ích khác`">+{{ amenityExtra }}</span>
      </div>
      <div class="badges">
        <span v-if="isNew" class="badge new-badge">Mới</span>
        <span v-if="isPeak" class="badge peak"><span class="peak-dot" aria-hidden="true"></span> Đang mùa {{ peakLabel }}</span>
        <span v-if="isYearRoundSeason" class="badge year">Quanh năm</span>
        <span v-else class="badge season">{{ seasonLabel }}</span>
        <span v-if="entity.attributes?.ocop" :class="['badge', 'ocop', { 'ocop-5': ocopStars === 5, 'ocop-4': ocopStars === 4, 'ocop-3': ocopStars === 3 }]">⭐ {{ entity.attributes.ocop }}</span>
      </div>
    </div>
  </NuxtLink>
</template>

<script lang="ts">
const AMENITY_ICONS: Record<string, { icon: string; label: string }> = {
  wifi: { icon: '📶', label: 'Wi-Fi' },
  free_entry: { icon: '🆓', label: 'Miễn phí' },
  kid_friendly: { icon: '👶', label: 'Trẻ em OK' },
  wheelchair: { icon: '♿', label: 'Xe lăn' },
  pet_friendly: { icon: '🐕', label: 'Thú cưng OK' },
  air_conditioned: { icon: '❄️', label: 'Máy lạnh' },
  restroom: { icon: '🚻', label: 'WC' },
  photography: { icon: '📸', label: 'Chụp ảnh OK' },
}
</script>

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
const allAmenities = computed(() => {
  const badges = props.entity.attributes?.amenity_badges
  if (!Array.isArray(badges) || !badges.length) return []
  return badges.map((k: string) => {
    const meta = AMENITY_ICONS[k]
    return meta ? { key: k, ...meta } : null
  }).filter(Boolean) as { key: string; icon: string; label: string }[]
})
const amenityIcons = computed(() => allAmenities.value.slice(0, 3))
const amenityExtra = computed(() => Math.max(0, allAmenities.value.length - 3))
const ocopStars = computed(() => parseInt(props.entity.attributes?.ocop) || 0)
const isNew = computed(() => {
  const u = props.entity.updatedAt
  if (!u) return false
  const diff = Date.now() - new Date(u).getTime()
  return diff > 0 && diff < 14 * 86400000
})
const peakLabel = computed(() => {
  const sf = props.seasonFilter
  if (!sf || sf === 'all') return ''
  if (sf === 'flood') return 'nước nổi'
  return `T${sf}`
})
const ratingDisplay = computed(() => {
  const a = props.entity.attributes
  const r = parseFloat(a?.rating)
  const c = parseInt(a?.review_count) || 0
  if (!r || r <= 0 || c < 1) return null
  const full = Math.floor(r)
  const half = r - full >= 0.5 ? '½' : ''
  return { stars: '★'.repeat(full) + half, score: r.toFixed(1), count: c }
})
</script>

<style scoped>
.card-name { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
:deep(.card) { contain: content; }
.card-amenities { display: flex; align-items: center; gap: 2px; margin-top: .25rem; }
.ca-icon { font-size: .7rem; opacity: .7; cursor: default; }
.ca-more { font-size: .65rem; color: var(--muted); font-weight: 600; margin-left: 1px; }
.card-rating { display: flex; align-items: center; gap: .25rem; font-size: .8rem; margin-top: .25rem; }
.cr-stars { color: var(--secondary, #d4a017); letter-spacing: -1px; }
.cr-score { font-weight: 600; color: var(--ink); }
.cr-count { color: var(--muted); font-size: .75rem; }
.badge.ocop-5 {
  background: linear-gradient(135deg, var(--secondary), var(--secondary-dark));
  color: var(--text-on-dark, #fff);
  border-color: transparent;
  box-shadow: 0 0 0 2px rgba(var(--secondary-rgb), .2);
}
.badge.ocop-4 {
  background: rgba(var(--secondary-rgb), .15);
  color: var(--secondary-dark);
}
.dark .badge.ocop-5 { box-shadow: 0 0 0 2px rgba(var(--secondary-rgb), .35); }
.dark .badge.ocop-4 { color: var(--secondary-fg); }
.badge.new-badge {
  background: rgba(52, 199, 89, .14);
  color: #1a8a3c;
  font-weight: 600;
}
.dark .badge.new-badge {
  background: rgba(52, 199, 89, .22);
  color: #34c759;
}
.peak-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  vertical-align: middle;
}
</style>
