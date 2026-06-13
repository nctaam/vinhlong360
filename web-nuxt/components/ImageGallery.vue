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
      <div v-if="lightboxIndex >= 0" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="lightboxIndex = -1">
        <button class="lb-close" aria-label="Đóng" @click="lightboxIndex = -1">&times;</button>
        <button v-if="images.length > 1" class="lb-prev" aria-label="Ảnh trước" @click="prev">&#8249;</button>
        <img :src="images[lightboxIndex]" :alt="`${alt} - ảnh ${lightboxIndex + 1}`" class="lb-img" />
        <button v-if="images.length > 1" class="lb-next" aria-label="Ảnh tiếp" @click="next">&#8250;</button>
        <div class="lb-counter" aria-live="polite">{{ lightboxIndex + 1 }} / {{ images.length }}</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  images: string[]
  alt?: string
}>()

const lightboxIndex = ref(-1)

function openLightbox(i: number) {
  lightboxIndex.value = i
}

function prev() {
  lightboxIndex.value = (lightboxIndex.value - 1 + props.images.length) % props.images.length
}

function next() {
  lightboxIndex.value = (lightboxIndex.value + 1) % props.images.length
}

function onKeydown(e: KeyboardEvent) {
  if (lightboxIndex.value < 0) return
  if (e.key === 'Escape') lightboxIndex.value = -1
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'ArrowRight') next()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
