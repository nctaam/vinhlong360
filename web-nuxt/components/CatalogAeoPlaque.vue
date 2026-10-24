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
            <span class="catalog-aeo-plaque__stamp sr-only" title="Dữ liệu bản địa được đối soát">
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
  kicker: 'Góc nhìn bản địa · Giải đáp nhanh',
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
  padding-block: var(--space-8);
}

.catalog-aeo-plaque__frame {
  --aeo-sheet-radius: var(--radius-sheet);
  max-inline-size: var(--maxw);
  margin-inline: auto;
  padding: var(--space-7) 0;
  border-block: 1px solid color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 28%, var(--color-border));
  border-inline: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transition: border-color 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  contain: layout style paint;
}

@media (min-width: 900px) {
  .catalog-aeo-plaque__frame {
    display: grid;
    grid-template-columns: minmax(15rem, 0.34fr) minmax(0, 0.66fr);
    gap: var(--space-4) var(--space-8);
    align-items: start;
  }

  .catalog-aeo-plaque__head {
    grid-column: 1;
    padding-inline-end: var(--space-6);
  }

  .catalog-aeo-plaque__content {
    grid-column: 2;
    grid-row: 1 / span 2;
    margin-bottom: 0;
  }

  .catalog-aeo-plaque__foot {
    grid-column: 1;
    justify-content: flex-start;
    border-top: 0;
    padding-top: 0;
    margin-top: var(--space-2);
  }
}

.catalog-aeo-plaque__head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.catalog-aeo-plaque__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  margin-top: 2px;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--tri-region-material-accent, var(--color-material-amber));
  font-size: 1.2rem;
  flex-shrink: 0;
}

.catalog-aeo-plaque__kicker-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
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
  color: var(--tri-region-material-accent, var(--color-brand));
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
  border-radius: var(--radius-pill);
  letter-spacing: normal;
}

.catalog-aeo-plaque__stamp-icon {
  font-size: 0.85em;
}

.catalog-aeo-plaque__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(1.3rem, 2.2vw, 1.68rem);
  font-weight: var(--weight-semibold);
  line-height: 1.2;
  letter-spacing: -0.015em;
  color: var(--color-text);
  text-wrap: balance;
}

.catalog-aeo-plaque__content {
  display: grid;
  grid-template-columns: repeat(var(--column-count, 2), 1fr);
  gap: var(--space-6);
  margin-bottom: var(--space-4);
  counter-reset: aeo-note;
}

@media (max-width: 768px) {
  .catalog-aeo-plaque__content {
    grid-template-columns: 1fr;
    gap: var(--space-5);
  }
}

.catalog-aeo-plaque__item {
  --aeo-item-radius: var(--radius-surface);
  counter-increment: aeo-note;
  display: flex;
  flex-direction: column;
  gap: var(--space-1h);
  padding: var(--space-1) 0 var(--space-1) var(--space-5);
  border-inline-start: 1px solid color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 32%, var(--color-border));
  border-radius: 0;
  background: transparent;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s var(--ease-out);
}

.catalog-aeo-plaque__item::before {
  content: counter(aeo-note, decimal-leading-zero);
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--tri-region-material-accent, var(--color-brand));
  line-height: 1;
  margin-bottom: 2px;
}

@media (hover: hover) and (pointer: fine) {
  .catalog-aeo-plaque__item:hover {
    border-inline-start-color: var(--tri-region-material-accent, var(--color-brand));
    transform: translateX(3px);
  }
}

.catalog-aeo-plaque__entry-title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(1.02rem, 1.25vw, 1.14rem);
  font-weight: var(--weight-semibold);
  line-height: 1.3;
  color: var(--color-text);
  text-wrap: pretty;
}

.catalog-aeo-plaque__dek {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
  text-wrap: pretty;
}

.catalog-aeo-plaque__foot {
  display: flex;
  justify-content: flex-start;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
  margin-top: var(--space-2);
}

.catalog-aeo-plaque__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-3) var(--space-2) 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-action, var(--color-text));
  text-decoration: none;
  border-radius: var(--radius-control);
  transition: color 150ms var(--ease-out), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.catalog-aeo-plaque__cta:hover {
  color: var(--tri-region-material-accent, var(--color-brand));
  transform: translateX(2px);
}

.catalog-aeo-plaque__cta:active {
  transform: scale(0.98);
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
  transform: translateX(4px);
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
