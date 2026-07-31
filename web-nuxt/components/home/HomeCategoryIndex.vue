<template>
  <section class="home-category-index" data-home-category-index aria-labelledby="home-category-title">
    <header class="home-category-index__header">
      <p>Chỉ mục địa phương</p>
      <h2 id="home-category-title">Khám phá theo nhu cầu</h2>
    </header>
    <nav class="home-category-index__primary" data-home-category-primary aria-label="Khám phá chính">
      <NuxtLink
        v-for="link in groups.primary"
        :key="link.key"
        :to="link.to"
        class="home-category-index__primary-link"
        :data-accent="link.accent"
      >
        <IconLine :name="link.icon" aria-hidden="true" />
        <span>
          <strong>{{ link.label }}</strong>
          <small>{{ link.hint }}</small>
        </span>
        <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
      </NuxtLink>
    </nav>
    <div class="home-category-index__utility" data-home-category-utility>
      <p>Tiện ích cho hành trình</p>
      <nav aria-label="Tiện ích hành trình">
        <NuxtLink
          v-for="link in groups.utility"
          :key="link.key"
          :to="link.to"
          class="home-category-index__utility-link"
          :data-accent="link.accent"
        >
          <IconLine :name="link.icon" aria-hidden="true" />
          <span>
            <strong>{{ link.label }}</strong>
            <small>{{ link.hint }}</small>
          </span>
          <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
        </NuxtLink>
      </nav>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { HomeCategoryGroups } from '~/utils/homeNocturnePresentation'

defineProps<{ groups: HomeCategoryGroups }>()
</script>
