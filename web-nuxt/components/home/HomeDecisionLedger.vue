<template>
  <section
    v-if="entries.length"
    class="home-decision-ledger"
    data-home-decision-ledger
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
      >
        <NuxtLink :to="entry.to" class="home-decision-ledger__link" :data-tone="entry.tone">
          <span class="home-decision-ledger__eyebrow">{{ entry.eyebrow }}</span>
          <strong class="home-decision-ledger__title">{{ entry.title }}</strong>
          <span class="home-decision-ledger__text">{{ entry.text }}</span>
          <span class="home-decision-ledger__arrow" aria-hidden="true">→</span>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { HomeDecisionEntry } from '~/utils/homeNocturnePresentation'

defineProps<{ entries: readonly HomeDecisionEntry[] }>()
</script>
