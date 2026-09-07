<template>
  <section
    class="catalog-aeo-plaque"
    data-catalog-aeo-plaque
    :data-material-accent="accent"
    :aria-labelledby="titleId"
  >
    <div class="catalog-aeo-plaque__frame">
      <div class="catalog-aeo-plaque__head">
        <span class="catalog-aeo-plaque__icon" aria-hidden="true">
          <IconLine :name="icon || 'bulb'" />
        </span>
        <div class="catalog-aeo-plaque__kicker-group">
          <span class="catalog-aeo-plaque__kicker">{{ kicker }}</span>
          <h2 :id="titleId" class="catalog-aeo-plaque__title">{{ title }}</h2>
        </div>
      </div>

      <div class="catalog-aeo-plaque__content" :style="{ '--column-count': Math.min(entries.length, 3) }">
        <article
          v-for="(item, idx) in entries"
          :key="idx"
          class="catalog-aeo-plaque__item"
        >
          <h3 class="catalog-aeo-plaque__entry-title">{{ item.heading }}</h3>
          <p class="catalog-aeo-plaque__dek">{{ item.text }}</p>
        </article>
      </div>

      <div v-if="ctaTo && ctaLabel" class="catalog-aeo-plaque__foot">
        <NuxtLink :to="ctaTo" class="catalog-aeo-plaque__cta" data-catalog-aeo-cta>
          <span>{{ ctaLabel }}</span>
          <span class="catalog-aeo-plaque__arrow" aria-hidden="true"><IconLine name="arrow-right" /></span>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useId } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  kicker?: string
  accent?: 'amber' | 'clay' | 'leaf' | 'river' | 'neutral'
  icon?: string
  entries: Array<{ heading: string; text: string }>
  ctaTo?: string
  ctaLabel?: string
}>(), {
  kicker: 'Góc nhìn bản địa · Giải đáp nhanh AEO',
  accent: 'amber',
  icon: 'bulb',
  ctaTo: '',
  ctaLabel: '',
})

const instanceId = useId().replace(/[^A-Za-z0-9_-]+/g, '-')
const titleId = `catalog-aeo-title-${instanceId}`
</script>

<style scoped>
.catalog-aeo-plaque {
  padding-block: var(--space-6);
}

.catalog-aeo-plaque__frame {
  max-inline-size: 56rem;
  margin-inline: auto;
  padding: var(--space-6) var(--space-6);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--tri-region-material-accent, var(--color-material-amber));
  border-radius: var(--radius-sheet);
  background: var(--color-canvas);
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.05), 0 0 0 1px rgba(var(--white-rgb), 0.5);
  contain: layout style paint;
}

.dark .catalog-aeo-plaque__frame {
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.2), 0 0 0 1px rgba(var(--white-rgb), 0.08);
}

.catalog-aeo-plaque__head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.catalog-aeo-plaque__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-full);
  background: rgba(var(--black-rgb), 0.04);
  color: var(--tri-region-material-accent, var(--color-material-amber));
  font-size: 1.25rem;
  flex-shrink: 0;
}

.dark .catalog-aeo-plaque__icon {
  background: rgba(var(--white-rgb), 0.08);
}

.catalog-aeo-plaque__kicker-group {
  display: flex;
  flex-direction: column;
}

.catalog-aeo-plaque__kicker {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.catalog-aeo-plaque__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-xl);
  line-height: var(--leading-tight);
  color: var(--color-text);
}

.catalog-aeo-plaque__content {
  display: grid;
  grid-template-columns: repeat(var(--column-count, 2), 1fr);
  gap: var(--space-5);
  margin-bottom: var(--space-4);
}

@media (max-width: 768px) {
  .catalog-aeo-plaque__content {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
}

.catalog-aeo-plaque__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.catalog-aeo-plaque__entry-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.catalog-aeo-plaque__dek {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
}

.catalog-aeo-plaque__foot {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
  margin-top: var(--space-2);
}

.catalog-aeo-plaque__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-action, var(--color-text));
  text-decoration: none;
  border-radius: var(--radius-full);
  transition: background 150ms var(--ease-out);
}

.catalog-aeo-plaque__cta:hover {
  background: rgba(var(--black-rgb), 0.04);
}

.dark .catalog-aeo-plaque__cta:hover {
  background: rgba(var(--white-rgb), 0.08);
}

.catalog-aeo-plaque__cta:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.catalog-aeo-plaque__arrow {
  display: inline-flex;
  align-items: center;
  transition: transform 160ms var(--ease-out-expo);
}

.catalog-aeo-plaque__cta:hover .catalog-aeo-plaque__arrow {
  transform: translateX(3px);
}

@media (prefers-reduced-motion: reduce) {
  .catalog-aeo-plaque__arrow,
  .catalog-aeo-plaque__cta {
    transform: none !important;
    transition: none !important;
  }
}
</style>
