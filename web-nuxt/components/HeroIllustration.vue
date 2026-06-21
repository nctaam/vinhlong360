<script setup lang="ts">
/**
 * HeroIllustration — decorative region-themed SVG motif behind hero text.
 *
 * P1: parametric motif heroes. The default `variant="full"` keeps the original
 * homepage scene (Mekong river + palms + boat + fruit + sun) UNCHANGED, so any
 * existing `<HeroIllustration />` (no prop) renders exactly as before.
 *
 * Catalog pages get their motif via a CSS-only ::before layer in catalog.css
 * (keyed off the cat-* class), so they do NOT need to import this component.
 * The parametric variants here are available for any page that wants an inline
 * SVG motif (e.g. a future detail/landing hero).
 *
 * Decorative + additive: aria-hidden, pointer-events:none, pure SVG (SSR/no-JS
 * safe), respects prefers-reduced-motion (animation disabled).
 */
const props = withDefaults(
  defineProps<{
    /** Motif to render. 'full' = original homepage scene. */
    variant?: 'full' | 'waves' | 'fruit' | 'palm' | 'lotus'
  }>(),
  { variant: 'full' },
)

/**
 * Perf: pause the decorative infinite animations while the hero is scrolled
 * out of view. Purely additive + progressive — when in view (or if the
 * observer never runs, e.g. SSR / no-IO) the look is unchanged. Animations are
 * already transform/opacity (paint-cheap) and reduced-motion gated globally;
 * this just avoids spending compositor cycles on an off-screen hero.
 */
const root = ref<SVGSVGElement | null>(null)
onMounted(() => {
  if (!import.meta.client || typeof IntersectionObserver === 'undefined') return
  const el = root.value
  if (!el) return
  const io = new IntersectionObserver(
    ([entry]) => el.classList.toggle('is-offscreen', !entry.isIntersecting),
    { rootMargin: '120px' },
  )
  io.observe(el)
  onUnmounted(() => io.disconnect())
})
</script>

