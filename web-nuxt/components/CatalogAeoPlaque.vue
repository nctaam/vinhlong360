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
          <div class="catalog-aeo-plaque__meta-row">
            <span class="catalog-aeo-plaque__kicker">{{ kicker }}</span>
            <span class="catalog-aeo-plaque__stamp" title="Dữ liệu bản địa được đối soát">
              <IconLine name="shield-check" class="catalog-aeo-plaque__stamp-icon" aria-hidden="true" />
              <span>Xác thực thực địa</span>
            </span>
          </div>
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
  box-shadow:
    0 2px 8px -2px rgba(var(--black-rgb), 0.05),
    0 0 0 1px rgba(var(--white-rgb), 0.5);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  contain: layout style paint;
}

.dark .catalog-aeo-plaque__frame {
  box-shadow:
    0 4px 14px -4px rgba(var(--black-rgb), 0.25),
    0 0 0 1px rgba(var(--white-rgb), 0.08);
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
  border-radius: var(--radius-pill, 999px);
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

.catalog-aeo-plaque__meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.catalog-aeo-plaque__kicker {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.catalog-aeo-plaque__stamp {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  color: var(--color-source-verified, var(--color-action));
  background: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 12%, transparent);
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-pill, 999px);
  letter-spacing: normal;
}

.catalog-aeo-plaque__stamp-icon {
  font-size: 0.85em;
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
  padding: var(--space-3);
  border-radius: var(--radius-surface);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.2s var(--ease-out);
}

.catalog-aeo-plaque__item:hover {
  background-color: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 4%, transparent);
  transform: translateY(-1px);
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
  border-radius: var(--radius-pill, 999px);
  transition: background 150ms var(--ease-out), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.catalog-aeo-plaque__cta:hover {
  background: color-mix(in srgb, var(--tri-region-material-accent, var(--color-material-amber)) 8%, transparent);
  transform: translateY(-1px);
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
  .catalog-aeo-plaque__frame,
  .catalog-aeo-plaque__item,
  .catalog-aeo-plaque__arrow,
  .catalog-aeo-plaque__cta {
    transform: none !important;
    transition: none !important;
  }
}
</style>
