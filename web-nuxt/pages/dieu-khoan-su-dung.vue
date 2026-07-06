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

    <!-- Jump-link TOC — 6 sections cross-link each other elsewhere on the site;
         without anchors a cross-link only ever lands on the page top. -->
    <nav class="legal-toc" aria-label="Mục lục điều khoản sử dụng">
      <a v-for="(s, i) in doc.sections" :key="i" :href="`#legal-section-${i + 1}`" class="legal-toc-link">
        {{ String(i + 1).padStart(2, '0') }}. {{ stripNum(s.heading) }}
      </a>
    </nav>

    <section
      v-for="(s, i) in doc.sections"
      :key="i"
      :id="`legal-section-${i + 1}`"
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

<style src="~/assets/css/legal.css"></style>
