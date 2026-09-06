<template>
  <div class="detail-cover-lightbox-suite">
    <!-- Nút xem ảnh bìa -->
    <button
      v-if="hasEntityImages"
      type="button"
      class="dc-photo-btn"
      :aria-label="entityImageDescriptors.length === 1 ? 'Xem ảnh' : `Xem ${entityImageDescriptors.length} ảnh`"
      @click="open(0)"
    >
      <IconLine class="dc-photo-icon" name="camera" aria-hidden="true" />
      {{ entityImageDescriptors.length === 1 ? 'Xem ảnh' : `${entityImageDescriptors.length} ảnh` }}
    </button>

    <!-- Dải thumbnail ảnh -->
    <div v-if="hasEntityImages && entityImageDescriptors.length > 1" class="dc-thumbs">
      <template v-for="(descriptor, i) in entityImageDescriptors.slice(0, 4)" :key="disclosureIdFor(i)">
        <button
          type="button"
          class="dc-thumb-btn"
          data-disclosure-target
          :class="{ active: i === 0 }"
          :aria-label="`Xem ảnh ${i + 1} của ${entityName}`"
          :aria-describedby="disclosureIdFor(i)"
          @click="open(i)"
        >
          <NuxtImg
            v-if="descriptor.url && isRemoteUrl(descriptor.url)"
            :src="descriptor.url"
            :alt="descriptor.alt"
            class="dc-thumb"
            loading="lazy"
            width="56"
            height="40"
            sizes="56px"
            decoding="async"
            @error="hideImage"
          />
          <img
            v-else-if="descriptor.url"
            :src="descriptor.url"
            :alt="descriptor.alt"
            class="dc-thumb"
            loading="lazy"
            width="56"
            height="40"
            decoding="async"
            @error="hideImage"
          />
          <ImageDisclosure :id="disclosureIdFor(i)" :descriptor="descriptor" presentation="short" />
        </button>
      </template>
      <button
        v-if="entityImageDescriptors.length > 4"
        type="button"
        class="dc-thumb-more"
        :aria-label="`Xem thêm ${entityImageDescriptors.length - 4} ảnh`"
        @click="open(4)"
      >
        +{{ entityImageDescriptors.length - 4 }}
      </button>
    </div>

    <!-- Hộp thoại Lightbox phóng to ảnh -->
    <LazyImageLightbox
      v-if="entityImageDescriptors.length"
      v-model="lightboxOpen"
      :images="entityImageDescriptors"
      :start-index="lbIndex"
    />
  </div>
</template>

<script setup lang="ts">
import type { ImageDescriptor } from '~/types/image'

interface Props {
  entityName: string
  entityId: string
  entityImageDescriptors: ImageDescriptor[]
  hasEntityImages: boolean
}

const props = defineProps<Props>()

const lightboxOpen = ref(false)
const lbIndex = ref(0)

function open(idx = 0) {
  if (!props.entityImageDescriptors.length) return
  lbIndex.value = typeof idx === 'number' ? idx : 0
  lightboxOpen.value = true
}

function sanitizeDisclosureIdToken(value: unknown): string {
  const raw = String(value ?? '').trim()
  if (!raw) return 'entity'
  return encodeURIComponent(raw).replace(/%/g, '_').replace(/[^A-Za-z0-9_-]+/g, '-') || 'entity'
}

function disclosureIdFor(index: number): string {
  const token = sanitizeDisclosureIdToken(props.entityId)
  return `entity-image-disclosure-${token}-rail-${index}`
}

function hideImage(payload: Event | string) {
  if (typeof payload === 'string') return
  const img = payload.target
  if (img instanceof HTMLImageElement) img.style.display = 'none'
}

defineExpose({
  open,
  lightboxOpen,
  lbIndex,
})
</script>

<style scoped>
.detail-cover-lightbox-suite {
  display: contents;
}
</style>
