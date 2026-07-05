<template>
  <section class="legal-page about-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Giới thiệu' }]" />

    <!-- Brand masthead — river→clay wash, unique to this page family. -->
    <section class="brand-masthead about-masthead">
      <div class="bm-inner">
        <p class="bm-eyebrow"><span class="bm-tick" aria-hidden="true"></span>Về vinhlong360</p>
        <h1>{{ doc.title }}</h1>
        <p class="bm-sub">Miền Tây không thiếu chỗ để đi. Cái thiếu là người kể cho bạn nghe vì sao nên ghé.</p>
      </div>
      <svg class="bm-motif" viewBox="0 0 160 120" aria-hidden="true" focusable="false">
        <path class="bm-river" d="M4 78 Q40 58 80 74 T156 66" fill="none" stroke-width="2" stroke-linecap="round" />
        <path class="bm-river bm-river--2" d="M4 96 Q44 80 84 92 T156 86" fill="none" stroke-width="1.4" stroke-linecap="round" />
        <path d="M56 68 q10-8 22 0 l-2 7 h-18 z" fill="none" stroke-width="1.6" stroke-linejoin="round" />
        <circle cx="118" cy="40" r="2.4" />
        <circle cx="130" cy="34" r="2.4" />
        <circle cx="142" cy="40" r="2.4" />
      </svg>
    </section>

    <p class="legal-updated">Cập nhật: {{ doc.updated_date }}</p>
    <div class="legal-body about-intro editorial-body drop-cap" v-html="introHtml"></div>

    <article
      v-for="(s, i) in doc.sections"
      :key="i"
      class="legal-section about-section reveal sediment-head"
      :class="{
        'highlight-badge': i < 3,
        'mission-section': i === 0,
        'noncommercial-section': i === 2,
        'tint-alt': i % 2 === 1,
      }"
    >
      <span class="about-section-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
      <div class="about-section-content">
        <template v-if="i === 0">
          <h2>{{ stripNum(s.heading) }}</h2>
          <blockquote class="pull-quote about-mission-quote">
            {{ missionQuote }}
            <cite>— Sứ mệnh vinhlong360</cite>
          </blockquote>
          <div class="legal-body" v-html="mdLite(missionRest)"></div>
        </template>
        <template v-else>
          <h2>{{ stripNum(s.heading) }}</h2>
          <div class="legal-body" v-html="mdLite(s.body)"></div>
        </template>
      </div>
    </article>

    <!-- Signature moment: the tri-province merge as the emotional subject, not a footnote. -->
    <section class="province-band reveal" aria-labelledby="province-band-heading">
      <h2 id="province-band-heading" class="sr-only">Ba vùng đất, một câu chuyện</h2>
      <div class="pb-grain" aria-hidden="true"></div>
      <div class="pb-glyphs">
        <div class="pb-glyph">
          <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path d="M24 6c-3 8-10 10-10 20a10 10 0 0 0 20 0c0-10-7-12-10-20Z" fill="none" stroke-width="1.6" /><path d="M24 26v16" stroke-width="1.6" /></svg>
          <p><strong>Vĩnh Long</strong> — sông nước, miệt vườn, làng nghề gốm đỏ.</p>
        </div>
        <div class="pb-glyph">
          <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path d="M24 8c6 4 6 10 2 14-4 4-4 8 0 12M24 8c-6 4-6 10-2 14 4 4 4 8 0 12" fill="none" stroke-width="1.6" /><path d="M14 34h20" stroke-width="1.6" /></svg>
          <p><strong>Bến Tre</strong> — xứ dừa, cù lao giữa sông, đặc sản dừa.</p>
        </div>
        <div class="pb-glyph">
          <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path d="M24 6 12 18h24Z" fill="none" stroke-width="1.6" stroke-linejoin="round" /><path d="M16 18v20h16V18M12 38h24" stroke-width="1.6" /></svg>
          <p><strong>Trà Vinh</strong> — văn hoá Khmer, chùa cổ, ẩm thực giao thoa.</p>
        </div>
      </div>
      <p class="pb-tagline">Sáp nhập trên bản đồ. Chưa từng sáp nhập trong lòng người.</p>
    </section>

    <!-- Closing band: About page should never dead-end. -->
    <section class="about-cta reveal">
      <NuxtLink to="/dia-diem" class="btn btn-primary">Xem hành trình mẫu</NuxtLink>
      <NuxtLink to="/lien-he" class="btn btn-outline">Liên hệ với chúng tôi</NuxtLink>
    </section>
  </section>
