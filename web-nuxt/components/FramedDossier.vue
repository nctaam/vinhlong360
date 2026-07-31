<template>
  <article
    class="framed-dossier"
    :class="{ 'framed-dossier--with-media': hasMedia }"
    data-framed-dossier
  >
    <figure v-if="hasMedia" class="framed-dossier__media" data-dossier-media>
      <img :src="mediaSrc" :alt="mediaAlt || ''">
      <figcaption v-if="mediaDisclosure" class="framed-dossier__disclosure">
        {{ mediaDisclosure }}
      </figcaption>
    </figure>

    <div class="framed-dossier__body">
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
      <div v-if="$slots.action" class="framed-dossier__action">
        <slot name="action" />
      </div>
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
}

const props = withDefaults(defineProps<Props>(), {
  eyebrow: undefined,
  headingTag: 'h2',
  mediaSrc: undefined,
  mediaAlt: '',
  mediaDisclosure: undefined,
})

const hasMedia = computed(() => Boolean(props.mediaSrc?.trim()))
</script>
