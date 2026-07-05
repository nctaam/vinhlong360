<template>
  <section class="ef" :class="`ef-${side}`">
    <NuxtLink :to="ctaTo" class="ef-visual" :aria-label="title">
      <div class="ef-img" ref="imgEl" :style="{ backgroundImage: `url(${image})` }" />
    </NuxtLink>
    <div class="ef-body">
      <span class="ef-kicker">{{ kicker }}</span>
      <h2 class="ef-title">{{ title }}</h2>
      <p class="ef-lede">{{ lede }}</p>
      <div v-if="thumbs?.length" class="ef-thumbs">
        <EntityCard v-for="t in thumbs.slice(0, 3)" :key="t.id" :entity="t" />
      </div>
      <NuxtLink :to="ctaTo" class="btn btn-primary ef-cta">{{ ctaText }} →</NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'

const props = withDefaults(defineProps<{
  image: string
  kicker: string
  title: string
  lede: string
  ctaText: string
  ctaTo: string
  thumbs?: Entity[]
  side?: 'left' | 'right'
  priority?: boolean
}>(), {
  side: 'left',
  priority: false,
})

const imgEl = ref<HTMLElement | null>(null)
useParallax(() => (imgEl.value ? [imgEl.value] : []), { intensity: 0.05 })

// LCP-critical image (Feature #1 only) — preload so the browser fetches it
// before it discovers the background-image via the compiled CSS.
if (props.priority) {
  useHead({
    link: [{ rel: 'preload', as: 'image', href: props.image }],
  })
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════
   ENTITYFEATURE — photo-led editorial magazine block
   ═══════════════════════════════════════════════════ */
.ef {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: var(--space-8);
  align-items: center;
}
.ef-right { grid-template-columns: 1fr 1.1fr; }
.ef-right .ef-visual { order: 2; }
.ef-right .ef-body { order: 1; }

.ef-visual {
  position: relative;
  display: block;
  overflow: hidden;
  border-radius: var(--radius-lg);
  aspect-ratio: var(--ratio-hero);
  isolation: isolate;
  box-shadow: var(--shadow-md);
}
.ef-img {
  position: absolute;
  inset: 0;
  width: 100%;
  /* Over-height so the parallax translate has room to move without exposing edges. */
  height: 120%;
  top: -10%;
  background-size: cover;
  background-position: center;
  transform: translate3d(0, var(--parallax, 0), 0);
  will-change: transform;
}
/* Subtle warm scrim at the base — grounds the image against the body copy on mobile
   stack and gives a touch of depth without a glassy overlay. */
.ef-visual::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: linear-gradient(to top, rgba(8, 9, 12, .22) 0%, transparent 32%);
  opacity: 0;
  transition: opacity var(--duration-slow) var(--ease-out);
}
.ef-visual:hover::after { opacity: 1; }
.ef-visual:hover .ef-img { transform: translate3d(0, var(--parallax, 0), 0) scale(1.03); }
.ef-visual:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }

.ef-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  min-width: 0;
}
.ef-kicker {
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: .14em;
  color: var(--accent-text);
}
.ef-title {
  margin: 0;
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(1.75rem, 1.4rem + 2.4vw, 2.75rem);
  line-height: var(--leading-tight);
  letter-spacing: -.01em;
  color: var(--ink);
  text-wrap: balance;
}
.ef-lede {
  margin: 0;
  max-width: var(--measure-read, 68ch);
  font-family: var(--font-editorial);
  font-size: clamp(1.05rem, 1rem + .35vw, 1.2rem);
  line-height: var(--leading-relaxed);
  color: var(--muted);
}
.ef-lede::first-letter {
  font-family: var(--font-editorial);
  font-weight: 600;
  float: left;
  font-size: 3.2em;
  line-height: .82;
  padding: .05em .1em 0 0;
  color: var(--primary);
}

.ef-thumbs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  width: 100%;
  margin-top: var(--space-1);
}

.ef-cta {
  margin-top: var(--space-2);
}

/* ── Stack to 1 column under 760px ── */
@media (max-width: 760px) {
  .ef { grid-template-columns: 1fr; gap: var(--space-5); }
  .ef-right .ef-visual, .ef-right .ef-body { order: initial; }
  .ef-thumbs { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-2); }
}
@media (max-width: 480px) {
  .ef-thumbs { grid-template-columns: 1fr 1fr; }
  .ef-thumbs :deep(.card:nth-child(3)) { display: none; }
}

/* ── Reduced motion: parallax composable already no-ops the JS; also freeze the
   hover scale/translate transitions so nothing moves on interaction. ── */
@media (prefers-reduced-motion: reduce) {
  .ef-img { transition: none; }
  .ef-visual:hover .ef-img { transform: translate3d(0, var(--parallax, 0), 0); }
  .ef-visual::after { transition: none; }
}
</style>
