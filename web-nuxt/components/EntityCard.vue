<template>
  <article :class="['card', `cat-${typeMeta.cat}`]">
    <div v-if="coverImage && !imgError" class="cover cover-img">
      <NuxtLink :to="cardPath" class="card-cover-link" :aria-label="`Xem ${entity.name}`">
        <NuxtImg v-if="isRemote" :src="allImages[activeSlide]" :alt="entity.name" :key="allImages[activeSlide]" loading="lazy" width="400" height="267" sizes="sm:100vw md:50vw lg:400px" decoding="async" @load="($event.target as HTMLElement)?.classList.add('loaded')" @error="imgError = true" />
        <img v-else :src="allImages[activeSlide]" :alt="entity.name" :key="allImages[activeSlide]" loading="lazy" width="400" height="267" decoding="async" @load="($event.target as HTMLElement)?.classList.add('loaded')" @error="imgError = true" />
        <span class="cover-tag cover-dateline" :class="`cat-${typeMeta.cat}`">{{ dateline }}</span>
      </NuxtLink>
      <template v-if="allImages.length > 1">
        <button v-if="activeSlide > 0" type="button" class="card-arrow card-arrow-prev" aria-label="Ảnh trước" @click.prevent="activeSlide--">‹</button>
        <button v-if="activeSlide < allImages.length - 1" type="button" class="card-arrow card-arrow-next" aria-label="Ảnh sau" @click.prevent="activeSlide++">›</button>
        <div class="card-dots" aria-hidden="true">
          <span v-for="(_, i) in allImages.slice(0, 5)" :key="i" :class="['card-dot', { active: i === activeSlide }]" />
        </div>
      </template>
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <div v-else class="cover cover-img cover-generated" :class="`cat-${typeMeta.cat}`" :style="{ backgroundImage: placeholderBg }">
      <span class="cover-grain" aria-hidden="true"></span>
      <NuxtLink :to="cardPath" class="card-cover-link" :aria-label="`Xem ${entity.name}`">
        <span class="cover-svg-icon" v-html="placeholderSvg" />
        <span class="cover-tag cover-dateline" :class="`cat-${typeMeta.cat}`">{{ dateline }}</span>
      </NuxtLink>
      <ClientOnly><SaveButton class="card-save" :entity="entity" size="sm" /></ClientOnly>
    </div>
    <NuxtLink :to="cardPath" class="card-b card-body-link">
      <span class="card-dateline">{{ dateline }}</span>
      <h3 class="card-name">{{ entity.name }}</h3>
      <span class="card-rule" aria-hidden="true"></span>
      <p class="summary card-teaser">{{ storyTeaser }}</p>
      <p v-if="placeName" class="place">{{ placeName }}</p>
      <div v-if="cardMeta" class="card-meta">
        <span v-if="cardMeta.price" class="cm-item"><IconLine name="tag" /> {{ cardMeta.price }}</span>
        <span v-if="cardMeta.hours" class="cm-item"><IconLine name="clock" /> {{ cardMeta.hours }}</span>
      </div>
      <div v-if="ratingDisplay" class="card-rating">
        <span class="cr-stars">{{ ratingDisplay.stars }}</span>
        <span class="cr-score">{{ ratingDisplay.score }}</span>
        <span class="cr-count">({{ ratingDisplay.count }})</span>
      </div>
      <div v-if="amenityIcons.length" class="card-amenities" :aria-label="amenityIcons.map(a => a.label).join(', ') + (amenityExtra > 0 ? ` và ${amenityExtra} tiện ích khác` : '')">
        <span v-for="a in amenityIcons" :key="a.key" class="ca-icon" :title="a.label" aria-hidden="true">{{ a.icon }}</span>
        <span v-if="amenityExtra > 0" class="ca-more" :title="`${amenityExtra} tiện ích khác`">+{{ amenityExtra }}</span>
      </div>
      <div class="badges">
        <span v-if="isNew" class="badge new-badge">Mới</span>
        <span v-if="isPeak" class="badge peak"><span class="peak-dot" aria-hidden="true"></span> Đang mùa {{ peakLabel }}</span>
        <span v-if="isYearRoundSeason" class="badge year">Quanh năm</span>
        <span v-else class="badge season">{{ seasonLabel }}</span>
        <span v-if="entity.attributes?.ocop" :class="['badge', 'ocop', { 'ocop-5': ocopStars === 5, 'ocop-4': ocopStars === 4, 'ocop-3': ocopStars === 3 }]"><IconLine name="star" /> {{ entity.attributes.ocop }}</span>
      </div>
    </NuxtLink>
  </article>
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
import { entityStoryTeaser, entityDateline } from '~/composables/useEntityStory'

const props = defineProps<{
  entity: Record<string, any>
  seasonFilter?: string | null
}>()