</template>

<script setup lang="ts">
import { mdLite } from '~/utils/mdLite'
import { ABOUT_PAGE, mergeAboutDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeAboutDoc(get('page.about', {}), ABOUT_PAGE))
const introHtml = computed(() => mdLite(doc.value.intro))

// Headings carry their own "N. " prefix; the .about-section-num badge already
// shows the order, so strip the inline number to avoid duplicate numbering.
const stripNum = (h: string) => (h || '').replace(/^\s*\d+\.\s*/, '')

// Section 0 (Sứ mệnh) becomes a pull-quote spread: the first paragraph of the
// existing mission body IS the thesis statement already (bolded in-source) —
// pulled out as-is, not invented. Remaining paragraphs stay as supporting body.
// Falls back to the whole body as the quote if content is ever a single block
// (e.g. an admin override with no blank-line break).
const missionQuote = computed(() => {
  const raw = doc.value.sections?.[0]?.body || ''
  const [first] = raw.split(/\n\s*\n/)
  return (first || raw).replace(/\*\*/g, '').trim()
})
const missionRest = computed(() => {
  const raw = doc.value.sections?.[0]?.body || ''
  const parts = raw.split(/\n\s*\n/)
  return parts.slice(1).join('\n\n').trim()
})

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
  ogTitle: () => doc.value.seo_title,
  ogDescription: () => doc.value.seo_description,
})

const aboutJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'AboutPage',
  name: 'Về vinhlong360',
  url: canonicalUrl('/gioi-thieu'),
  mainEntity: {
    '@type': 'Organization',
    name: 'vinhlong360',
    url: canonicalUrl('/'),
    logo: 'https://vinhlong360.vn/icons/icon-512.png',
    areaServed: ['Vĩnh Long', 'Bến Tre', 'Trà Vinh'],
  },
}

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/gioi-thieu') }],
  script: [
    { type: 'application/ld+json', innerHTML: JSON.stringify(aboutJsonLd) },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Giới thiệu' },
        ],
      }),
    },
  ],
})
</script>

<style scoped>
/* Mobile-first baseline; scaled up on wider screens below. */
.legal-page { max-width: 760px; margin: 0 auto; padding: 0 var(--space-4) var(--space-10); line-height: var(--leading-relaxed); }

/* ── Brand masthead ────────────────────────────────────────────────
   The ONLY place on the site this specific river→clay wash appears —
   deliberately distinct from .catalog-hero so brand pages never read
   as catalog pages. Full-bleed via negative margin against the page's
   own inline padding, grain overlay + gradient wash, no photography. */
.brand-masthead {
  position: relative;
  overflow: clip;
  isolation: isolate;
  margin: 0 calc(-1 * var(--space-4)) var(--space-8);
  padding: var(--space-8) var(--space-4) var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-6);
  background:
    var(--grain),
    linear-gradient(120deg, color-mix(in srgb, var(--river-600) 14%, transparent) 0%, var(--bg-warm) 55%, rgba(var(--primary-rgb), .16) 120%);
  background-blend-mode: overlay, normal;
}
.bm-inner { flex: 1 1 auto; min-width: 0; max-width: var(--measure-read); }
.bm-eyebrow {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--primary-fg-strong); margin: 0 0 var(--space-3);
}
.bm-tick { width: 14px; height: 1.5px; background: var(--accent, var(--amber-500)); flex-shrink: 0; }
.brand-masthead h1 {
  font-family: var(--font-editorial); font-weight: 600;
  font-size: clamp(2rem, 1.6rem + 2vw, 3rem);
  line-height: var(--leading-tight); letter-spacing: var(--tracking-tight);
  color: var(--ink); margin: 0 0 var(--space-2); text-wrap: balance;
}
.bm-sub {
  font-family: var(--font-editorial); font-style: italic;
  font-size: clamp(1rem, .92rem + .4vw, 1.2rem);
  line-height: var(--leading-snug); color: var(--ink-secondary, var(--muted));
  margin: 0; max-width: 46ch;
}
.bm-motif { width: clamp(84px, 9vw + 40px, 140px); height: auto; flex-shrink: 0; color: var(--clay-400); opacity: .85; }
.bm-motif path, .bm-motif circle { stroke: currentColor; fill: none; }
.bm-motif circle { fill: currentColor; stroke: none; }
.bm-river { stroke-dasharray: 6 5; animation: bm-ripple 12s linear infinite; }
.bm-river--2 { animation-duration: 15s; animation-direction: reverse; opacity: .6; }
@keyframes bm-ripple { to { stroke-dashoffset: -110; } }

