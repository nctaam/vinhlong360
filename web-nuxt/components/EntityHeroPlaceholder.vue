<template>
  <div class="ehp" :class="`cat-${cat}`" :style="{ backgroundImage: bg }" :data-material-accent="resolvedMaterialAccent" role="img" :aria-label="descriptor?.alt || `Minh hoạ đồ hoạ ${label}`">
    <span class="ehp-grain" aria-hidden="true"></span>
    <span class="ehp-wash" aria-hidden="true"></span>
    <span class="ehp-motif" aria-hidden="true" v-html="motif"></span>
    <span v-if="!descriptor" class="ehp-note">{{ disclosure }}</span>
  </div>
</template>

<script setup lang="ts">
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
import type { ImageDescriptor } from '~/types/image'
import { aiDisclosure } from '~/utils/aiDisclosure'
import { resolveRegionalAccent, type RegionalAccent } from '~/utils/regionalColor'

const props = withDefaults(defineProps<{
  id?: string | number
  cat?: string
  label?: string
  descriptor?: ImageDescriptor
  materialAccent?: RegionalAccent
}>(), {
  cat: 'place',
  label: '',
})

const seed = computed(() => props.id ?? props.cat ?? 'placeholder')
const bg = computed(() => generateCategoryPlaceholder(seed.value, props.cat))
const motif = computed(() => generateCategoryIcon(props.cat))
const label = computed(() => props.label || '')
const resolvedMaterialAccent = computed(() => props.materialAccent || resolveRegionalAccent(props.cat))
const disclosure = computed(() => props.descriptor?.full_disclosure || aiDisclosure.placeholder.full_disclosure)
</script>

<style scoped>
.ehp {
  position: relative; width: 100%; height: 100%; min-height: 100%;
  background-size: cover; background-position: center; overflow: hidden; isolation: isolate;
}
.ehp-grain { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 140px 140px; opacity: .07; }
.dark .ehp-grain { opacity: .1; }
.ehp-wash { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background: linear-gradient(105deg, color-mix(in srgb, var(--tri-region-material-accent) 30%, transparent), transparent 54%, color-mix(in srgb, var(--tri-region-material-accent) 22%, transparent));
  mix-blend-mode: soft-light; }
/* oversized off-centre category motif bleeding off the right edge */
.ehp-motif { position: absolute; right: -6%; bottom: -8%; z-index: 1; width: 46%; max-width: 320px;
  color: rgba(var(--white-rgb),.5); opacity: .5; }
.ehp-motif :deep(svg) { width: 100%; height: auto; display: block; }
.ehp-note { position: absolute; left: var(--space-4); bottom: var(--space-3); z-index: 2;
  font-size: var(--text-2xs); color: rgba(var(--white-rgb),.82); text-shadow: 0 1px 3px rgba(var(--black-rgb),.45);
  max-width: 62%; line-height: 1.3; }
</style>
