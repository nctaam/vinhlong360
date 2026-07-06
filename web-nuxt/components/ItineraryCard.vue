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
      <span class="cover-tag cover-dateline cat-itinerary" aria-hidden="true">{{ dateline }}</span>
    </div>
    <div
      v-else
      class="cover cover-img cover-generated cat-itinerary"
      :style="{ backgroundImage: placeholderBg }"
    >
      <span class="cover-grain" aria-hidden="true"></span>
      <span class="cover-svg-icon" v-html="placeholderSvg" />
      <span class="cover-tag cover-dateline cat-itinerary" aria-hidden="true">{{ dateline }}</span>
    </div>
    <div class="card-b">
      <span class="card-dateline">{{ dateline }}</span>
      <h3 class="card-name">{{ itinerary.title || itinerary.name }}</h3>
      <span class="card-rule" aria-hidden="true"></span>
      <div class="itinerary-badge-row">
        <span v-if="itinerary.duration" class="itinerary-duration-badge">{{ itinerary.duration }}</span>
        <span class="itinerary-stops-badge">{{ stopCount }} điểm dừng</span>
      </div>
      <p class="summary card-teaser">{{ itinerary.summary || itinerary.description || '' }}</p>
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
// Cover = real AI-gen Mekong photo per former province (was flat /img/cat/*.jpg illustrations that
// repeated — every "liên vùng" trip showed the same itinerary.jpg). Multi-region/unknown trips
// rotate deterministically by id so adjacent cards show different real photos.
const AREA_PHOTO: Record<string, string> = {
  'vinh-long': '/img/area-vinh-long.webp',
  'ben-tre': '/img/area-ben-tre.webp',
  'tra-vinh': '/img/area-tra-vinh.webp',
}
const ROVING = ['/img/area-vinh-long.webp', '/img/area-ben-tre.webp', '/img/area-tra-vinh.webp', '/img/cat-du-lich.webp']
const coverSrc = computed(() => {
  const direct = AREA_PHOTO[props.itinerary.area]
  if (direct) return direct
  const id = String(props.itinerary.id || props.itinerary.title || '')
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return ROVING[h % ROVING.length]
})
// Deterministic per-itinerary placeholder fallback — seeded by id.
const placeholderBg = computed(() => generateCategoryPlaceholder(props.itinerary.id, 'itinerary'))
const placeholderSvg = computed(() => generateCategoryIcon('itinerary'))

const itineraryAreas = computed(() => Array.isArray(props.itinerary.areas) ? props.itinerary.areas.filter(Boolean) : [])
const areaMeta = computed(() => AREA_META[props.itinerary.area] || { emoji: '📍', name: props.itinerary.area })
const areaName = computed(() => {
  const primary = areaMeta.value.name
  const extra = itineraryAreas.value
    .filter((key: string) => key !== props.itinerary.area)
    .map((key: string) => AREA_META[key]?.name)
    .filter(Boolean)
  return extra.length ? `${primary} + ${extra.join(', ')}` : primary
})
// stop count drives the curated-trip indicator badge (duration + stops)
const stopCount = computed(() => props.itinerary.stops?.length ?? props.itinerary.days?.reduce((n: number, d: any) => n + (d.stops?.length || 0), 0) ?? 0)
// Dateline eyebrow echoes the Story Card pattern ({LOẠI} · {KHU VỰC}) so itinerary cards
// read as the same "spec-tag" idiom as EntityCard, not a bespoke label.
const dateline = computed(() => `Lịch trình · ${areaName.value}`)
</script>

<style scoped>
/* ── Story Card parity (echoes EntityCard's editorial idiom, §2 of the narrative system) ── */
.card-name { font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em; }
.card-dateline {
  display: inline-block; margin-bottom: 2px;
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
.cover-dateline { text-transform: uppercase; letter-spacing: .08em; }
.card-rule {
  display: block; width: 26px; height: 2px; border-radius: 2px; margin: 5px 0 6px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .card-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.card-teaser { color: var(--muted); }
/* grain overlay — turns the flat generated-placeholder gradient into an intentional
   illustration instead of a bare gradient (anti-slop tell #1) */
.cover-grain {
  position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .06;
}
.dark .cover-grain { opacity: .09; }
</style>
