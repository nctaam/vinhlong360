<template>
  <article
    class="framed-dossier"
    :class="{ 'framed-dossier--with-media': hasMedia }"
    data-framed-dossier
    :data-density="density"
  >
    <div class="framed-dossier__body" data-dossier-region="identity">
      <p v-if="eyebrow" class="framed-dossier__eyebrow" data-dossier-eyebrow>
        {{ eyebrow }}
      </p>
      <component :is="headingTag" class="framed-dossier__title" data-dossier-title>
        {{ title }}
      </component>
      <div v-if="$slots.summary" class="framed-dossier__summary">
        <slot name="summary" />
      </div>
      <div v-if="$slots.meta" class="framed-dossier__meta">
        <slot name="meta" />
      </div>
    </div>

    <figure v-if="hasMedia" class="framed-dossier__media" data-dossier-media>
      <img :src="mediaSrc" :alt="mediaAlt || ''">
      <figcaption v-if="mediaDisclosure" class="framed-dossier__disclosure">
        {{ mediaDisclosure }}
      </figcaption>
    </figure>
    <p v-else-if="mediaStatus === 'partial'" class="framed-dossier__disclosure" data-dossier-media-state="partial">
      Hình ảnh chưa tải được. Thông tin còn lại vẫn có thể sử dụng.
    </p>

    <div v-if="$slots.trust" class="framed-dossier__trust" data-dossier-region="trust">
      <slot name="trust" />
    </div>
    <div
      v-if="$slots.action"
      class="framed-dossier__action"
      data-dossier-action
      data-dossier-region="action"
      :data-safe-area="actionSafeArea ? 'bottom' : undefined"
    >
      <slot name="action" />
    </div>
    <div v-if="$slots.facts" class="framed-dossier__facts" data-dossier-region="facts">
      <slot name="facts" />
    </div>
    <div v-if="$slots.default" class="framed-dossier__narrative" data-dossier-region="narrative">
      <slot />
    </div>
    <div v-if="$slots.related" class="framed-dossier__related" data-dossier-region="related">
      <slot name="related" />
    </div>
  </article>
</template>

<script setup lang="ts">
type Props = {
  eyebrow?: string
  title: string
  headingTag?: 'h2' | 'h3' | 'h4'
  mediaSrc?: string
  mediaAlt?: string
  mediaDisclosure?: string
  mediaStatus?: 'ready' | 'partial'
  actionSafeArea?: boolean
  density?: 'comfortable' | 'compact'
}

const props = withDefaults(defineProps<Props>(), {
  eyebrow: undefined,
  headingTag: 'h2',
  mediaSrc: undefined,
  mediaAlt: '',
  mediaDisclosure: undefined,
  mediaStatus: 'ready',
  actionSafeArea: false,
  density: 'comfortable',
})

const hasMedia = computed(() => Boolean(props.mediaSrc?.trim()))
</script>
