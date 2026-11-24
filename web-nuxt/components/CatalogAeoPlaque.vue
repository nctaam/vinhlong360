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

      <details class="catalog-aeo-plaque__details">
        <summary class="catalog-aeo-plaque__summary">
          <span>Xem {{ resolvedEntries.length }} điểm tóm lược thực địa</span>
          <IconLine name="chevron-down" class="catalog-aeo-plaque__chevron" aria-hidden="true" />
        </summary>

        <div class="catalog-aeo-plaque__content" :style="{ '--column-count': Math.min(resolvedEntries.length, 3) }">
          <article
            v-for="(item, idx) in resolvedEntries"
            :key="idx"
            class="catalog-aeo-plaque__item"
          >
            <div v-if="item.coverSrc" class="catalog-aeo-plaque__media">
              <img
                :src="item.coverSrc"
                :alt="item.heading"
                class="catalog-aeo-plaque__img"
                width="480"
                height="270"
                loading="lazy"
                decoding="async"
              >
            </div>
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
      </details>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  kicker?: string
  accent?: 'amber' | 'clay' | 'leaf' | 'river' | 'neutral'
  icon?: string
  entries: Array<{ heading: string; text: string; tag?: string; coverSrc?: string }>
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

const resolvedEntries = computed(() => props.entries || [])
</script>

<style scoped>
.catalog-aeo-plaque {
  padding-block: var(--space-5);
}

.catalog-aeo-plaque__frame {
  --aeo-sheet-radius: var(--radius-sheet);
  max-inline-size: var(--maxw);
  margin-inline: auto;
  padding: var(--space-5) 0;
  border-block: 1px solid color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 28%, var(--color-border));
  border-inline: 0;
  contain: layout style paint;
}

.catalog-aeo-plaque__head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.catalog-aeo-plaque__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  margin-top: 2px;
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
}

.catalog-aeo-plaque__stamp-icon {
  font-size: 0.85em;
}

.catalog-aeo-plaque__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(1.2rem, 2vw, 1.52rem);
  font-weight: var(--weight-semibold);
  line-height: 1.25;
  letter-spacing: -0.015em;
  color: var(--color-text);
  text-wrap: balance;
}

.catalog-aeo-plaque__summary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  margin-top: var(--space-2);
  padding-inline-start: calc(1.75rem + var(--space-3));
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-action, var(--color-text));
  cursor: pointer;
  list-style: none;
  user-select: none;
}

.catalog-aeo-plaque__summary::-webkit-details-marker {
  display: none;
}

.catalog-aeo-plaque__summary:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.catalog-aeo-plaque__chevron {
  width: 1rem;
  height: 1rem;
  transition: transform 0.2s var(--ease-out);
}

.catalog-aeo-plaque__details[open] .catalog-aeo-plaque__chevron {
  transform: rotate(180deg);
}

.catalog-aeo-plaque__details::details-content {
  interpolate-size: allow-keywords;
  overflow: clip;
  contain: layout;
}

.catalog-aeo-plaque__details:not([open])::details-content {
  block-size: 0;
}

@media (prefers-reduced-motion: no-preference) {
  .catalog-aeo-plaque__details::details-content {
    transition: block-size, content-visibility, display;
    transition-duration: 0.28s;
    transition-timing-function: var(--ease-out-expo, ease-in-out);
    transition-behavior: allow-discrete;
  }
}

.catalog-aeo-plaque__content {
  display: grid;
  grid-template-columns: repeat(var(--column-count, 2), 1fr);
  gap: var(--space-6);
  margin-top: var(--space-4);
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
  counter-increment: aeo-note;
  display: flex;
  flex-direction: column;
  gap: var(--space-1h);
  padding: var(--space-1) 0 var(--space-1) var(--space-5);
  border-inline-start: 1px solid color-mix(in srgb, var(--tri-region-material-accent, var(--color-brand)) 32%, var(--color-border));
  transition: border-color 0.2s var(--ease-out);
}

.catalog-aeo-plaque__media {
  overflow: clip;
  border-radius: var(--radius-surface);
  aspect-ratio: 16 / 10;
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.catalog-aeo-plaque__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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
  .catalog-aeo-plaque__cta,
  .catalog-aeo-plaque__chevron {
    transform: none !important;
    transition: none !important;
  }
}
</style>
