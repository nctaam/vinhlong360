<template>
  <section class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Hành trình' }]" />
    <div class="page-head">
      <h1>Hành trình của bạn</h1>
      <p>Tất cả địa điểm, đặc sản và trải nghiệm bạn đã lưu — sẵn sàng để lên lịch trình.</p>
    </div>

    <!-- GĐ-audit: favorites đọc từ localStorage (client-only) → bọc ClientOnly tránh hydration mismatch -->
    <ClientOnly>
    <!-- Quick stats -->
    <div v-if="count > 0" class="journey-stats">
      <div v-for="(items, type) in byType" :key="type" class="js-item">
        <span class="js-emoji">{{ getTypeMeta(type).emoji }}</span>
        <strong>{{ items.length }}</strong>
        <span>{{ getTypeMeta(type).label }}</span>
      </div>
    </div>

    <!-- CTA bar -->
    <div v-if="count > 0" class="journey-cta">
      <NuxtLink to="/tao-lich-trinh" no-prefetch class="btn btn-primary">Tạo lịch trình từ danh sách này</NuxtLink>
      <button class="btn btn-ghost btn-sm" @click="clearAll">Xóa tất cả</button>
    </div>

    <!-- Grouped by type -->
    <div v-if="count > 0">
      <div v-for="(items, type) in byType" :key="type" class="journey-group">
        <h2>{{ getTypeMeta(type).emoji }} {{ getTypeMeta(type).label }} <span class="jg-count">({{ items.length }})</span></h2>
        <div class="grid">
          <div v-for="fav in items" :key="fav.id" class="journey-card">
            <div v-if="fav.image" class="jc-img">
              <img :src="fav.image" :alt="fav.name" loading="lazy" />
            </div>
            <div class="jc-body">
              <NuxtLink :to="`/dia-diem/${fav.id}`" class="jc-name">{{ fav.name }}</NuxtLink>
              <p v-if="fav.place_name" class="jc-place">{{ fav.place_name }}</p>
              <p v-if="fav.summary" class="jc-summary">{{ fav.summary }}</p>
              <div class="jc-actions">
                <NuxtLink :to="`/dia-diem/${fav.id}`" class="btn btn-sm btn-ghost">Xem chi tiết</NuxtLink>
                <button class="btn btn-sm btn-ghost danger" @click="remove(fav.id)">Bỏ lưu</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="journey-empty">
      <div class="je-icon">🗺️</div>
      <h2>Chưa có gì được lưu</h2>
      <p>Khám phá các địa điểm, đặc sản và trải nghiệm — nhấn ❤️ để lưu vào hành trình của bạn.</p>
      <div class="je-links">
        <NuxtLink to="/du-lich" class="btn btn-primary">Khám phá du lịch</NuxtLink>
        <NuxtLink to="/san-pham" class="btn btn-outline">Xem sản phẩm</NuxtLink>
        <NuxtLink to="/lich-trinh" class="btn btn-ghost">Lịch trình gợi ý</NuxtLink>
      </div>
    </div>
    </ClientOnly>
  </section>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'

const { favorites, byType, count, remove, clear } = useFavorites()

function getTypeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: 'place' }
}

function clearAll() {
  if (confirm('Xóa tất cả mục đã lưu?')) clear()
}

useSeoMeta({
  title: 'Hành trình của bạn — vinhlong360',
  description: 'Danh sách địa điểm, đặc sản và trải nghiệm bạn đã lưu để khám phá Vĩnh Long.',
  robots: 'noindex,follow',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/hanh-trinh') }],
})
</script>
