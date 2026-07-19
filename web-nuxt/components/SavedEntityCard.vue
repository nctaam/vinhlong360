<template>
  <div class="saved-entity card">
    <NuxtLink :to="savedItemPath(item)" class="saved-entity-link">
      <span class="saved-entity-cover">
        <NuxtImg v-if="displayDescriptor.url && isRemoteUrl(displayDescriptor.url)" :src="displayDescriptor.url" :alt="displayDescriptor.alt" :aria-describedby="disclosureId" class="saved-entity-img" width="120" height="80" sizes="sm:100vw md:120px" loading="lazy" decoding="async" @error="imgError = true" />
        <img v-else-if="displayDescriptor.url" :src="displayDescriptor.url" :alt="displayDescriptor.alt" :aria-describedby="disclosureId" class="saved-entity-img" width="120" height="80" loading="lazy" decoding="async" @error="imgError = true" />
        <span v-else class="saved-entity-img saved-entity-img-generated" aria-hidden="true"><span class="cover-grain"></span></span>
        <span class="saved-image-disclosure"><ImageDisclosure :id="disclosureId" :descriptor="displayDescriptor" presentation="short" /></span>
      </span>
      <div class="saved-entity-info">
        <span v-if="dateline" class="saved-dateline">{{ dateline }}</span>
        <span class="saved-entity-name">{{ item.name }}</span>
        <span class="saved-card-rule" aria-hidden="true"></span>
        <span v-if="item.place_name" class="saved-entity-place">{{ item.place_name }}</span>
      </div>
    </NuxtLink>
    <slot name="action" />
  </div>
</template>

<script setup lang="ts">
// Shared Story-Card treatment for "saved/favorite entity" rows — canonical look
// authored on da-luu.vue: serif name, uppercase dateline eyebrow, tri-province
// .card-rule, grain overlay on the no-photo cover. Consolidates the 3 bespoke
// copies that had drifted (da-luu, lich-trinh/index, nguoi-dung/[id]) into one
// component so all three render consistently AND all get NuxtImg optimization
// (the previous nguoi-dung plain-<img> was the drift point).
//
// Deliberately NOT built on EntityCard: EntityCard expects a full entity object
// (images[], attributes, season, updatedAt) to drive its carousel/badges/rating/
// amenities, but saved rows only ever carry a thin snapshot (id/name/type/image/
// place_name/place_area). EntityCard also bakes in its own save/unsave SaveButton,
// which would collide with each page's own remove/unsave action here — so the
// per-page action is a slot instead.
import { TYPE_META } from '~/composables/useConstants'
import { entityDateline } from '~/composables/useEntityStory'
import { describeEntityPlaceholder } from '~/utils/imageDescriptors'
import { normalizeSavedImageSnapshot } from '~/utils/savedImageDescriptors'
import { useId } from 'vue'

const props = defineProps<{
  item: Record<string, any>
}>()

const imgError = ref(false)
const savedSnapshot = computed(() => normalizeSavedImageSnapshot(props.item))
const displayDescriptor = computed(() => imgError.value
  ? describeEntityPlaceholder(props.item)
  : savedSnapshot.value.image_descriptor)
const disclosureInstance = useId().replace(/[^A-Za-z0-9_-]+/g, '-')
const disclosureId = computed(() => {
  const token = String(props.item?.id || 'saved').replace(/[^A-Za-z0-9_-]+/g, '-')
  return `saved-card-${token}-${disclosureInstance}`
})
watch(() => props.item, () => { imgError.value = false }, { deep: true })

// "{TYPE LABEL} · {AREA}" eyebrow — same fallback chain as EntityCard's dateline,
// applied to the thin saved-item snapshot (id/name/type/place_area/summary only).
const dateline = computed(() => {
  const label = TYPE_META[props.item?.type]?.label || props.item?.type || ''
  if (!label) return ''
  return entityDateline(props.item, label)
})
</script>

<style scoped>
/* Entity row — editorial parity with EntityCard's Story-Card treatment:
   serif title, uppercase dateline eyebrow, tri-province card-rule, grain
   overlay on the no-photo cover. Canonical look authored on da-luu.vue. */
.saved-entity { display: flex; align-items: center; padding: .5rem; gap: 0; }
.saved-entity-link {
  display: flex; align-items: center; gap: .75rem; flex: 1; min-width: 0;
  text-decoration: none; color: var(--ink);
}
.saved-entity-cover { position: relative; display: block; flex-shrink: 0; width: 80px; height: 56px; border-radius: var(--radius-md); overflow: hidden; }
.saved-entity-img { display: block; width: 80px; height: 56px; border-radius: var(--radius-md); object-fit: cover; flex-shrink: 0; }
.saved-image-disclosure { position: absolute; inset: auto 2px 2px; display: flex; justify-content: flex-end; }
.saved-image-disclosure :deep([data-image-disclosure]) { font-size: 9px; padding: 1px 4px; }
.saved-entity-img-generated { position: relative; background: linear-gradient(160deg, rgba(var(--primary-rgb), .14) 0%, var(--bg-alt) 70%); }
.saved-entity-img-generated .cover-grain {
  position: absolute; inset: 0; background-image: var(--grain); background-size: 120px 120px; opacity: .06;
}
.dark .saved-entity-img-generated .cover-grain { opacity: .09; }
.saved-entity-info { flex: 1; min-width: 0; }
.saved-dateline {
  display: block; margin-bottom: 1px;
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
}
.saved-entity-name {
  display: block; font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em;
  font-size: .95rem; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.saved-card-rule {
  display: block; width: 22px; height: 2px; border-radius: 2px; margin: 3px 0 3px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .saved-card-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.saved-entity-place { display: block; font-size: .78rem; color: var(--ink-700); }

/* Dark */
.dark .saved-entity { background: var(--bg-alt); }

/* Mobile */
@media (max-width: 600px) {
  .saved-entity-cover, .saved-entity-img { width: 60px; height: 42px; }
}
</style>
