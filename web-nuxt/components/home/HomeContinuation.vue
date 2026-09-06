<template>
  <section class="home-continuation" data-home-section="journey-continuation" aria-labelledby="home-continuation-title">
    <div>
      <p class="home-continuation__eyebrow">Tiếp tục hành trình</p>
      <h2 id="home-continuation-title">Giữ mạch khám phá khi bạn đã có một điểm bắt đầu</h2>
    </div>
    <!-- Personalized continuation is client-only because it reads saved/recent local state. -->
    <ClientOnly>
      <JourneyActionRail
        v-if="!pending && actions.length"
        :actions="actions"
        title="Tiếp tục hành trình của bạn"
        subtitle="Từ những gì bạn đã lưu và vừa xem."
        aria-label="Gợi ý hành trình trên trang chủ"
        compact
      />
      <template #fallback>
        <div class="home-continuation-rail-fallback" aria-hidden="true" style="min-height: 64px;"></div>
      </template>
    </ClientOnly>
    <nav class="home-continuation__links" aria-label="Bước tiếp theo">
      <NuxtLink to="/ban-do">Mở bản đồ</NuxtLink>
      <NuxtLink to="/lich-trinh">Xem lịch trình</NuxtLink>
    </nav>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  actions: any[]
  pending?: boolean
}>()
</script>
