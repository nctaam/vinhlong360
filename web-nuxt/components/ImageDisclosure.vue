<script setup lang="ts">
import { useId } from 'vue'
import type { ImageDescriptor } from '~/types/image'

const props = withDefaults(defineProps<{
  descriptor: ImageDescriptor
  id?: string
  presentation?: 'short' | 'full'
}>(), {
  presentation: 'short',
})

function sanitizeDisclosureIdToken(value: string): string {
  const token = value.trim().replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '')
  if (!token) return ''
  return /^[A-Za-z_]/.test(token) ? token : `image-disclosure-${token}`
}

// Vue's useId is deterministic across SSR hydration and unique within the tree.
const generatedDisclosureId = `image-disclosure-${sanitizeDisclosureIdToken(useId())}`
const disclosureId = computed(() => sanitizeDisclosureIdToken(props.id || '') || generatedDisclosureId)
const showShortLabel = computed(() => props.presentation === 'short' && props.descriptor.short_label !== null)
const disclosureVisible = computed(() => props.presentation === 'full' || props.descriptor.short_label === null)
</script>

<template>
  <span class="image-disclosure" data-disclosure-target data-color-role="disclosure" :aria-describedby="disclosureId">
    <span v-if="showShortLabel" data-short-label data-image-disclosure>{{ descriptor.short_label }}</span>
    <span
      :id="disclosureId"
      data-full-disclosure
      :data-image-disclosure="showShortLabel ? undefined : ''"
      :class="{ 'image-disclosure-sr-only': !disclosureVisible }"
    >{{ descriptor.full_disclosure }}</span>
    <span v-if="descriptor.credit" class="image-disclosure-credit" data-credit>{{ descriptor.credit }}</span>
  </span>
</template>

<style scoped>
.image-disclosure {
  display: inline-flex;
  align-items: center;
  gap: .35em;
  padding: .2em .45em;
  color: var(--color-text-muted);
  font-size: var(--text-2xs, .72rem);
  line-height: 1.3;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}
.image-disclosure-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.image-disclosure-credit { color: var(--color-text-muted); }
</style>
