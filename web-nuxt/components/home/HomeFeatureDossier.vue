<template>
  <aside class="home-feature-dossier" data-home-feature-dossier>
    <NuxtLink
      v-if="descriptor.url"
      :to="detailTo"
      class="home-feature-dossier__media"
      data-home-feature-media
      :aria-label="`Xem ${title}`"
    >
      <NuxtImg
        v-if="isRemote(descriptor.url)"
        :src="descriptor.url"
        :alt="descriptor.alt"
        :aria-describedby="disclosureId"
        width="960"
        height="640"
        sizes="375px sm:540px md:640px"
        loading="eager"
        fetchpriority="high"
      />
      <img
        v-else
        :src="descriptor.url"
        :alt="descriptor.alt"
        :aria-describedby="disclosureId"
        width="960"
        height="640"
        loading="eager"
        fetchpriority="high"
      >
      <ImageDisclosure :id="disclosureId" :descriptor="descriptor" presentation="short" />
    </NuxtLink>
    <div v-else class="home-feature-dossier__media home-feature-dossier__media--empty" data-home-feature-media>
      <IconLine name="pin" aria-hidden="true" />
      <ImageDisclosure :id="disclosureId" :descriptor="descriptor" presentation="short" />
    </div>

    <FramedDossier :eyebrow="eyebrow" :title="title" heading-tag="h2">
      <template v-if="summary" #summary>
        <p>{{ summary }}</p>
      </template>
      <template v-if="region" #meta>
        <span>{{ region }}</span>
      </template>
      <template #action>
        <NuxtLink :to="detailTo" class="home-feature-dossier__action" data-home-feature-action>
          Khám phá
        </NuxtLink>
        <NuxtLink
          v-if="plannerTo"
          :to="plannerTo"
          no-prefetch
          class="home-feature-dossier__action home-feature-dossier__action--secondary"
          data-home-feature-action
        >
          Thêm vào lịch trình
        </NuxtLink>
      </template>
    </FramedDossier>
  </aside>
</template>

<script setup lang="ts">
import type { ImageDescriptor } from '~/types/image'

const isRemote = isRemoteUrl

withDefaults(defineProps<{
  eyebrow: string
  title: string
  summary?: string | null
  region?: string | null
  descriptor: ImageDescriptor
  disclosureId: string
  detailTo: string
  plannerTo?: string
}>(), {
  summary: undefined,
  region: undefined,
  plannerTo: undefined,
})
</script>
