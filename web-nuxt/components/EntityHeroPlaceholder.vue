<template>
  <div class="ehp" :class="`cat-${cat}`" :style="{ backgroundImage: bg }" role="img" :aria-label="`Ảnh minh hoạ theo tông màu ${label}`">
    <span class="ehp-grain" aria-hidden="true"></span>
    <span class="ehp-wash" aria-hidden="true"></span>
    <span class="ehp-motif" aria-hidden="true" v-html="motif"></span>
    <span class="ehp-note">Ảnh minh hoạ theo tông màu đặc trưng — chưa có ảnh thật cho nơi này.</span>
  </div>
</template>

<script setup lang="ts">
import { generateCategoryPlaceholder, generateCategoryIcon } from '~/composables/useCategoryPlaceholder'
const props = defineProps<{ id: string | number; cat: string; label?: string }>()
const bg = computed(() => generateCategoryPlaceholder(props.id, props.cat))
const motif = computed(() => generateCategoryIcon(props.cat))
const label = computed(() => props.label || '')
</script>

<style scoped>
.ehp {
  position: relative; width: 100%; height: 100%; min-height: 100%;
  background-size: cover; background-position: center; overflow: hidden; isolation: isolate;
}
.ehp-grain { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background-image: var(--grain); background-size: 140px 140px; opacity: .07; }
.dark .ehp-grain { opacity: .1; }
/* horizontal river→amber→clay sediment wash, low opacity, anchored bottom */
.ehp-wash { position: absolute; inset: 0; z-index: 1; pointer-events: none;
  background: linear-gradient(105deg, rgba(51,100,110,.28) 0%, rgba(232,163,61,.14) 50%, rgba(156,61,34,.24) 100%);
  mix-blend-mode: soft-light; }
/* oversized off-centre category motif bleeding off the right edge */
.ehp-motif { position: absolute; right: -6%; bottom: -8%; z-index: 1; width: 46%; max-width: 320px;
  color: rgba(255,255,255,.5); opacity: .5; }
.ehp-motif :deep(svg) { width: 100%; height: auto; display: block; }
.ehp-note { position: absolute; left: var(--space-4); bottom: var(--space-3); z-index: 2;
  font-size: var(--text-2xs); color: rgba(255,255,255,.82); text-shadow: 0 1px 3px rgba(0,0,0,.45);
  max-width: 62%; line-height: 1.3; }
</style>
