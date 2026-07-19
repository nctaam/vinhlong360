<script setup lang="ts">
import { useId } from 'vue'
import type { ImageDescriptor } from '~/types/image'

const props = withDefaults(defineProps<{
  images: ImageDescriptor[]
  modelValue: boolean
  startIndex?: number
}>(), { startIndex: 0 })

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

function normalizeIndex(value: number, length = props.images.length): number {
  if (!length) return 0
  const candidate = Number.isInteger(value) ? value : 0
  return ((candidate % length) + length) % length
}

const index = ref(normalizeIndex(props.startIndex))
const dialogEl = ref<HTMLElement | null>(null)
const swiping = ref(false)
const touchDX = ref(0)
let touchStartX = 0
let pendingDX = 0
let dragRafId = 0

const prefetched = new Set<string>()
const prefetchLinks: HTMLLinkElement[] = []
const lightboxId = `lightbox-${useId().replace(/[^A-Za-z0-9_-]+/g, '-')}`

const active = computed(() => props.images[index.value] ?? null)
const captionId = computed(() => `${lightboxId}-disclosure-${index.value}`)

function close() { emit('update:modelValue', false) }

const isOpen = computed(() => props.modelValue)
useModalA11y(isOpen, dialogEl, { onClose: close })

watch(() => props.modelValue, (open) => {
  if (open) {
    index.value = normalizeIndex(props.startIndex)
  } else {
    swiping.value = false
    touchDX.value = 0
  }
})

watch(() => props.images.length, (length) => {
  index.value = normalizeIndex(index.value, length)
})

function prev() {
  const len = props.images.length
  if (!len) return
  index.value = (index.value - 1 + len) % len
}
function next() {
  const len = props.images.length
  if (!len) return
  index.value = (index.value + 1) % len
}

watch(index, (idx) => {
  if (!props.modelValue || !import.meta.client) return
  const imgs = props.images
  if (!imgs || imgs.length <= 1) return
  const len = imgs.length
  for (const offset of [1, -1]) {
    const src = imgs[(idx + offset + len) % len]?.url
    if (typeof src === 'string' && src && !prefetched.has(src)) {
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
  const touch = e.touches[0]
  if (!touch) return
  touchStartX = touch.clientX
  touchDX.value = 0
  pendingDX = 0
  swiping.value = true
}
function onTouchMove(e: TouchEvent) {
  if (!swiping.value || !e.touches.length) return
  const touch = e.touches[0]
  if (!touch) return
  pendingDX = touch.clientX - touchStartX
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
        <button type="button" v-if="images.length > 1" class="lb-prev" data-prev aria-label="Ảnh trước" @click="prev">&#8249;</button>
        <template v-if="active">
          <img
            v-if="active.url"
            data-active-media
            :src="active.url"
            :alt="active.alt"
            :aria-describedby="captionId"
            class="lb-img"
            :style="dragStyle"
            :key="`image-${index}`"
            loading="eager"
            decoding="async"
            @error="($event.target as HTMLImageElement).style.opacity = '0.3'"
          />
          <div
            v-else
            data-active-media
            data-placeholder-media="true"
            role="img"
            :aria-label="active.alt"
            :aria-describedby="captionId"
            class="lb-placeholder"
            :key="`placeholder-${index}`"
          >
            <span aria-hidden="true">▧</span>
          </div>
          <span :id="captionId" data-full-disclosure class="lb-caption">
            <span>{{ active.full_disclosure }}</span>
            <span v-if="active.credit" data-credit class="lb-credit">{{ active.credit }}</span>
          </span>
        </template>
        <button type="button" v-if="images.length > 1" class="lb-next" data-next aria-label="Ảnh tiếp" @click="next">&#8250;</button>
        <div class="lb-counter" data-counter aria-live="polite">{{ images.length ? index + 1 : 0 }} / {{ images.length }}</div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.lb-caption {
  position: absolute;
  left: 50%;
  bottom: calc(var(--space-5) + 48px);
  transform: translateX(-50%);
  z-index: 1;
  width: min(720px, calc(100vw - 48px));
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: .5px solid rgba(255, 255, 255, .16);
  border-radius: var(--radius-md, 10px);
  background: rgba(0, 0, 0, .68);
  color: var(--text-on-dark, #fff);
  font-size: var(--text-sm);
  line-height: 1.4;
  text-align: center;
}
.lb-credit { color: rgba(255, 255, 255, .74); font-size: var(--text-xs); }
.lb-placeholder {
  width: min(90vw, 960px);
  height: min(70vh, 640px);
  display: grid;
  place-items: center;
  border-radius: var(--radius-md, 10px);
  color: rgba(255, 255, 255, .62);
  background: linear-gradient(135deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .03));
  font-size: 4rem;
}
</style>
