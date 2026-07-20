<script setup lang="ts">
import { useId } from 'vue'
import type { ImageDescriptor } from '~/types/image'

const props = withDefaults(defineProps<{
  images: ImageDescriptor[]
  alt: string
  maxThumbs?: number
  standalone?: boolean
}>(), { maxThumbs: 4, standalone: false })

const emit = defineEmits<{ 'open-lightbox': [index: number] }>()

const carouselRef = ref<HTMLElement | null>(null)
const activeSlide = ref(0)
const lbOpen = ref(false)
const lbStart = ref(0)
const galleryId = `gallery-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`

function openLightbox(idx: number) {
  if (!props.images[idx]) return
  if (props.standalone) {
    lbStart.value = idx
    lbOpen.value = true
  } else {
    emit('open-lightbox', idx)
  }
}

const thumbImages = computed(() => props.images.slice(1, props.maxThumbs + 1))
const extraCount = computed(() => Math.max(0, props.images.length - props.maxThumbs - 1))
const firstImage = computed(() => props.images[0] ?? null)
const hasRenderableImages = computed(() => props.images.some(image => Boolean(image.url)))

function disclosureId(surface: string, index: number): string {
  return `${galleryId}-${surface}-${index}`
}

const isRemote = isRemoteUrl

function onImgError(e: Event | string) {
  if (typeof e === 'string') return
  const img = e.target as HTMLImageElement
  if (!(img instanceof HTMLImageElement)) return
  img.style.opacity = '0.15'
  img.style.objectFit = 'contain'
}

function onScroll() {
  const el = carouselRef.value
  if (!el) return
  const idx = Math.round(el.scrollLeft / el.offsetWidth)
  activeSlide.value = Math.min(idx, props.images.length - 1)
}

function goToSlide(idx: number) {
  carouselRef.value?.scrollTo({ left: idx * (carouselRef.value?.offsetWidth ?? 0), behavior: 'smooth' })
}
</script>

