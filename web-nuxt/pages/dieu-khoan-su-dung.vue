<template>
  <section class="legal-page about-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Điều khoản sử dụng' }]" />
    <!-- Hero -->
    <section class="catalog-hero cat-org legal-hero">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">📋</span>
        <div>
          <h1>{{ doc.title }}</h1>
          <p>{{ doc.seo_description }}</p>
        </div>
      </div>
    </section>

    <p class="dateline-eyebrow">HỒ SƠ PHÁP LÝ · CẬP NHẬT {{ doc.updated_date }}</p>
    <div class="legal-body editorial-body drop-cap" v-html="introHtml"></div>

    <section
      v-for="(s, i) in doc.sections"
      :key="i"
      class="legal-section reveal sediment-head"
    >
      <span class="about-section-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
      <div class="about-section-content">
        <h2>{{ stripNum(s.heading) }}</h2>
        <div class="legal-body editorial-body" v-html="mdLite(s.body)"></div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { mdLite } from '~/utils/mdLite'
import { LEGAL_TERMS, mergeLegalDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeLegalDoc(get('legal.terms', {}), LEGAL_TERMS))
const introHtml = computed(() => mdLite(doc.value.intro))

// Headings may carry their own "N. " prefix; the .about-section-num badge
// already shows the order, so strip the inline number to avoid duplicates.
const stripNum = (h: string) => (h || '').replace(/^\s*\d+\.\s*/, '')

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
  ogTitle: () => doc.value.seo_title,
  ogDescription: () => doc.value.seo_description,
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/dieu-khoan-su-dung') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Điều khoản sử dụng' },
      ],
    }),
  }],
})
</script>

<style scoped>
/* Mobile-first baseline; scaled up on wider screens below. */
.legal-page { max-width: 760px; margin: 0 auto; padding: var(--space-6) var(--space-4) var(--space-10); line-height: var(--leading-relaxed); }

/* ── Hero (cat-org institutional motif) ────────────────────────────
   .catalog-hero base styles (container, padding, icon, h1/p) come from
   the global catalog.css; we only supply the institutional gradient. */
.legal-hero { margin-bottom: var(--space-6); }
.about-page :deep(.catalog-hero.cat-org) {
  background: linear-gradient(135deg, rgba(var(--secondary-rgb), .12) 0%, var(--bg-warm) 100%);
}

.legal-page h1 { font-size: var(--text-3xl); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); color: var(--primary-fg-strong); margin-bottom: var(--space-1); }

/* Local page masthead eyebrow — small-caps dateline, matches the site's
   area/ward eyebrow pattern but scoped here (not promoted global). */
.dateline-eyebrow {
  font-family: var(--font-sans); font-size: var(--text-xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--muted); margin: 0 0 var(--space-6); padding-left: var(--space-3);
  position: relative;
}
.dateline-eyebrow::before {
  content: ""; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: var(--space-2); height: 1.5px; background: var(--primary);
}

/* Legal prose gets the measured reading width + relaxed leading; the intro
   paragraph (drop-cap) is the one lede moment on an otherwise plain-spoken page. */
.legal-body.editorial-body { margin-bottom: 0; }
.legal-body.drop-cap { margin-bottom: var(--space-2); }

/* ── Section rhythm: number badge + content zone ──────────────────── */
.legal-section {
  display: flex;
  align-items: flex-start;
  gap: var(--space-5);
  margin: var(--space-6) 0 0;
}
.about-section-num {
  flex: 0 0 auto;
  width: var(--space-8);
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  line-height: 1.1;
  color: var(--ink-tertiary, var(--muted));
  opacity: .55;
  font-variant-numeric: tabular-nums;
  letter-spacing: var(--tracking-tight);
}
.about-section-content { flex: 1 1 auto; min-width: 0; }
.legal-section h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--ink);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: .5px solid var(--line);
}

/* ── Body typography ──────────────────────────────────────────────── */
/* .editorial-body already sets the reading font-size/measure/leading on the
   wrapping .legal-body div (see above); these :deep(p)/:deep(li) rules only
   need to supply color + list layout, not re-set a smaller font-size that
   would fight the editorial measure. */
.legal-page :deep(p) { color: var(--ink-secondary, var(--ink)); }
.legal-page :deep(ul) { padding-inline-start: var(--space-5); }
.legal-page :deep(li) { margin: var(--space-2) 0; color: var(--ink-secondary, var(--ink)); }
.legal-page :deep(a) { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration-line: underline; text-decoration-color: transparent; text-underline-offset: 3px; transition: text-decoration-color .3s var(--ease-out), color .3s var(--ease-out); }
.legal-page :deep(a:hover) { text-decoration-color: var(--primary-fg); }
.legal-page :deep(a:focus-visible) { outline: 2px solid var(--primary); outline-offset: 2px; }

/* ── Responsive scale-up ──────────────────────────────────────────── */
@media (min-width: 640px) {
  .legal-page { padding: var(--space-8) var(--space-5) var(--space-16); }
}
@media (max-width: 600px) {
  .legal-section { flex-direction: column; gap: var(--space-2); }
  .about-section-num { font-size: var(--text-lg); width: auto; }
}

/* ── Dark mode ────────────────────────────────────────────────────── */
.dark .about-page :deep(.catalog-hero.cat-org) {
  background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%);
}
.dark .legal-page :deep(a) { text-decoration-color: transparent; }
.dark .legal-page :deep(a:hover) { text-decoration-color: var(--primary-fg); }

/* Reveal stagger + reduced-motion fallback are provided by the global
   .reveal infrastructure in base.css. */
</style>
