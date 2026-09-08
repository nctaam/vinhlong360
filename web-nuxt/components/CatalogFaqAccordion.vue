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
  gap: var(--space-3);
}

.catalog-faq-item {
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--card);
  overflow: hidden;
  transition: border-color 0.2s var(--ease-out), box-shadow 0.2s var(--ease-out);
}

.catalog-faq-item:hover {
  border-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 30%, var(--line));
}

.catalog-faq-item[open] {
  border-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 55%, var(--line));
  box-shadow: 0 4px 12px -2px rgba(var(--black-rgb), 0.04);
}

.catalog-faq-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  cursor: pointer;
  user-select: none;
  list-style: none;
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
  padding: 0 var(--space-5) var(--space-5);
  border-top: 1px solid transparent;
}

.catalog-faq-item[open] .catalog-faq-answer {
  border-top-color: color-mix(in srgb, var(--line) 60%, transparent);
  padding-top: var(--space-3);
}

.catalog-faq-answer p {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--muted);
}

/* Dark mode */
.dark .catalog-faq-item {
  border-color: rgba(var(--white-rgb), 0.08);
}

.dark .catalog-faq-item:hover {
  border-color: rgba(var(--white-rgb), 0.16);
}

.dark .catalog-faq-item[open] {
  border-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 50%, rgba(var(--white-rgb), 0.2));
  box-shadow: 0 4px 14px -2px rgba(var(--black-rgb), 0.28);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .catalog-faq-item,
  .catalog-faq-chevron {
    transition: none;
  }
}
</style>