<template>
  <!-- No images: placeholder -->
  <div v-if="!hasRenderableImages" class="pg-empty" role="img" :aria-label="firstImage?.alt || alt" :aria-describedby="firstImage ? disclosureId('empty', 0) : undefined">
    <span class="pg-empty-grain" aria-hidden="true"></span>
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <rect width="48" height="48" rx="8" fill="currentColor" opacity="0.08"/>
      <path d="M16 32l6-8 4 5 6-10 6 13H10z" fill="currentColor" opacity="0.2"/>
      <circle cx="18" cy="18" r="3" fill="currentColor" opacity="0.25"/>
    </svg>
    <span v-if="firstImage" :id="disclosureId('empty', 0)" data-full-disclosure class="pg-empty-text">
      <span>{{ firstImage.full_disclosure }}</span>
      <span v-if="firstImage.credit" data-credit class="pg-empty-credit">{{ firstImage.credit }}</span>
    </span>
    <span v-else class="pg-empty-text">Chưa có ảnh cho nơi này</span>
  </div>

  <!-- Single image -->
  <div v-else-if="images.length === 1 && firstImage" class="pg-single">
    <button type="button" class="pg-img-btn" @click="openLightbox(0)" :aria-label="`Xem ảnh ${firstImage.alt}`">
      <NuxtImg v-if="firstImage.url && isRemote(firstImage.url)" data-gallery-media :src="firstImage.url" :alt="firstImage.alt" class="pg-main-img" :aria-describedby="disclosureId('single', 0)" loading="eager" fetchpriority="high" width="960" height="640" sizes="sm:100vw md:100vw lg:960px" decoding="async" @error="onImgError" />
      <img v-else-if="firstImage.url" data-gallery-media :src="firstImage.url" :alt="firstImage.alt" class="pg-main-img" :aria-describedby="disclosureId('single', 0)" loading="eager" fetchpriority="high" width="960" height="640" decoding="async" @error="onImgError" />
      <span :id="disclosureId('single', 0)" data-full-disclosure class="pg-disclosure">
        <span>{{ firstImage.full_disclosure }}</span>
        <span v-if="firstImage.credit" data-credit>{{ firstImage.credit }}</span>
      </span>
    </button>
  </div>

  <!-- Desktop: asymmetric grid -->
  <div v-else class="pg-grid" role="group" :aria-label="`Bộ ảnh ${alt}`">
    <button type="button" class="pg-main" @click="openLightbox(0)" :aria-label="`Ảnh chính — ${firstImage?.alt || alt}`">
      <NuxtImg v-if="firstImage?.url && isRemote(firstImage.url)" data-gallery-media :src="firstImage.url" :alt="firstImage.alt" class="pg-main-img" :aria-describedby="disclosureId('main', 0)" loading="eager" fetchpriority="high" width="640" height="427" sizes="sm:100vw md:60vw lg:640px" decoding="async" @error="onImgError" />
      <img v-else-if="firstImage?.url" data-gallery-media :src="firstImage.url" :alt="firstImage.alt" class="pg-main-img" :aria-describedby="disclosureId('main', 0)" loading="eager" fetchpriority="high" width="640" height="427" decoding="async" @error="onImgError" />
      <span v-else class="pg-media-placeholder" role="img" :aria-label="firstImage?.alt || alt" :aria-describedby="disclosureId('main', 0)">▧</span>
      <span v-if="firstImage" :id="disclosureId('main', 0)" data-full-disclosure class="pg-disclosure">
        <span>{{ firstImage.full_disclosure }}</span>
        <span v-if="firstImage.credit" data-credit>{{ firstImage.credit }}</span>
      </span>
    </button>
    <div class="pg-thumbs">
      <button
        v-for="(descriptor, i) in thumbImages"
        :key="`${descriptor.url || descriptor.alt}-${i}`"
        type="button"
        class="pg-thumb"
        @click="openLightbox(i + 1)"
        :aria-label="`Ảnh ${i + 2} — ${alt}`"
      >
        <NuxtImg v-if="descriptor.url && isRemote(descriptor.url)" data-gallery-media :src="descriptor.url" :alt="descriptor.alt" class="pg-thumb-img" :aria-describedby="disclosureId('thumb', i + 1)" loading="lazy" width="200" height="200" sizes="sm:60px md:80px lg:100px" decoding="async" @error="onImgError" />
        <img v-else-if="descriptor.url" data-gallery-media :src="descriptor.url" :alt="descriptor.alt" class="pg-thumb-img" :aria-describedby="disclosureId('thumb', i + 1)" loading="lazy" width="200" height="200" decoding="async" @error="onImgError" />
        <span v-else class="pg-media-placeholder" role="img" :aria-label="descriptor.alt" :aria-describedby="disclosureId('thumb', i + 1)">▧</span>
        <span :id="disclosureId('thumb', i + 1)" data-full-disclosure class="pg-disclosure">
          <span>{{ descriptor.full_disclosure }}</span>
          <span v-if="descriptor.credit" data-credit>{{ descriptor.credit }}</span>
        </span>
      </button>
    </div>
    <button v-if="images.length > 1" type="button" class="pg-show-all" @click="openLightbox(0)">
      <span class="pg-show-icon" aria-hidden="true">&#128247;</span>
      Xem trọn bộ {{ images.length }} ảnh
    </button>
  </div>

  <!-- Mobile: carousel -->
  <div v-if="images.length > 1" class="pg-carousel-wrap">
    <div ref="carouselRef" class="pg-carousel" @scroll.passive="onScroll" role="group" :aria-label="`Bộ ảnh ${alt}`">
      <button
        v-for="(descriptor, i) in images"
        :key="`${descriptor.url || descriptor.alt}-slide-${i}`"
        type="button"
        class="pg-slide"
        @click="openLightbox(i)"
        :aria-label="`Ảnh ${i + 1} — ${alt}`"
      >
        <NuxtImg v-if="descriptor.url && isRemote(descriptor.url)" data-gallery-media :src="descriptor.url" :alt="descriptor.alt" :aria-describedby="disclosureId('slide', i)" class="pg-slide-img" :loading="i === 0 ? 'eager' : 'lazy'" width="400" height="267" sizes="sm:100vw md:60vw lg:400px" decoding="async" @error="onImgError" />
        <img v-else-if="descriptor.url" data-gallery-media :src="descriptor.url" :alt="descriptor.alt" :aria-describedby="disclosureId('slide', i)" class="pg-slide-img" :loading="i === 0 ? 'eager' : 'lazy'" width="400" height="267" decoding="async" @error="onImgError" />
        <span v-else class="pg-media-placeholder" role="img" :aria-label="descriptor.alt" :aria-describedby="disclosureId('slide', i)">▧</span>
        <span :id="disclosureId('slide', i)" data-full-disclosure class="pg-disclosure">
          <span>{{ descriptor.full_disclosure }}</span>
          <span v-if="descriptor.credit" data-credit>{{ descriptor.credit }}</span>
        </span>
      </button>
    </div>
    <div v-if="images.length <= 8" class="pg-dots" aria-hidden="true">
      <button
        v-for="(_, i) in images"
        :key="i"
        type="button"
        tabindex="-1"
        :class="['pg-dot', { active: i === activeSlide }]"
        :aria-label="`Ảnh ${i + 1}`"
        @click="goToSlide(i)"
      />
    </div>
    <span v-else class="pg-counter">{{ activeSlide + 1 }}/{{ images.length }}</span>
  </div>

  <ImageLightbox v-if="standalone && images.length" v-model="lbOpen" :images="images" :start-index="lbStart" />
</template>

<style scoped>
/* Placeholder — phù-sa treatment: gradient wash + grain overlay, same restraint as
   the Story Card cover placeholder (anti-slop: flat gradient alone reads as unfinished). */
.pg-empty {
  position: relative;
  aspect-ratio: var(--gallery-main-ratio);
  width: 100%;
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.08), rgba(var(--secondary-rgb), 0.08));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--muted);
}
.pg-empty-grain {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .05;
}
.dark .pg-empty-grain { opacity: .08; }
.pg-empty svg, .pg-empty-text { position: relative; z-index: 1; }
.pg-empty-text { font-family: var(--font-editorial); font-size: var(--text-sm); }
.pg-empty-credit { position: relative; z-index: 1; font-size: var(--text-xs); color: var(--muted); }

