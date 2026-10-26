<template>
  <section v-if="items.length" class="catalog-faq block" aria-labelledby="catalog-faq-title">
    <div class="catalog-faq-head sediment-head">
      <div class="catalog-faq-meta">
        <span class="catalog-faq-kicker">{{ kicker }}</span>
        <span class="catalog-faq-stamp">
          <IconLine name="shield-check" class="catalog-faq-stamp-icon" aria-hidden="true" />
          <span>Thông tin xác thực</span>
        </span>
      </div>
      <h2 id="catalog-faq-title" class="catalog-faq-title">{{ title }}</h2>
    </div>

    <div class="catalog-faq-list">
      <details
        v-for="(item, index) in items"
        :key="index"
        class="catalog-faq-item"
      >
        <summary class="catalog-faq-summary">
          <span class="catalog-faq-q">{{ item.q }}</span>
          <IconLine name="chevron-down" class="catalog-faq-chevron" aria-hidden="true" />
        </summary>
        <div class="catalog-faq-answer">
          <p>{{ item.a }}</p>
        </div>
      </details>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { FaqItem } from '~/composables/useSeoHelpers'

withDefaults(defineProps<{
  items: FaqItem[]
  title?: string
  kicker?: string
}>(), {
  title: 'Câu hỏi thường gặp',
  kicker: 'Hỏi đáp · Cẩm nang thực địa',
})
</script>

<style scoped>
.catalog-faq {
  margin-top: var(--space-8);
  margin-bottom: var(--space-8);
}

.catalog-faq-head {
  margin-bottom: var(--space-5);
}

.catalog-faq-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
}

.catalog-faq-kicker {
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--muted);
}

.catalog-faq-stamp {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  color: var(--muted);
}

.catalog-faq-stamp-icon {
  width: 0.85rem;
  height: 0.85rem;
  color: var(--tri-region-material-accent, var(--color-brand));
}

.catalog-faq-title {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--ink);
}

.catalog-faq-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  counter-reset: faq-entry;
  border-block-start: 1px solid var(--line);
}

.catalog-faq-item {
  counter-increment: faq-entry;
  border: 0;
  border-block-end: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  overflow: hidden;
  transition: background-color 0.2s var(--ease-out);
}

.catalog-faq-item:hover {
  background: color-mix(in srgb, var(--bg-warm) 55%, transparent);
}

.catalog-faq-item[open] {
  background: color-mix(in srgb, var(--card) 65%, transparent);
}

.catalog-faq-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.catalog-faq-q {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.catalog-faq-q::before {
  content: counter(faq-entry, decimal-leading-zero);
  font-family: var(--font-editorial);
  font-style: italic;
  font-weight: 500;
  font-size: var(--text-lg);
  color: var(--tri-region-material-accent, var(--color-brand));
  flex-shrink: 0;
}

.catalog-faq-summary::-webkit-details-marker {
  display: none;
}

.catalog-faq-chevron {
  flex-shrink: 0;
  width: 1.15rem;
  height: 1.15rem;
  color: var(--muted);
  transition: transform 0.2s var(--ease-out), color 0.2s var(--ease-out);
}

.catalog-faq-item[open] .catalog-faq-chevron {
  transform: rotate(180deg);
  color: var(--tri-region-material-accent, var(--color-brand));
}

.catalog-faq-answer {
  padding: 0 0 var(--space-4) var(--space-6);
}

.catalog-faq-answer p {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--muted);
}

/* Dark mode */
.dark .catalog-faq-item {
  border-color: var(--line);
}

.dark .catalog-faq-item:hover {
  background: rgba(var(--white-rgb), 0.02);
}

.dark .catalog-faq-item[open] {
  background: rgba(var(--white-rgb), 0.03);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .catalog-faq-item,
  .catalog-faq-chevron {
    transition: none;
  }
}
</style>
