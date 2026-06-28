<script setup lang="ts">
const props = withDefaults(defineProps<{
  images: string[]
  alt: string
  maxThumbs?: number
}>(), { maxThumbs: 4 })

const emit = defineEmits<{ 'open-lightbox': [index: number] }>()

const carouselRef = ref<HTMLElement | null>(null)
const activeSlide = ref(0)

const thumbImages = computed(() => props.images.slice(1, props.maxThumbs + 1))
const extraCount = computed(() => Math.max(0, props.images.length - props.maxThumbs - 1))

function isRemote(src: string) {
  return /^https?:\/\//.test(src)
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
  <div v-if="!images.length" class="pg-empty" role="img" :aria-label="alt">
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <rect width="48" height="48" rx="8" fill="currentColor" opacity="0.08"/>
      <path d="M16 32l6-8 4 5 6-10 6 13H10z" fill="currentColor" opacity="0.2"/>
      <circle cx="18" cy="18" r="3" fill="currentColor" opacity="0.25"/>
    </svg>
    <span class="pg-empty-text">Chưa có ảnh</span>
  </div>

  <!-- Single image -->
  <div v-else-if="images.length === 1" class="pg-single">
    <button type="button" class="pg-img-btn" @click="emit('open-lightbox', 0)" :aria-label="`Xem ảnh ${alt}`">
      <NuxtImg v-if="isRemote(images[0])" :src="images[0]" :alt="alt" class="pg-main-img" loading="eager" fetchpriority="high" width="960" height="640" sizes="sm:100vw md:100vw lg:960px" decoding="async" />
      <img v-else :src="images[0]" :alt="alt" class="pg-main-img" loading="eager" fetchpriority="high" width="960" height="640" decoding="async" />
    </button>
  </div>

  <!-- Desktop: asymmetric grid -->
  <div v-else class="pg-grid" role="group" :aria-label="`Bộ ảnh ${alt}`">
    <button type="button" class="pg-main" @click="emit('open-lightbox', 0)" :aria-label="`Ảnh chính — ${alt}`">
      <NuxtImg v-if="isRemote(images[0])" :src="images[0]" :alt="alt" class="pg-main-img" loading="eager" fetchpriority="high" width="640" height="427" sizes="sm:100vw md:60vw lg:640px" decoding="async" />
      <img v-else :src="images[0]" :alt="alt" class="pg-main-img" loading="eager" fetchpriority="high" width="640" height="427" decoding="async" />
    </button>
    <div class="pg-thumbs">
      <button
        v-for="(src, i) in thumbImages"
        :key="src"
        type="button"
        class="pg-thumb"
        @click="emit('open-lightbox', i + 1)"
        :aria-label="`Ảnh ${i + 2} — ${alt}`"
      >
        <NuxtImg v-if="isRemote(src)" :src="src" alt="" aria-hidden="true" class="pg-thumb-img" loading="lazy" width="200" height="200" sizes="sm:60px md:80px lg:100px" decoding="async" />
        <img v-else :src="src" alt="" aria-hidden="true" class="pg-thumb-img" loading="lazy" width="200" height="200" decoding="async" />
      </button>
    </div>
    <button v-if="images.length > 1" type="button" class="pg-show-all" @click="emit('open-lightbox', 0)">
      <span class="pg-show-icon" aria-hidden="true">&#128247;</span>
      Xem {{ images.length }} ảnh
    </button>
  </div>

  <!-- Mobile: carousel -->
  <div v-if="images.length > 1" class="pg-carousel-wrap">
    <div ref="carouselRef" class="pg-carousel" @scroll.passive="onScroll" role="group" :aria-label="`Bộ ảnh ${alt}`">
      <button
        v-for="(src, i) in images"
        :key="src"
        type="button"
        class="pg-slide"
        @click="emit('open-lightbox', i)"
        :aria-label="`Ảnh ${i + 1} — ${alt}`"
      >
        <NuxtImg v-if="isRemote(src)" :src="src" :alt="i === 0 ? alt : ''" :aria-hidden="i > 0 ? 'true' : undefined" class="pg-slide-img" :loading="i === 0 ? 'eager' : 'lazy'" width="400" height="267" sizes="sm:100vw md:60vw lg:400px" decoding="async" />
        <img v-else :src="src" :alt="i === 0 ? alt : ''" :aria-hidden="i > 0 ? 'true' : undefined" class="pg-slide-img" :loading="i === 0 ? 'eager' : 'lazy'" width="400" height="267" decoding="async" />
      </button>
    </div>
    <div v-if="images.length <= 8" class="pg-dots" aria-hidden="true">
      <button
        v-for="(_, i) in images"
        :key="i"
        type="button"
        :class="['pg-dot', { active: i === activeSlide }]"
        :aria-label="`Ảnh ${i + 1}`"
        @click="goToSlide(i)"
      />
    </div>
    <span v-else class="pg-counter">{{ activeSlide + 1 }}/{{ images.length }}</span>
  </div>
</template>

<style scoped>
/* Placeholder */
.pg-empty {
  aspect-ratio: var(--gallery-main-ratio);
  width: 100%;
  border-radius: var(--radius-lg, 12px);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.08), rgba(var(--secondary-rgb), 0.08));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--muted);
}
.pg-empty-text { font-size: var(--text-sm); }

/* Single image */
.pg-single { width: 100%; }
.pg-img-btn {
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
.pg-main:hover .pg-main-img { transform: scale(1.03); }

.pg-thumbs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: var(--gallery-gap);
}

.pg-thumb {
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
.pg-thumb:hover .pg-thumb-img { transform: scale(1.05); }

/* "Xem X ảnh" pill */
.pg-show-all {
  position: absolute;
  bottom: var(--space-3);
  right: var(--space-3);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1h) var(--space-3);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: var(--radius-full, 999px);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold, 600);
  color: var(--ink-900, #1a1a1a);
  cursor: pointer;
  transition: background 200ms, transform 200ms;
}
.pg-show-all:hover { background: var(--card, #fff); transform: scale(1.03); }
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
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    border-radius: var(--radius-full, 999px);
    color: var(--text-on-dark, #fff);
    font-size: var(--text-xs);
    font-weight: var(--weight-semibold, 600);
  }
}
</style>