/* Single image */
.pg-single { width: 100%; }
.pg-img-btn {
  position: relative;
  display: block;
  width: 100%;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}
.pg-img-btn:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
.pg-main-img {
  width: 100%;
  aspect-ratio: var(--gallery-main-ratio);
  object-fit: cover;
  display: block;
}

/* Desktop grid */
.pg-grid {
  position: relative;
  display: grid;
  grid-template-columns: 3fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: var(--gallery-gap);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}

.pg-main {
  position: relative;
  grid-row: 1 / -1;
  padding: 0;
  border: none;
  background: var(--bg-alt);
  cursor: pointer;
  overflow: hidden;
}
.pg-main:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.pg-main .pg-main-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform .3s var(--ease-out, ease);
}
.pg-main:hover .pg-main-img { transform: scale(var(--img-hover-scale)); }

.pg-thumbs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: var(--gallery-gap);
}

.pg-thumb {
  position: relative;
  padding: 0;
  border: none;
  background: var(--bg-alt);
  cursor: pointer;
  overflow: hidden;
}
.pg-thumb:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.pg-thumb-img {
  width: 100%;
  height: 100%;
  aspect-ratio: var(--gallery-thumb-ratio);
  object-fit: cover;
  display: block;
  transition: transform .3s var(--ease-out, ease);
}
.pg-thumb:hover .pg-thumb-img { transform: scale(var(--img-hover-scale)); }

.pg-media-placeholder {
  width: 100%;
  height: 100%;
  min-height: 120px;
  display: grid;
  place-items: center;
  color: var(--muted);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .08), rgba(var(--secondary-rgb), .08));
  font-size: 2rem;
}
.pg-disclosure {
  position: absolute;
  z-index: 2;
  left: var(--space-2);
  right: var(--space-2);
  bottom: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm, 6px);
  color: var(--text-on-dark);
  background: rgba(var(--black-rgb), .7);
  font-size: var(--text-2xs, .72rem);
  line-height: 1.35;
  text-align: left;
  pointer-events: none;
}
.pg-disclosure [data-credit] { color: rgba(var(--white-rgb), .78); }

/* "Xem trọn bộ N ảnh" pill — hairline museum-label register, not an app badge */
.pg-show-all {
  position: absolute;
  bottom: var(--space-3);
  right: var(--space-3);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1h) var(--space-3);
  background: rgba(var(--white-rgb), 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--black-rgb), 0.12);
  border-radius: var(--radius-full, 999px);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold, 600);
  color: var(--ink-900);
  cursor: pointer;
  transition: background 200ms, transform 200ms;
}
.pg-show-all:hover { background: var(--card, var(--white)); transform: scale(1.03); }
.pg-show-all:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.pg-show-icon { font-size: 1em; }

/* Mobile carousel — hidden on desktop */
.pg-carousel-wrap { display: none; }

@media (max-width: 767px) {
  .pg-grid { display: none; }
  .pg-carousel-wrap { display: block; position: relative; }

  .pg-carousel {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    border-radius: var(--radius-lg, 12px);
  }
  .pg-carousel::-webkit-scrollbar { display: none; }

  .pg-slide {
    position: relative;
    flex: 0 0 100%;
    scroll-snap-align: center;
    padding: 0;
    border: none;
    background: var(--bg-alt);
    cursor: pointer;
  }
  .pg-slide:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
  .pg-slide-img {
    width: 100%;
    aspect-ratio: var(--gallery-main-ratio);
    object-fit: cover;
    display: block;
  }

  .pg-dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    padding: var(--space-2) 0;
  }
  .pg-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    border: none;
    padding: 0;
    background: rgba(var(--primary-rgb), 0.25);
    cursor: pointer;
    transition: background 200ms, transform 200ms;
  }
  .pg-dot.active {
    background: var(--primary);
    transform: scale(1.3);
  }
  .pg-dot:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

  .pg-counter {
    position: absolute;
    bottom: var(--space-3);
    right: var(--space-3);
    padding: 2px 10px;
    background: rgba(var(--black-rgb), 0.55);
    backdrop-filter: blur(4px);
    border-radius: var(--radius-full, 999px);
    color: var(--text-on-dark, var(--white));
    font-size: var(--text-xs);
    font-weight: var(--weight-semibold, 600);
    font-variant-numeric: tabular-nums;
  }
}
.dark .pg-show-all {
  background: rgba(var(--black-rgb), 0.7);
  border-color: rgba(var(--white-rgb), 0.15);
  color: var(--white);
}
.dark .pg-show-all:hover { background: rgba(var(--black-rgb), 0.8); }
@media (prefers-reduced-motion: reduce) {
  .pg-main .pg-main-img,
  .pg-thumb-img { transition: none; }
  .pg-main:hover .pg-main-img,
  .pg-thumb:hover .pg-thumb-img { transform: none; }
  .pg-show-all:hover { transform: none; }
  .pg-dot { transition: none; }
}
</style>
