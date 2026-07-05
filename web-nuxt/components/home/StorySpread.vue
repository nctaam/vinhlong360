<template>
  <section class="spread" ref="sectionEl" aria-labelledby="spread-title">
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
    <!-- Chữ ký: "Ba dòng sông hội tụ" — sông Tiền/Hậu/Cổ Chiên vẽ dần khi cuộn tới,
         gặp nhau sau tiêu đề. Một khoảnh khắc táo bạo duy nhất; nơi khác giữ tĩnh. -->
    <svg class="spread-rivers" viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <path pathLength="1" d="M-60,150 C 250,115 450,250 600,250 C 780,250 980,360 1260,330" />
      <path pathLength="1" d="M-60,250 C 230,250 440,250 600,250 C 780,250 980,250 1260,250" />
      <path pathLength="1" d="M-60,350 C 250,385 450,250 600,250 C 780,250 980,140 1260,170" />
      <circle class="river-node" cx="600" cy="250" r="3.2" />
    </svg>
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

// River-line signature draws in once when the spread scrolls into view. No-JS/SSR shows the
// lines already drawn (CSS default); prefers-reduced-motion freezes them (no draw). Observer
// disconnects after firing once.
const sectionEl = ref<HTMLElement | null>(null)
let riverObserver: IntersectionObserver | null = null
onMounted(() => {
  const el = sectionEl.value
  if (!el) return
  if (!('IntersectionObserver' in window)) { el.classList.add('rivers-drawn'); return }
  riverObserver = new IntersectionObserver((entries) => {
    if (entries.some(e => e.isIntersecting)) {
      el.classList.add('rivers-drawn')
      riverObserver?.disconnect()
    }
  }, { threshold: 0.25 })
  riverObserver.observe(el)
})
onUnmounted(() => riverObserver?.disconnect())
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

/* ── River-line signature — the one bold moment (draws on scroll) ── */
.spread-rivers {
  position: absolute;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.spread-rivers path {
  fill: none;
  stroke: rgba(255, 255, 255, .42);
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 0; /* SSR / no-JS: already drawn */
}
.spread-rivers .river-node { fill: rgba(255, 255, 255, .6); }
/* JS present: hide the lines until the spread scrolls in, then stroke them on (staggered). */
html.js .spread:not(.rivers-drawn) .spread-rivers path { stroke-dashoffset: 1; }
html.js .spread:not(.rivers-drawn) .spread-rivers .river-node { opacity: 0; }
.spread.rivers-drawn .spread-rivers path {
  stroke-dashoffset: 0;
  transition: stroke-dashoffset 2.4s var(--ease-out, cubic-bezier(.16, 1, .3, 1));
}
.spread.rivers-drawn .spread-rivers path:nth-child(2) { transition-delay: .18s; }
.spread.rivers-drawn .spread-rivers path:nth-child(3) { transition-delay: .36s; }
.spread.rivers-drawn .spread-rivers .river-node { opacity: 1; transition: opacity .7s ease .95s; }

/* ── Reduced motion: freeze Ken Burns, parallax, AND the river draw ── */
@media (prefers-reduced-motion: reduce) {
  .spread-img {
    animation: none;
    transform: none;
  }
  html.js .spread .spread-rivers path { stroke-dashoffset: 0 !important; transition: none !important; }
  html.js .spread .spread-rivers .river-node { opacity: 1 !important; transition: none !important; }
}
</style>
