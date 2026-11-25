<template>
  <section class="home-culinary-trail block reveal" :aria-label="culinaryCfg.ariaLabel" data-home-culinary-trail>
    <div class="home-culinary-trail__head section-head">
      <div class="sh-text">
        <span class="home-culinary-trail__eyebrow" data-color-role="brand">
          <IconLine name="bowl" aria-hidden="true" />
          <span>{{ culinaryCfg.eyebrow }}</span>
        </span>
        <h2>{{ culinaryCfg.title }}</h2>
        <p class="sh-sub">{{ culinaryCfg.subtitle }}</p>
      </div>
      <NuxtLink to="/am-thuc" class="see-all">
        <span>{{ culinaryCfg.seeAllLabel }}</span>
        <IconLine name="arrow-right" class="inline-arrow" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- 4-Column Light Print Gallery: 0 Scrims, 0 Pills Over Food, 0 Orphan Slots -->
    <div class="home-culinary-trail__grid">
      <article
        v-for="dish in SIGNATURE_DISHES"
        :key="dish.id"
        class="home-culinary-card"
        data-culinary-card
      >
        <NuxtLink :to="dish.to" class="home-culinary-card__media" tabindex="-1" aria-hidden="true">
          <img
            class="home-culinary-card__img"
            :src="dish.coverSrc"
            :alt="dish.name"
            width="600"
            height="450"
            loading="lazy"
            decoding="async"
            @error="onImgFallback"
          >
        </NuxtLink>

        <div class="home-culinary-card__body">
          <div class="home-culinary-card__meta">
            <span class="home-culinary-card__origin">{{ dish.origin }}</span>
            <span class="home-culinary-card__price-badge">{{ dish.priceRange }}</span>
          </div>

          <h3 class="home-culinary-card__title">
            <NuxtLink :to="dish.to">{{ dish.name }}</NuxtLink>
          </h3>

          <p class="home-culinary-card__venue">
            <IconLine name="pin" aria-hidden="true" />
            <span>{{ dish.reputableVenue }}</span>
          </p>

          <div class="home-culinary-card__action">
            <NuxtLink :to="dish.mapTo" class="home-culinary-card__btn">
              <IconLine name="map" aria-hidden="true" />
              <span>Vị trí & Chỉ đường</span>
              <IconLine name="arrow-right" class="home-culinary-card__arrow" aria-hidden="true" />
            </NuxtLink>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import IconLine from '~/components/IconLine.vue'
import { PROVINCE_CONFIG, type ProvinceCulinaryDish } from '~/utils/provinceConfig'

type CulinaryDish = ProvinceCulinaryDish

const culinaryCfg = PROVINCE_CONFIG.home.culinaryTrail
const SIGNATURE_DISHES: readonly CulinaryDish[] = culinaryCfg.dishes

function onImgFallback(e: Event) {
  const img = e.target as HTMLImageElement
  if (img && !img.dataset.fallbackApplied) {
    img.dataset.fallbackApplied = 'true'
    img.src = culinaryCfg.fallbackImage
  }
}
</script>

<style scoped>
.home-culinary-trail {
  max-width: var(--maxw);
  margin-inline: auto;
  padding-inline: var(--space-5);
  padding-block: clamp(var(--space-8), 5vw, var(--space-12));
  border-block-start: 1px solid var(--color-border);
}

.home-culinary-trail__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  margin-block-end: var(--space-2);
}

.home-culinary-trail__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
  margin-block-start: var(--space-6);
}

@media (min-width: 600px) {
  .home-culinary-trail__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .home-culinary-trail__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--space-5);
    align-items: stretch;
  }
}

/* Light Print Folio Card (clean canvas below, pure macro dish photo on top) */
.home-culinary-card {
  display: flex;
  flex-direction: column;
  background: transparent;
  border-block-start: 1px solid var(--color-border);
  padding-block-start: var(--space-3);
  transition: border-color 0.2s ease;
}

.home-culinary-card:hover {
  border-color: var(--color-brand);
}

.home-culinary-card:active {
  transform: scale(0.99);
}

.home-culinary-card:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
  border-radius: var(--radius-control);
}

.home-culinary-card__media {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-surface);
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.home-culinary-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.home-culinary-card:hover .home-culinary-card__img {
  transform: scale(1.04);
}

.home-culinary-card__body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-2);
  padding-block-start: var(--space-3);
  min-width: 0;
}

.home-culinary-card__meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.home-culinary-card__origin {
  font-size: var(--text-2xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.home-culinary-card__price-badge {
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--color-brand);
  white-space: nowrap;
}

.home-culinary-card__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  line-height: 1.3;
  text-wrap: balance;
  overflow-wrap: break-word;
}

.home-culinary-card__title a {
  color: var(--color-text);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-culinary-card__title a:hover {
  color: var(--color-action);
}

.home-culinary-card__title a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-culinary-card__venue {
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.45;
  text-wrap: pretty;
}

.home-culinary-card__venue .line-icon {
  color: var(--color-brand);
  flex-shrink: 0;
  margin-block-start: 2px;
}

.home-culinary-card__action {
  margin-top: auto;
  padding-top: var(--space-1);
}

.home-culinary-card__btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-action);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  text-decoration: none;
  transition: color 0.2s ease;
}

.home-culinary-card__btn:hover {
  color: var(--color-brand);
}

.home-culinary-card__btn:active {
  transform: scale(0.98);
}

.home-culinary-card__btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}

.home-culinary-card__arrow {
  transition: transform 0.2s ease;
}

.home-culinary-card:hover .home-culinary-card__arrow,
.home-culinary-card__btn:hover .home-culinary-card__arrow {
  transform: translateX(3px);
}

@media (prefers-reduced-motion: reduce) {
  .home-culinary-card,
  .home-culinary-card__img,
  .home-culinary-card__arrow {
    transition: none;
  }
}
</style>