<template>
  <svg
    ref="root"
    class="hero-illustration"
    viewBox="0 0 600 400"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <!-- Reusable gradient defs (additive — only referenced by the upgraded full scene) -->
    <defs>
      <radialGradient id="hero-sun-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(232,163,61,.55)" />
        <stop offset="45%" stop-color="rgba(232,163,61,.18)" />
        <stop offset="100%" stop-color="rgba(232,163,61,0)" />
      </radialGradient>
      <linearGradient id="hero-river-sheen" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="rgba(255,255,255,0)" />
        <stop offset="50%" stop-color="rgba(255,255,255,.14)" />
        <stop offset="100%" stop-color="rgba(255,255,255,0)" />
      </linearGradient>
    </defs>

    <!-- ── FULL scene (original homepage) ── -->
    <template v-if="props.variant === 'full'">
      <!-- Atmospheric sun glow — soft warm halo gives the scene depth/focal warmth -->
      <circle class="hero-glow" cx="530" cy="60" r="150" fill="url(#hero-sun-glow)" />
      <!-- River -->
      <path d="M0 280 Q150 260 300 280 Q450 300 600 270 L600 400 L0 400Z" fill="rgba(255,255,255,.08)" />
      <path d="M0 300 Q120 285 280 300 Q440 315 600 290 L600 400 L0 400Z" fill="rgba(255,255,255,.05)" />
      <!-- River sheen — a slow horizontal shimmer that travels across the water -->
      <path class="hero-sheen" d="M0 290 Q140 273 290 290 Q450 307 600 280 L600 320 Q450 347 290 330 Q140 313 0 330Z" fill="url(#hero-river-sheen)" />
      <!-- Palm trees -->
      <g opacity=".15">
        <line x1="520" y1="280" x2="520" y2="160" stroke="#fff" stroke-width="4" />
        <path d="M520 160 Q490 140 460 155" stroke="#fff" stroke-width="3" fill="none" />
        <path d="M520 160 Q550 135 580 145" stroke="#fff" stroke-width="3" fill="none" />
        <path d="M520 160 Q510 130 495 125" stroke="#fff" stroke-width="3" fill="none" />
        <path d="M520 160 Q535 128 555 120" stroke="#fff" stroke-width="3" fill="none" />
        <path d="M520 165 Q485 155 470 170" stroke="#fff" stroke-width="2.5" fill="none" />
        <path d="M520 165 Q555 150 575 160" stroke="#fff" stroke-width="2.5" fill="none" />
      </g>
      <g opacity=".1" transform="translate(-80, 20)">
        <line x1="520" y1="280" x2="520" y2="180" stroke="#fff" stroke-width="3.5" />
        <path d="M520 180 Q495 162 468 175" stroke="#fff" stroke-width="2.5" fill="none" />
        <path d="M520 180 Q545 158 572 165" stroke="#fff" stroke-width="2.5" fill="none" />
        <path d="M520 180 Q512 152 498 148" stroke="#fff" stroke-width="2.5" fill="none" />
        <path d="M520 180 Q532 150 550 144" stroke="#fff" stroke-width="2.5" fill="none" />
      </g>
      <!-- Boat -->
      <g opacity=".12" transform="translate(80, 240)">
        <path d="M0 20 Q20 30 60 30 Q80 30 90 20 Q70 35 20 35Z" fill="#fff" />
        <line x1="40" y1="20" x2="40" y2="-5" stroke="#fff" stroke-width="2" />
        <path d="M42 -5 Q55 5 42 15" fill="rgba(255,255,255,.6)" />
      </g>
      <!-- Fruits cluster -->
      <g opacity=".1" transform="translate(480, 60)">
        <circle cx="0" cy="0" r="12" fill="#E8A33D" />
        <circle cx="22" cy="5" r="10" fill="#E8A33D" />
        <circle cx="8" cy="20" r="11" fill="#E8A33D" />
        <path d="M5 -14 Q8 -22 15 -18" stroke="#4BA97D" stroke-width="2" fill="none" />
      </g>
      <!-- Sun/moon -->
      <circle cx="530" cy="60" r="30" fill="rgba(232,163,61,.12)" />
      <circle cx="530" cy="60" r="22" fill="rgba(232,163,61,.08)" />
      <!-- Small waves -->
      <path d="M50 310 Q70 305 90 310 Q110 315 130 310" stroke="rgba(255,255,255,.08)" stroke-width="2" fill="none" />
      <path d="M200 320 Q220 315 240 320 Q260 325 280 320" stroke="rgba(255,255,255,.06)" stroke-width="2" fill="none" />
      <path d="M350 305 Q370 300 390 305 Q410 310 430 305" stroke="rgba(255,255,255,.07)" stroke-width="2" fill="none" />
    </template>

    <!-- ── WAVES motif (Mekong river) ── -->
    <g v-else-if="props.variant === 'waves'" class="motif motif-anim" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <path d="M-20 150 Q90 120 200 150 T420 150 T640 150" />
      <path d="M-20 210 Q90 180 200 210 T420 210 T640 210" />
      <path d="M-20 270 Q90 240 200 270 T420 270 T640 270" />
      <path d="M-20 330 Q90 300 200 330 T420 330 T640 330" />
    </g>

    <!-- ── FRUIT cluster (citrus / produce) ── -->
    <g v-else-if="props.variant === 'fruit'" class="motif" fill="none" stroke="currentColor" stroke-width="2.5" transform="translate(360, 90)">
      <circle cx="0" cy="40" r="48" />
      <circle cx="72" cy="74" r="38" />
      <circle cx="20" cy="118" r="42" />
      <path d="M-18 -8 Q-6 -36 22 -26" stroke-linecap="round" />
      <path d="M0 -10 Q20 -34 44 -24" stroke-linecap="round" />
    </g>

    <!-- ── PALM (coconut) ── -->
    <g v-else-if="props.variant === 'palm'" class="motif" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" transform="translate(120, 0)">
      <path d="M300 400 Q312 240 304 120" />
      <path d="M304 120 Q244 88 182 112" />
      <path d="M304 120 Q364 84 426 104" />
      <path d="M304 120 Q284 64 252 44" />
      <path d="M304 120 Q330 60 372 44" />
      <path d="M304 132 Q250 126 210 154" />
      <path d="M304 132 Q360 120 402 144" />
    </g>

    <!-- ── LOTUS (festival) ── -->
    <g v-else-if="props.variant === 'lotus'" class="motif" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" transform="translate(190, 60)">
      <path d="M120 300 Q120 200 120 150" />
      <path d="M120 150 Q70 190 66 290 Q116 260 120 150" />
      <path d="M120 150 Q170 190 174 290 Q124 260 120 150" />
      <path d="M120 160 Q30 188 14 280 Q90 264 120 160" />
      <path d="M120 160 Q210 188 226 280 Q150 264 120 160" />
      <path d="M120 168 Q120 110 120 96" />
    </g>
  </svg>
