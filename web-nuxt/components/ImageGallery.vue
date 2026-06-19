<template>
  <div v-if="images.length" class="detail-gallery">
    <img
      v-for="(src, i) in images"
      :key="i"
      :src="src"
      :alt="`${alt} - ảnh ${i + 1}`"
      class="detail-img"
      :loading="i === 0 ? 'eager' : 'lazy'"
      width="400"
      height="240"
      decoding="async"
      @click="openLightbox(i)"
    />
    <!-- Lightbox -->
    <Teleport to="body">
      <Transition name="lb-fade">
        <div v-if="lightboxIndex >= 0" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="closeLightbox">
          <button type="button" class="lb-close" aria-label="Đóng" @click="closeLightbox">&times;</button>
          <button type="button" v-if="images.length > 1" class="lb-prev" aria-label="Ảnh trước" @click="prev">&#8249;</button>
          <img :src="images[lightboxIndex]" :alt="`${alt} - ảnh ${lightboxIndex + 1}`" class="lb-img" decoding="async" loading="lazy" />
          <button type="button" v-if="images.length > 1" class="lb-next" aria-label="Ảnh tiếp" @click="next">&#8250;</button>
          <div class="lb-counter" aria-live="polite">{{ lightboxIndex + 1 }} / {{ images.length }}</div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  images: string[]
  alt?: string
}>()

const lightboxIndex = ref(-1)
let triggerEl: HTMLElement | null = null

function openLightbox(i: number) {
  triggerEl = document.activeElement as HTMLElement
  lightboxIndex.value = i
}

function closeLightbox() {
  lightboxIndex.value = -1
  nextTick(() => triggerEl?.focus())
}

function prev() {
  lightboxIndex.value = (lightboxIndex.value - 1 + props.images.length) % props.images.length
}

function next() {
  lightboxIndex.value = (lightboxIndex.value + 1) % props.images.length
}

function onKeydown(e: KeyboardEvent) {
  if (lightboxIndex.value < 0) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'ArrowRight') next()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
