<template>
  <section class="home-continuation" data-home-section="journey-continuation" aria-labelledby="home-continuation-title">
    <div class="home-continuation__intro">
      <p class="home-continuation__eyebrow">Tiếp tục hành trình</p>
      <h2 id="home-continuation-title">Giữ mạch khám phá khi bạn đã có một điểm bắt đầu</h2>
      <p class="home-continuation__lead-desc">Tra cứu tọa độ thực địa, kết nối tuyến sông miệt vườn và lên kế hoạch tự túc thuận tiện nhất.</p>
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
      <NuxtLink to="/du-lich" class="home-continuation__link home-continuation__link--featured">
        <IconLine name="compass" aria-hidden="true" />
        <span class="home-continuation__link-text">
          <strong class="home-continuation__link-title">Khám phá 1.772 điểm đến</strong>
          <span class="home-continuation__link-sub">Di sản, danh thắng & làng nghề miệt vườn</span>
        </span>
        <IconLine name="arrow-right" class="home-continuation__arrow" aria-hidden="true" />
      </NuxtLink>
      <NuxtLink to="/ban-do" class="home-continuation__link">
        <IconLine name="map" aria-hidden="true" />
        <span class="home-continuation__link-text">
          <strong class="home-continuation__link-title">Mở bản đồ thực địa</strong>
          <span class="home-continuation__link-sub">Định vị bến phà, vườn trái cây & quán ngon</span>
        </span>
        <IconLine name="arrow-right" class="home-continuation__arrow" aria-hidden="true" />
      </NuxtLink>
      <NuxtLink to="/lich-trinh" class="home-continuation__link">
        <IconLine name="calendar" aria-hidden="true" />
        <span class="home-continuation__link-text">
          <strong class="home-continuation__link-title">Xem 16 lịch trình thong dong</strong>
          <span class="home-continuation__link-sub">Gợi ý 1 ngày, 2N1Đ và 3N2Đ từ người địa phương</span>
        </span>
        <IconLine name="arrow-right" class="home-continuation__arrow" aria-hidden="true" />
      </NuxtLink>
    </nav>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  actions: any[]
  pending?: boolean
}>()
</script>