.legal-updated { color: var(--ink-tertiary); font-size: var(--text-sm); margin-bottom: var(--space-6); }
.about-intro { margin-bottom: var(--space-8); }

/* ── Section rhythm: number badge + content zone ──────────────────── */
.about-section {
  display: flex;
  align-items: flex-start;
  gap: var(--space-5);
  margin: var(--space-6) 0 0;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-lg);
}
/* Odd/even background-tint alternation — scrolling reads as turning a page. */
.about-section.tint-alt { background: var(--bg-warm); }
.about-section-num {
  flex: 0 0 auto;
  width: var(--space-8);
  font-family: var(--font-editorial);
  font-size: var(--text-2xl);
  font-weight: 600;
  font-variant-numeric: tabular-nums oldstyle-nums;
  line-height: 1.1;
  color: var(--ink-tertiary);
  opacity: .55;
  letter-spacing: var(--tracking-tight);
}
.about-section-content { flex: 1 1 auto; min-width: 0; }
/* h2 typography (serif + weight) now comes from .sediment-head on the
   article; we only keep the spacing/border here. */
.about-section h2 {
  font-size: var(--text-lg);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: .5px solid var(--line);
}

/* Sections 1-3 read as trust callouts. */
.highlight-badge {
  background: var(--bg-warm);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-top: var(--space-5);
}
.highlight-badge h2 { border-bottom: none; padding-bottom: 0; }
/* highlight-badge already tints via --bg-warm; don't double-tint. */
.highlight-badge.tint-alt { background: var(--bg-warm); }

/* Section 1 — Mission emphasis (pull-quote spread lives inside). */
.mission-section {
  border-left: 4px solid var(--secondary-fg);
  background: rgba(var(--secondary-rgb), .08);
}
.about-mission-quote { margin: var(--space-4) 0 var(--space-5); }
.about-mission-quote :deep(cite) { font-style: normal; }

/* Section 3 — Non-commercial trust signal. */
.noncommercial-section :deep(.legal-body > p:first-child) { font-weight: var(--weight-semibold); color: var(--primary-fg-strong); }
.noncommercial-section :deep(.legal-body ul) { list-style: none; padding-inline-start: 0; }
.noncommercial-section :deep(.legal-body li) { position: relative; padding-inline-start: var(--space-6); }
.noncommercial-section :deep(.legal-body li)::before {
  content: '✓';
  position: absolute;
  inset-inline-start: 0;
  color: var(--secondary-fg);
  font-weight: var(--weight-bold);
}