</template>

<style scoped>
.hero-illustration {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
/* Parametric motif variants: muted line-art that reads on light bg; white on dark. */
.hero-illustration .motif {
  color: var(--ink-700, #586860);
  opacity: .1;
}
:global(.dark) .hero-illustration .motif {
  color: #fff;
  opacity: .08;
}
/* Gentle sway — only on the 'waves' motif, which has no static SVG transform
   (animating transform on the translated fruit/palm/lotus groups would clobber
   their positioning, so those stay static — they still read as authored). */
.hero-illustration .motif.motif-anim {
  animation: hero-motif-sway 8s var(--ease-out, ease-in-out) infinite;
}
@keyframes hero-motif-sway {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-8px, 4px); }
}
/* Sun glow — gentle breathing halo (full scene). Soft, slow, calm. */
.hero-illustration .hero-glow {
  transform-box: fill-box;
  transform-origin: center;
  animation: hero-glow-breathe 9s ease-in-out infinite;
}
@keyframes hero-glow-breathe {
  0%, 100% { opacity: .9; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.08); }
}
/* River sheen — a slow light sweep travelling across the water */
.hero-illustration .hero-sheen {
  animation: hero-sheen-sweep 11s ease-in-out infinite;
}
@keyframes hero-sheen-sweep {
  0%, 100% { opacity: .3; transform: translateX(-40px); }
  50% { opacity: .9; transform: translateX(40px); }
}
/* Boat float (full scene) */
.hero-illustration :deep(g[transform*="translate(80, 240)"]) {
  animation: boat-float 6s ease-in-out infinite;
}
@keyframes boat-float {
  0%, 100% { transform: translate(80px, 240px); }
  50% { transform: translate(84px, 237px); }
}
/* Waves shimmer (full scene) */
.hero-illustration :deep(path[d*="M50 310"]) {
  animation: wave-drift 8s ease-in-out infinite;
}
.hero-illustration :deep(path[d*="M200 320"]) {
  animation: wave-drift 8s ease-in-out infinite 2s;
}
.hero-illustration :deep(path[d*="M350 305"]) {
  animation: wave-drift 8s ease-in-out infinite 4s;
}
@keyframes wave-drift {
  0%, 100% { opacity: 1; transform: translateX(0); }
  50% { opacity: .6; transform: translateX(8px); }
}
/* Off-screen pause (JS-gated via IntersectionObserver). Holds the current
   frame — same paint, zero ongoing compositor work while scrolled away.
   No-op when the class is absent (in view / SSR / no observer). */
.hero-illustration.is-offscreen,
.hero-illustration.is-offscreen :deep(*) {
  animation-play-state: paused !important;
}
@media (prefers-reduced-motion: reduce) {
  .hero-illustration :deep(g),
  .hero-illustration :deep(path),
  .hero-illustration .motif { animation: none !important; opacity: .08; }
  /* New depth layers settle to a calm static state (keep their own opacity, no motion) */
  .hero-illustration .hero-glow { animation: none !important; opacity: .9; }
  .hero-illustration .hero-sheen { animation: none !important; opacity: .4; }
}
</style>
