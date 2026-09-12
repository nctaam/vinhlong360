<template>
  <section
    v-if="entries.length"
    class="home-decision-ledger"
    data-home-decision-ledger
    data-route-trace="home-decisions"
    aria-labelledby="home-decision-title"
  >
    <header class="home-decision-ledger__intro">
      <p>Gợi ý nhanh</p>
      <h2 id="home-decision-title">Hôm nay bạn muốn bắt đầu thế nào?</h2>
      <p>Dựa trên mùa, sự kiện và nội dung đang có để đưa bạn tới đúng luồng tiếp theo.</p>
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
          <span class="home-decision-ledger__arrow" aria-hidden="true"><IconLine name="arrow-right" /></span>
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
