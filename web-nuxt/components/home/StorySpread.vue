<template>
  <section class="spread" aria-labelledby="spread-title">
    <div class="spread-img" ref="imgEl">
      <img
        :src="image"
        :srcset="srcset"
        sizes="100vw"
        loading="lazy"
        decoding="async"
        alt=""
      />
    </div>
    <div class="spread-scrim" aria-hidden="true" />
    <div class="spread-copy">
      <span class="spread-kicker">{{ kicker }}</span>
      <h2 id="spread-title" class="spread-title">{{ title }}</h2>
      <p class="spread-sub">{{ subtitle }}</p>
      <NuxtLink v-if="ctaTo" :to="ctaTo" class="btn btn-primary spread-cta">{{ ctaText }} →</NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  image: string
  srcset?: string
  kicker: string
  title: string
  subtitle: string
  ctaText?: string
  ctaTo?: string
}>(), {
  srcset: '',
  ctaText: '',
  ctaTo: '',
})

const imgEl = ref<HTMLElement | null>(null)
useParallax(() => (imgEl.value ? [imgEl.value] : []), { intensity: 0.12 })
</script>

<style scoped>
/* ═══════════════════════════════════════════════════
   STORYSPREAD — full-bleed signature moment (Ken Burns + parallax)
   Breaks out of the page container edge-to-edge. Below the fold —
   image is lazy-loaded; a fixed min-height prevents CLS.
   ═══════════════════════════════════════════════════ */
.spread {
  position: relative;
  width: 100vw;
  margin-inline: calc(50% - 50vw);
  min-height: clamp(24rem, 60vh, 40rem);
  overflow: hidden;
  display: grid;
  place-items: center;
  isolation: isolate;
  color: var(--text-on-dark, #fff);
}

.spread-img {
  position: absolute;
  inset: -6%;
  z-index: -2;
  transform: translate3d(0, var(--parallax, 0), 0) scale(1.06);
  animation: spread-kenburns var(--dur-kenburns, 24s) var(--ease-in-out) infinite alternate;
  will-change: transform;
}
.spread-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  display: block;
}
@keyframes spread-kenburns {
  0%   { transform: translate3d(0, var(--parallax, 0), 0) scale(1.06) translate(0, 0); }
  100% { transform: translate3d(0, var(--parallax, 0), 0) scale(1.12) translate(-1.4%, -1%); }
}

.spread-scrim {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--scrim-hero);
  pointer-events: none;
}

.spread-copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
  max-width: var(--measure-read, 68ch);
  padding: var(--space-8) var(--space-5);
}
.spread-kicker {
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: .18em;
  color: rgba(255, 255, 255, .85);
}
.spread-title {
  margin: 0;
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(2rem, 1.5rem + 3.2vw, 3.5rem);
  line-height: var(--leading-tight);
  letter-spacing: -.01em;
  color: var(--text-on-dark, #fff);
  text-wrap: balance;
  text-shadow: 0 2px 24px rgba(0, 0, 0, .35);
}
.spread-sub {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(1.05rem, 1rem + .4vw, 1.25rem);
  line-height: var(--leading-relaxed);
  color: rgba(255, 255, 255, .90);
  text-wrap: balance;
}
.spread-cta {
  margin-top: var(--space-2);
}

/* ── Reduced motion: freeze both Ken Burns and parallax ── */
@media (prefers-reduced-motion: reduce) {
  .spread-img {
    animation: none;
    transform: none;
  }
}
</style>
