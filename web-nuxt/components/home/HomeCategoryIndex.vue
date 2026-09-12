<template>
  <section class="home-category-index" data-home-category-index aria-labelledby="home-category-title">
    <header class="home-category-index__header">
      <p>Trải nghiệm phong phú</p>
      <h2 id="home-category-title">Bạn muốn trải nghiệm điều gì hôm nay?</h2>
    </header>
    <nav class="home-category-index__primary" data-home-category-primary aria-label="Khám phá chính">
      <NuxtLink
        v-for="(link, index) in groups.primary"
        :key="link.key"
        :to="link.to"
        class="home-category-index__primary-link home-category-index__card"
        :class="{ 'home-category-index__card--lead': index === 0 }"
        :data-material-accent="link.accent"
        data-decision-route
      >
        <span class="home-category-index__media" aria-hidden="true">
          <img
            :src="categoryImage(link.key)"
            alt=""
            loading="lazy"
            decoding="async"
            width="320"
            height="180"
            class="home-category-index__media-img"
            @error="onImgError"
          >
          <span class="home-category-index__scrim" />
        </span>
        <span class="home-category-index__meta">
          <IconLine :name="link.icon" aria-hidden="true" />
          <span>
            <strong>{{ link.label }}</strong>
            <small>{{ link.hint }}</small>
          </span>
          <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
          <span class="home-category-index__arrow" aria-hidden="true"><IconLine name="arrow-right" /></span>
        </span>
      </NuxtLink>
    </nav>
    <div class="home-category-index__utility" data-home-category-utility>
      <p>Tiện ích cho hành trình</p>
      <nav aria-label="Tiện ích hành trình">
        <NuxtLink
          v-for="link in groups.utility"
          :key="link.key"
          :to="link.to"
          class="home-category-index__utility-link home-category-index__card"
          :data-material-accent="link.accent"
          data-decision-route
        >
          <span class="home-category-index__media" aria-hidden="true">
            <img
              :src="categoryImage(link.key)"
              alt=""
              loading="lazy"
              decoding="async"
              width="240"
              height="140"
              class="home-category-index__media-img"
              @error="onImgError"
            >
            <span class="home-category-index__scrim" />
          </span>
          <span class="home-category-index__meta">
            <IconLine :name="link.icon" aria-hidden="true" />
            <span>
              <strong>{{ link.label }}</strong>
              <small>{{ link.hint }}</small>
            </span>
            <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
            <span class="home-category-index__arrow" aria-hidden="true"><IconLine name="arrow-right" /></span>
          </span>
        </NuxtLink>
      </nav>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { HomeCategoryGroups } from '~/utils/homeNocturnePresentation'

defineProps<{ groups: HomeCategoryGroups }>()

const CATEGORY_IMAGES: Record<string, string> = {
  'du-lich': '/img/cat-du-lich.webp',
  'am-thuc': '/img/cat-am-thuc.webp',
  'ocop': '/img/cat-ocop.webp',
  'le-hoi': '/img/cat-le-hoi.webp',
  'luu-tru': '/img/cat-luu-tru.webp',
  'lich-trinh': '/img/cat-lich-trinh.webp',
  'ban-do': '/img/cat-ban-do.webp',
}

function categoryImage(key: string): string {
  return CATEGORY_IMAGES[key] || '/img/cat-du-lich.webp'
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  if (img) img.style.display = 'none'
}
</script>
