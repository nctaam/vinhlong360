<template>
  <aside
    class="home-feature-dossier"
    data-home-feature-dossier
    data-media-led-feature="editorial-lead"
  >
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
      <template #meta>
        <span v-if="region">{{ region }}</span>
        <span class="home-feature-dossier__stamp" title="Di sản đất phù sa & gốm đỏ Mang Thít">
          <IconLine name="flame" aria-hidden="true" />
          <span>Thổ nhưỡng di sản</span>
        </span>
        <NuxtLink
          v-if="mapTo"
          :to="mapTo"
          class="home-feature-dossier__coords home-feature-dossier__coords--link"
          :data-geo-coordinates="coordinates || '10.254° N, 105.972° E'"
          :title="`Xem vị trí trên bản đồ (${coordinates || '10.254° N, 105.972° E'})`"
        >
          <IconLine name="pin" aria-hidden="true" />
          <span>{{ coordinates || '10.254° N, 105.972° E' }}</span>
        </NuxtLink>
        <span
          v-else
          class="home-feature-dossier__coords"
          :data-geo-coordinates="coordinates || '10.254° N, 105.972° E'"
          :title="`Tọa độ thực địa: ${coordinates || '10.254° N, 105.972° E'}`"
        >
          <IconLine name="pin" aria-hidden="true" />
          <span>{{ coordinates || '10.254° N, 105.972° E' }}</span>
        </span>
        <SourceMark
          :tier="sourceTier"
          :source-title="sourceTitle"
          :source-url="sourceUrl"
          :verified-at="verifiedAt"
          compact
        />
      </template>
      <template #action>
        <NuxtLink
          :to="detailTo"
          class="home-feature-dossier__action"
          data-home-feature-action
          data-color-role="action-secondary"
        >
          Khám phá
        </NuxtLink>
        <NuxtLink
          v-if="plannerTo"
          :to="plannerTo"
          no-prefetch
          class="home-feature-dossier__action home-feature-dossier__action--secondary"
          data-home-feature-action
          data-color-role="action-secondary"
        >
          Thêm vào lịch trình
        </NuxtLink>
      </template>
    </FramedDossier>
  </aside>
</template>

<script setup lang="ts">
import SourceMark from '~/components/SourceMark.vue'
import type { ImageDescriptor } from '~/types/image'
import type { SourceTier } from '~/utils/regionalColor'

const isRemote = isRemoteUrl

withDefaults(defineProps<{
  eyebrow: string
  title: string
  summary?: string | null
  region?: string | null
  descriptor: ImageDescriptor
  disclosureId: string
  detailTo: string
  sourceTier: SourceTier
  sourceTitle?: string | null
  sourceUrl?: string | null
  verifiedAt?: string | null
  plannerTo?: string
  coordinates?: string | null
  mapTo?: string | null
}>(), {
  summary: undefined,
  region: undefined,
  plannerTo: undefined,
  sourceTitle: undefined,
  sourceUrl: undefined,
  verifiedAt: undefined,
  coordinates: '10.254° N, 105.972° E',
  mapTo: undefined,
})
</script>
