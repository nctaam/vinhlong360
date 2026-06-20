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
      role="button"
      tabindex="0"
      :aria-label="`Xem ảnh ${i + 1}`"
      @click="openLightbox(i)"
      @keydown.enter.prevent="openLightbox(i)"
      @keydown.space.prevent="openLightbox(i)"
    />
    <!-- Lightbox -->
    <Teleport to="body">
      <Transition name="lb-fade">
        <div v-if="lightboxIndex >= 0" ref="lbEl" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="closeLightbox">
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
const lbEl = ref<HTMLElement>()
let triggerEl: HTMLElement | null = null

function openLightbox(i: number) {
  triggerEl = document.activeElement as HTMLElement
  lightboxIndex.value = i
  nextTick(() => lbEl.value?.querySelector<HTMLElement>('button')?.focus())
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
  else if (e.key === 'ArrowLeft') prev()
  else if (e.key === 'ArrowRight') next()
  else if (e.key === 'Tab') {
    // Trap focus among the lightbox controls while the modal is open.
    const btns = lbEl.value ? Array.from(lbEl.value.querySelectorAll<HTMLElement>('button')) : []
    if (!btns.length) return
    const first = btns[0]!, last = btns[btns.length - 1]!
    const active = document.activeElement as HTMLElement
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus() }
    else if (!btns.includes(active)) { e.preventDefault(); first.focus() }
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