/* ── Signature moment: "Ba vùng, một câu chuyện" ──────────────────── */
.province-band {
  position: relative;
  overflow: clip;
  margin: var(--space-editorial) calc(-1 * var(--space-4)) var(--space-8);
  padding: var(--space-8) var(--space-4);
  background: linear-gradient(120deg, color-mix(in srgb, var(--river-600) 12%, transparent) 0%, var(--bg-warm) 50%, rgba(var(--primary-rgb), .14) 100%);
  text-align: center;
}
.pb-grain { position: absolute; inset: 0; background: var(--grain); opacity: .05; pointer-events: none; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.pb-glyphs {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-6);
  max-width: 900px;
  margin: 0 auto var(--space-6);
}
.pb-glyph {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-3);
  opacity: 0; transform: translateY(8px);
  transition: opacity .6s var(--ease-out), transform .6s var(--ease-out);
}
.province-band.revealed .pb-glyph { opacity: 1; transform: translateY(0); }
.province-band.revealed .pb-glyph:nth-child(2) { transition-delay: 120ms; }
.province-band.revealed .pb-glyph:nth-child(3) { transition-delay: 240ms; }
.pb-glyph svg { width: 44px; height: 44px; color: var(--clay-600); }
.pb-glyph svg path { stroke: currentColor; }
.pb-glyph p { margin: 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); max-width: 26ch; }
.pb-tagline {
  position: relative;
  font-family: var(--font-editorial); font-style: italic; font-weight: 500;
  font-size: clamp(1.15rem, 1rem + .8vw, 1.5rem);
  color: var(--ink); margin: 0; text-wrap: balance;
}

/* ── Closing CTA — About should never dead-end. ───────────────────── */
.about-cta {
  display: flex; gap: var(--space-3); justify-content: center; flex-wrap: wrap;
  padding-bottom: var(--space-4);
}

/* ── Body typography ──────────────────────────────────────────────── */
.legal-page :deep(p) { font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
/* Override AFTER the rule above (same specificity — source order decides):
   the intro lede is the one place .editorial-body's larger clamp() size
   should win over the blanket --text-sm legal-body rule. */
.about-intro :deep(p) { font-size: inherit; color: inherit; }
.legal-page :deep(ul) { padding-inline-start: var(--space-5); }
.legal-page :deep(li) { margin: var(--space-2) 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page :deep(a) { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration-line: underline; text-decoration-color: transparent; text-underline-offset: 3px; transition: text-decoration-color .3s var(--ease-out), color .3s var(--ease-out); }
.legal-page :deep(a:hover) { text-decoration-color: var(--primary-fg); }
.legal-page :deep(a:visited) { color: var(--primary-fg); opacity: .85; }
.legal-page :deep(a:focus-visible) { outline: 2px solid var(--primary); outline-offset: 2px; }

/* ── Responsive scale-up ──────────────────────────────────────────── */
@media (min-width: 640px) {
  .legal-page { padding: 0 var(--space-5) var(--space-16); }
  .brand-masthead { margin-inline: calc(-1 * var(--space-5)); padding-inline: var(--space-8); }
  .province-band { margin-inline: calc(-1 * var(--space-5)); padding-inline: var(--space-8); }
}
@media (max-width: 600px) {
  .about-section { flex-direction: column; gap: var(--space-2); }
  .about-section-num { font-size: var(--text-lg); width: auto; }
  .brand-masthead { flex-direction: column; text-align: center; padding-block: var(--space-6); }
  .bm-inner { max-width: none; }
}

/* ── Dark mode ────────────────────────────────────────────────────── */
.dark .brand-masthead {
  background:
    var(--grain),
    linear-gradient(120deg, rgba(116, 171, 181, .1) 0%, rgba(255,255,255,.02) 55%, rgba(var(--primary-rgb), .12) 120%);
}
.dark .bm-motif { color: var(--clay-400); opacity: .7; }
.dark .highlight-badge { background: var(--bg-alt); border-color: var(--line); }
.dark .about-section.tint-alt { background: rgba(255,255,255,.025); }
.dark .mission-section { border-color: var(--secondary-fg); background: rgba(var(--secondary-rgb), .12); }
.dark .province-band { background: linear-gradient(120deg, rgba(116, 171, 181, .08) 0%, rgba(255,255,255,.02) 50%, rgba(var(--primary-rgb), .1) 100%); }
.dark .pb-glyph svg { color: var(--clay-400); }
.dark .legal-page :deep(a) { text-decoration-color: transparent; }
.dark .legal-page :deep(a:hover) { text-decoration-color: var(--primary-fg); }

/* ── Reduced motion ───────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .bm-river, .bm-river--2 { animation: none; stroke-dasharray: none; }
  .pb-glyph { transition: none; opacity: 1; transform: none; }
}

/* Reveal stagger + reduced-motion fallback are provided by the global
   .reveal infrastructure in base.css. */
</style>