const imgError = ref(false)
const activeSlide = ref(0)
const cardPath = computed(() => entityPath(props.entity.id))
const typeMeta = computed(() => TYPE_META[props.entity.type] || { emoji: '•', label: props.entity.type, cat: 'place' })
const allImages = computed(() => {
  const imgs = props.entity.images
  return Array.isArray(imgs) && imgs.length ? imgs : coverImage.value ? [coverImage.value] : []
})
// Deterministic per-entity placeholder (no real photos exist yet) — seeded by id.
const placeholderBg = computed(() => generateCategoryPlaceholder(props.entity.id, typeMeta.value.cat))
const placeholderSvg = computed(() => generateCategoryIcon(typeMeta.value.cat))
const coverImage = computed(() => {
  const imgs = props.entity.images
  if (Array.isArray(imgs) && imgs.length > 0) return imgs[0]
  return null
})
const isRemote = computed(() => typeof coverImage.value === 'string' && isRemoteUrl(coverImage.value))
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
const storyTeaser = computed(() => entityStoryTeaser(props.entity) || cardSummary.value)
const dateline = computed(() => entityDateline(props.entity, typeMeta.value.label))
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
/* 3:2 aspect ratio for card images */
.cover-img { aspect-ratio: 3 / 2; height: auto; }
.card-cover-link {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: block;
  color: inherit;
  text-decoration: none;
}
.card-cover-link:focus-visible,
.card-body-link:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: -2px;
}
.card-body-link {
  color: inherit;
  text-decoration: none;
}
/* Heart pop animation */
@keyframes heart-pop {
  0% { transform: scale(1); }
  50% { transform: scale(1.25); }
  100% { transform: scale(1); }
}
.card-save :deep(.save-active) { animation: heart-pop .3s; }
@media (prefers-reduced-motion: reduce) { .card-save :deep(.save-active) { animation: none; } }
/* Carousel arrows */
.card-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(var(--white-rgb), 0.9);
  color: var(--ink-900);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-spring-gentle);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(var(--black-rgb), 0.15);
}
.card-arrow-prev { left: var(--space-2); }
.card-arrow-next { right: var(--space-2); }
.card-arrow:hover { transform: translateY(-50%) scale(1.1); }
.card-arrow:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; opacity: 1; }
:deep(.card:hover) .card-arrow { opacity: 1; }
/* Carousel dots */
.card-dots {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: var(--space-1);
  z-index: 3;
}
.card-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(var(--white-rgb), 0.6);
  transition: background 200ms var(--ease-out), transform 200ms var(--ease-spring-gentle);
}
.card-dot.active {
  background: var(--text-on-dark, var(--white));
  transform: scale(1.3);
}
.card-amenities { display: none; }
/* ── Story Card (Wave 1 keystone) — editorial treatment on every grid card ── */
.card-type { display: none; }
.card-name { font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em; }
/* dateline eyebrow — small-caps, hairline accent, NOT a solid pill */
.card-dateline {
  display: inline-block; margin-bottom: 2px;
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
/* the on-cover dateline stays legible on imagery — keep the readable chip form there */
.cover-dateline { text-transform: uppercase; letter-spacing: .08em; }
/* tri-province "sediment" rule between name and teaser (card-scale sediment tick) */
.card-rule {
  display: block; width: 26px; height: 2px; border-radius: 2px; margin: 5px 0 6px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .card-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.card-teaser { color: var(--muted); }
/* grain overlay turns the flat placeholder gradient into an intentional illustration */
.cover-grain {
  position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .06;
}
.dark .cover-grain { opacity: .09; }
.ca-icon { font-size: .7rem; opacity: .7; cursor: default; }
.ca-more { font-size: .65rem; color: var(--muted); font-weight: 600; margin-left: 1px; }
.card-rating { display: flex; align-items: center; gap: .25rem; font-size: .8rem; margin-top: .25rem; }
.cr-stars { color: var(--secondary); letter-spacing: -1px; }
.cr-score { font-weight: 600; color: var(--ink); }
.cr-count { color: var(--muted); font-size: .75rem; }
.badge.ocop-5 {
  background: linear-gradient(135deg, var(--secondary), var(--secondary-dark));
  color: var(--text-on-dark, var(--white));
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
  background: var(--success-bg, rgba(52, 199, 89, .14));
  color: var(--success);
  font-weight: 600;
}
.dark .badge.new-badge {
  background: rgba(var(--success-rgb, 102, 187, 106), .22);
  color: var(--success);
}
.peak-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  vertical-align: middle;
}
.dark .card-arrow {
  background: rgba(var(--black-rgb), 0.65);
  color: var(--white);
  box-shadow: 0 1px 4px rgba(var(--black-rgb), 0.4);
}
.dark .card-dot { background: rgba(var(--white-rgb), 0.4); }
</style>
