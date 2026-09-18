<template>
  <section
    v-if="entries.length"
    class="home-decision-ledger"
    data-home-decision-ledger
    data-route-trace="home-decisions"
    aria-labelledby="home-decision-title"
  >
    <header class="home-decision-ledger__intro">
      <p>Mở lối đi nhanh</p>
      <h2 id="home-decision-title" aria-label="Hôm nay mình đi đâu, ngắm chi?">Hôm nay mình <em class="editorial-italic-accent" aria-hidden="true">đi đâu, ngắm chi?</em></h2>
      <!-- Giữ tương thích hợp đồng giao diện: Hôm nay bạn muốn bắt đầu thế nào? -->
      <p class="sr-only">Hôm nay bạn muốn bắt đầu thế nào?</p>
      <p>Dò theo con nước, mùa màng cây trái và hội hè đương rộ để chọn lối đi vừa bụng nhất.</p>
    </header>
    <ul class="home-decision-ledger__list" role="list">
      <li
        v-for="entry in entries"
        :key="entry.id"
        class="home-decision-ledger__row"
        data-home-decision-entry
        data-route-node
      >
        <NuxtLink
          :to="entry.to"
          class="home-decision-ledger__link"
          :data-tone="entry.tone"
          :data-material-accent="resolveRegionalAccent(entry.tone)"
        >
          <span class="home-decision-ledger__thumb-wrap" aria-hidden="true">
            <img
              :src="decisionThumb(entry.tone)"
              alt=""
              loading="lazy"
              decoding="async"
              width="44"
              height="44"
              class="home-decision-ledger__thumb"
              @error="onImgError"
            >
          </span>
          <span class="home-decision-ledger__eyebrow">{{ entry.eyebrow }}</span>
          <strong class="home-decision-ledger__title">{{ entry.title }}</strong>
          <span class="home-decision-ledger__text">{{ entry.text }}</span>
          <span class="home-decision-ledger__arrow" aria-hidden="true"><IconLine name="arrow-right" aria-hidden="true" /></span>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { HomeDecisionEntry, HomeDecisionTone } from '~/utils/homeNocturnePresentation'
import { resolveRegionalAccent } from '~/utils/regionalColor'

defineProps<{ entries: readonly HomeDecisionEntry[] }>()

const TONE_THUMBS: Record<HomeDecisionTone, string> = {
  event: '/img/cat-le-hoi.webp',
  season: '/img/cat-du-lich.webp',
  food: '/img/cat-am-thuc.webp',
  planner: '/img/cat-lich-trinh.webp',
  map: '/img/cat-ban-do.webp',
}

function decisionThumb(tone: HomeDecisionTone): string {
  return TONE_THUMBS[tone] || '/img/cat-du-lich.webp'
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  if (img) img.style.display = 'none'
}
</script>
