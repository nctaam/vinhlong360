<template>
  <NuxtLoadingIndicator color="var(--primary)" :height="2" :throttle="200" />
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
// Speculation Rules: prefetch (nhẹ — chỉ tải document, KHÔNG prerender/chạy JS → không
// tải backend) link nội-bộ khi hover/pointerdown (eagerness moderate), loại admin/api/auth.
// Chrome/Edge hỗ trợ; trình duyệt khác bỏ qua an toàn. Bổ trợ cho hard-nav (Nuxt SPA đã
// tự prefetch client-side cho điều-hướng NuxtLink).
useHead({
  script: [{
    type: 'speculationrules',
    innerHTML: JSON.stringify({
      prefetch: [{
        source: 'document',
        eagerness: 'moderate',
        where: { and: [
          { href_matches: '/*' },
          { not: { href_matches: '/admin/*' } },
          { not: { href_matches: '/api/*' } },
          { not: { href_matches: '/auth/*' } },
          { not: { selector_matches: '[rel~=nofollow]' } },
        ] },
      }],
    }),
  }],
})
</script>
