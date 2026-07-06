<template>
  <section class="spread" aria-labelledby="spread-title">
    <div class="spread-img" ref="imgEl">
      <img
        :src="image"
        :srcset="srcset"
        sizes="100vw"
        loading="lazy"
        decoding="async"
        :alt="imageAlt"
      />
    </div>
    <div class="spread-scrim" aria-hidden="true" />
    <div class="spread-copy">
      <span class="spread-kicker"><span class="spread-tick" aria-hidden="true" />{{ kicker }}</span>
      <h2 id="spread-title" class="spread-title">{{ title }}</h2>
      <p class="spread-sub">{{ subtitle }}</p>
      <NuxtLink v-if="ctaTo" :to="ctaTo" class="btn btn-primary spread-cta">{{ ctaText }} →</NuxtLink>
    </div>
    <!-- Signature: phù-sa stratum — the alluvial layer (river→amber→clay) that
         built this delta, rendered as the spread's ground line. -->
    <div class="spread-stratum" aria-hidden="true" />
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
  /** Descriptive alt for the signature image (empty = decorative). */
  imageAlt?: string
}>(), {
  srcset: '',
  ctaText: '',
  ctaTo: '',
  imageAlt: '',
})

const imgEl = ref<HTMLElement | null>(null)
useParallax(() => (imgEl.value ? [imgEl.value] : []), { intensity: 0.12 })
</script>

<style scoped>
/* ═══════════════════════════════════════════════════
   STORYSPREAD — full-bleed signature moment (Ken Burns + parallax).
   Copy anchored lower-LEFT (rule-of-thirds), not centered; boldness spent on
   the phù-sa stratum band at the ground line. Below the fold — image lazy-loads;
   fixed min-height prevents CLS.
   ═══════════════════════════════════════════════════ */
.spread {
  position: relative;
  width: 100vw;
  margin-inline: calc(50% - 50vw);
  min-height: clamp(26rem, 64vh, 42rem);
  overflow: hidden;
  display: grid;
  align-items: end;        /* anchor copy to the bottom … */
  justify-items: start;    /* … and the left (was place-items:center) */
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

/* Directional scrim — heaviest at the bottom-left where the copy sits, fading to
   near-clear top-right so the imagery still breathes. */
.spread-scrim {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(
    to top right,
    rgba(8, 9, 12, .84) 0%,
    rgba(8, 9, 12, .52) 40%,
    rgba(8, 9, 12, .14) 78%,
    rgba(8, 9, 12, .04) 100%
  );
  pointer-events: none;
}

.spread-copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  gap: var(--space-3);
  max-width: 44ch;
  padding: var(--space-8) var(--space-6);
  /* generous left inset on wide screens; clears the stratum band at the bottom */
  padding-inline-start: clamp(var(--space-5), 6vw, var(--space-16));
  padding-block-end: calc(var(--space-10) + var(--space-4));
}
.spread-kicker {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: .18em;
  color: rgba(255, 255, 255, .88);
}
/* phù-sa tick — same river→amber→clay recipe as .sediment-head, tying the
   signature moment back to the site's one motif. */
.spread-tick {
  width: 26px;
  height: 3px;
  margin-inline-end: 10px;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-500) 52%, var(--clay-500, #C4694E) 100%);
}
.spread-title {
  margin: 0;
  font-family: var(--font-editorial);
  font-weight: 600;
  font-size: clamp(2.1rem, 1.5rem + 3.6vw, 3.75rem);
  line-height: var(--leading-tight);
  letter-spacing: -.015em;
  color: var(--text-on-dark, #fff);
  text-wrap: balance;
  text-shadow: 0 2px 24px rgba(0, 0, 0, .4);
}
.spread-sub {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: clamp(1.05rem, 1rem + .4vw, 1.25rem);
  line-height: var(--leading-relaxed);
  color: rgba(255, 255, 255, .92);
  text-wrap: pretty;
  text-shadow: 0 1px 12px rgba(0, 0, 0, .4);
}
.spread-cta {
  margin-top: var(--space-2);
}

/* ── Signature: phù-sa stratum ───────────────────────────────────────────────
   A substantial layered band across the ground line — the three lands as one
   sediment story (river silt → amber → clay). Grain gives it materiality so it
   reads as an alluvial stratum, not a flat progress bar. */
.spread-stratum {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  height: clamp(12px, 1.7vh, 18px);
  background: linear-gradient(
    90deg,
    var(--river-600) 0%, var(--river-600) 20%,
    var(--amber-600) 42%, var(--amber-500) 56%,
    var(--clay-600) 80%, var(--clay-600) 100%
  );
  box-shadow: 0 -1px 0 rgba(0, 0, 0, .28), 0 -10px 26px rgba(0, 0, 0, .20);
}
.spread-stratum::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: var(--grain);
  background-size: 120px 120px;
  opacity: .5;
  mix-blend-mode: overlay;
}
/* a hairline of light along the top edge lifts the band off the imagery */
.spread-stratum::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 1px;
  background: rgba(255, 255, 255, .22);
}

/* ── Reduced motion: freeze both Ken Burns and parallax ── */
@media (prefers-reduced-motion: reduce) {
  .spread-img {
    animation: none;
    transform: none;
  }
}
</style>
