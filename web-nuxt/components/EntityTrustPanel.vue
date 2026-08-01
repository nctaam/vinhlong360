<template>
  <section class="entity-trust-panel" data-entity-trust-panel aria-labelledby="entity-trust-title">
    <div class="entity-trust-panel__head">
      <h2 id="entity-trust-title">Độ tin cậy dữ liệu</h2>
      <SourceMark :tier="tier" />
    </div>
    <FreshnessLine :status="freshnessStatus" :updated-label="updatedLabel" />
    <a v-if="sourceUrl" data-source-link :href="sourceUrl" target="_blank" rel="noopener nofollow">{{ sourceTitle }}</a>
    <span v-else data-source-label>{{ sourceTitle }}</span>
    <p>{{ note }}</p>
    <NuxtLink data-report-action :to="reportTo">Báo sai hoặc bổ sung nguồn</NuxtLink>
  </section>
</template>

<script setup lang="ts">
import type { FreshnessStatus, SourceTier } from '../utils/regionalColor'

defineProps<{
  tier: SourceTier
  sourceTitle: string
  sourceUrl?: string
  freshnessStatus: FreshnessStatus
  updatedLabel: string
  note: string
  reportTo: string
}>()
</script>

<style scoped>
.entity-trust-panel {
  display: grid;
  gap: var(--space-3);
  margin: var(--space-4) 0;
  padding: var(--space-4);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.entity-trust-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.entity-trust-panel h2,
.entity-trust-panel p {
  margin: 0;
}

.entity-trust-panel h2 {
  font-size: var(--text-base);
}

.entity-trust-panel p,
[data-source-label],
[data-source-link],
[data-report-action] {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

[data-source-label],
.entity-trust-panel p {
  color: var(--color-text-muted);
}

[data-source-link],
[data-report-action] {
  color: var(--color-action);
  overflow-wrap: anywhere;
  text-underline-offset: 2px;
}

[data-report-action] {
  width: fit-content;
  font-weight: var(--weight-semibold);
}

:is([data-source-link], [data-report-action]):focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
</style>
