<template>
  <main class="legal-page">
    <h1>{{ doc.title }}</h1>
    <p class="legal-updated">Cập nhật: {{ doc.updated_date }}</p>
    <div class="legal-body" v-html="introHtml"></div>
    <section v-for="(s, i) in doc.sections" :key="i" class="legal-section">
      <h2>{{ s.heading }}</h2>
      <div class="legal-body" v-html="mdLite(s.body)"></div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { mdLite } from '~/utils/mdLite'
import { LEGAL_PRIVACY, mergeLegalDoc } from '~/utils/legalContent'

useReveal()
const { get } = useSiteSettings()
const doc = computed(() => mergeLegalDoc(get('legal.privacy', {}), LEGAL_PRIVACY))
const introHtml = computed(() => mdLite(doc.value.intro))

useSeoMeta({
  title: () => doc.value.seo_title,
  description: () => doc.value.seo_description,
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/chinh-sach-bao-mat') }] })
</script>

<style scoped>
.legal-page { max-width: 760px; margin: 0 auto; padding: var(--space-8) var(--space-5) var(--space-16); line-height: var(--leading-relaxed); }
.legal-page h1 { font-size: var(--text-2xl); font-weight: var(--weight-bold); letter-spacing: var(--tracking-tight); margin-bottom: var(--space-1); }
.legal-page h2 { font-size: var(--text-lg); font-weight: var(--weight-semibold); margin: var(--space-8) 0 var(--space-3); padding-bottom: var(--space-2); border-bottom: .5px solid var(--line); }
.legal-updated { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-6); }
.legal-page :deep(p) { font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page :deep(ul) { padding-inline-start: var(--space-5); }
.legal-page :deep(li) { margin: var(--space-2) 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); }
.legal-page :deep(a) { color: var(--primary-fg); font-weight: var(--weight-semibold); text-decoration-line: underline; text-decoration-color: transparent; text-underline-offset: 3px; transition: text-decoration-color .3s var(--ease-out); }
.legal-page :deep(a:hover) { text-decoration-color: var(--primary-fg); }
.legal-page :deep(a:focus-visible) { outline: 2px solid var(--primary); outline-offset: 2px; }
</style>
