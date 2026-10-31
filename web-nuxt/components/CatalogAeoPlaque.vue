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

      <div class="catalog-aeo-plaque__content" :style="{ '--column-count': Math.min(resolvedEntries.length, 3) }">
        <article
          v-for="(item, idx) in resolvedEntries"
          :key="idx"
          class="catalog-aeo-plaque__item"
          :class="{ 'has-image': Boolean(item.coverSrc) }"
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
            <span v-if="item.tag" class="catalog-aeo-plaque__tag">{{ item.tag }}</span>
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

const AEO_FALLBACK_COVERS: Record<string, string[]> = {
  amber: ['/img/cat-am-thuc.webp', '/img/cat-ocop.webp', '/img/spread/cu-lao-an-binh-640.webp'],
  clay: ['/img/entities/lang-gom-do-mang-thit.webp', '/img/area-vinh-long.webp', '/img/entities/van-thanh-mieu-vinh-long.webp'],
  leaf: ['/img/spread/cu-lao-an-binh-640.webp', '/img/area-ben-tre.webp', '/img/cat-du-lich.webp'],
  river: ['/img/spread/song-nuoc-640.webp', '/img/area-tra-vinh.webp', '/img/cat-lich-trinh.webp'],
  neutral: ['/img/area-vinh-long.webp', '/img/area-ben-tre.webp', '/img/area-tra-vinh.webp'],
}

function resolveDefaultEntryCover(
  item: { heading: string; text: string; tag?: string; coverSrc?: string },
  idx: number,
  accent: string,
): { coverSrc: string; tag?: string } {
  if (item.coverSrc) return { coverSrc: item.coverSrc, tag: item.tag }
  const h = `${item.heading} ${item.text}`.toLowerCase()
  if (h.includes('gốm') || h.includes('mang thít') || h.includes('lò gạch')) {
    return { coverSrc: '/img/entities/lang-gom-do-mang-thit.webp', tag: item.tag || 'Di sản Gốm Đỏ' }
  }
  if (h.includes('bến tre') || h.includes('xứ dừa') || h.includes('chợ lách') || h.includes('mỹ lồng')) {
    return { coverSrc: '/img/area-ben-tre.webp', tag: item.tag || 'Bến Tre · Xứ Dừa' }
  }
  if (h.includes('trà vinh') || h.includes('khmer') || h.includes('ao bà om') || h.includes('cầu kè')) {
    return { coverSrc: '/img/area-tra-vinh.webp', tag: item.tag || 'Trà Vinh · Văn hóa Khmer' }
  }
  if (h.includes('an bình') || h.includes('cù lao') || h.includes('nhà vườn')) {
    return { coverSrc: '/img/spread/cu-lao-an-binh-640.webp', tag: item.tag || 'Cù lao An Bình' }
  }
  if (h.includes('ocop') || h.includes('chứng nhận') || h.includes('sao')) {
    return { coverSrc: '/img/cat-ocop.webp', tag: item.tag || 'Chuẩn OCOP' }
  }
  if (h.includes('ẩm thực') || h.includes('món') || h.includes('đặc sản')) {
    return { coverSrc: '/img/cat-am-thuc.webp', tag: item.tag || 'Ẩm thực bản địa' }
  }
  if (h.includes('lưu trú') || h.includes('homestay') || h.includes('nghỉ dưỡng')) {
    return { coverSrc: '/img/cat-luu-tru.webp', tag: item.tag || 'Không gian lưu trú' }
  }
  if (h.includes('lễ hội') || h.includes('nghi thức') || h.includes('văn hóa')) {
    return { coverSrc: '/img/cat-le-hoi.webp', tag: item.tag || 'Di sản lễ hội' }
  }
  const pool = AEO_FALLBACK_COVERS[accent] ?? AEO_FALLBACK_COVERS.amber!
  return { coverSrc: pool[idx % pool.length]!, tag: item.tag }
}

const resolvedEntries = computed(() =>
  (props.entries || []).map((item, idx) => {
    const media = resolveDefaultEntryCover(item, idx, props.accent || 'amber')
    return {
      ...item,
      coverSrc: media.coverSrc,
      tag: media.tag,
    }
  }),
)
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

.catalog-aeo-plaque__item.has-image {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface, 12px);
  background: var(--color-surface);
  box-shadow: 0 4px 16px -4px rgba(var(--black-rgb), 0.04);
}

.catalog-aeo-plaque__item.has-image::before {
  margin-bottom: var(--space-1);
}

.catalog-aeo-plaque__media {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-control, 8px);
  aspect-ratio: 16 / 10;
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.catalog-aeo-plaque__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  display: block;
}

.catalog-aeo-plaque__tag {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-text);
  background: rgba(var(--white-rgb), 0.88);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 0.15rem var(--space-2);
  border-radius: var(--radius-control, 4px);
  box-shadow: 0 2px 6px rgba(var(--black-rgb), 0.08);
}

:root.dark .catalog-aeo-plaque__tag {
  background: color-mix(in srgb, var(--color-surface) 85%, transparent);
}

@media (hover: hover) and (pointer: fine) {
  .catalog-aeo-plaque__item.has-image:hover {
    border-color: var(--tri-region-material-accent, var(--color-brand));
    transform: translateY(-2px);
    box-shadow: 0 8px 24px -6px rgba(var(--black-rgb), 0.08);
  }
  .catalog-aeo-plaque__item.has-image:hover .catalog-aeo-plaque__img {
    transform: scale(1.04);
  }
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
