<script setup lang="ts">
const props = withDefaults(defineProps<{
  images: string[]
  modelValue: boolean
  startIndex?: number
}>(), { startIndex: 0 })

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const index = ref(props.startIndex)
const dialogEl = ref<HTMLElement | null>(null)
const swiping = ref(false)
const touchDX = ref(0)
let touchStartX = 0
let pendingDX = 0
let dragRafId = 0

const prefetched = new Set<string>()
const prefetchLinks: HTMLLinkElement[] = []

function close() { emit('update:modelValue', false) }

const isOpen = computed(() => props.modelValue)
useModalA11y(isOpen, dialogEl, { onClose: close })

watch(() => props.modelValue, (open) => {
  if (open) {
    index.value = props.startIndex
  } else {
    swiping.value = false
    touchDX.value = 0
  }
})

function prev() {
  const len = props.images.length || 1
  index.value = (index.value - 1 + len) % len
}
function next() {
  const len = props.images.length || 1
  index.value = (index.value + 1) % len
}

watch(index, (idx) => {
  if (!props.modelValue || !import.meta.client) return
  const imgs = props.images
  if (!imgs || imgs.length <= 1) return
  const len = imgs.length
  for (const offset of [1, -1]) {
    const src = imgs[(idx + offset + len) % len]
    if (src && !prefetched.has(src)) {
      prefetched.add(src)
      const link = document.createElement('link')
      link.rel = 'prefetch'
      link.as = 'image'
      link.href = src
      document.head.appendChild(link)
      prefetchLinks.push(link)
    }
  }
})

const dragStyle = computed(() => {
  if (!swiping.value || !touchDX.value) return {}
  const dx = touchDX.value
  const abs = Math.abs(dx)
  const opacity = Math.max(0.5, 1 - abs / 380)
  const scale = opacity > 0.75 ? 1 : Math.max(0.94, opacity)
  return { transform: `translateX(${dx}px) scale(${scale})`, opacity, transition: 'none' }
})

function onTouchStart(e: TouchEvent) {
  if (!e.touches.length) return
  touchStartX = e.touches[0].clientX
  touchDX.value = 0
  pendingDX = 0
  swiping.value = true
}
function onTouchMove(e: TouchEvent) {
  if (!swiping.value || !e.touches.length) return
  pendingDX = e.touches[0].clientX - touchStartX
  if (!dragRafId) {
    dragRafId = requestAnimationFrame(() => { touchDX.value = pendingDX; dragRafId = 0 })
  }
}
function onTouchEnd() {
  if (dragRafId) { cancelAnimationFrame(dragRafId); dragRafId = 0 }
  if (!swiping.value) return
  touchDX.value = pendingDX
  if (touchDX.value < -60) next()
  else if (touchDX.value > 60) prev()
  swiping.value = false
  touchDX.value = 0
}

onUnmounted(() => {
  if (import.meta.client) {
    prefetchLinks.forEach(link => link.remove())
    if (dragRafId) { cancelAnimationFrame(dragRafId); dragRafId = 0 }
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="lb-fade">
      <div v-if="modelValue" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh"
        @click.self="close" @keydown.left="prev" @keydown.right="next"
        ref="dialogEl"
        @touchstart.passive="onTouchStart" @touchmove.passive="onTouchMove" @touchend="onTouchEnd">
        <button type="button" class="lb-close" aria-label="Đóng" @click="close">&times;</button>
        <button type="button" v-if="images.length > 1" class="lb-prev" aria-label="Ảnh trước" @click="prev">&#8249;</button>
        <img :src="images[index]" :alt="`Ảnh ${index + 1}`" class="lb-img" :style="dragStyle" :key="index"
          loading="eager" decoding="async" @error="($event.target as HTMLImageElement).style.opacity = '0.3'" />
        <button type="button" v-if="images.length > 1" class="lb-next" aria-label="Ảnh tiếp" @click="next">&#8250;</button>
        <div class="lb-counter" aria-live="polite">{{ index + 1 }} / {{ images.length }}</div>
      </div>
    </Transition>
  </Teleport>
</template>
