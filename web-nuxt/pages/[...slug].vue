<template>
  <section class="page" style="text-align: center; padding: 80px 20px">
    <h1 style="font-size: 4rem; margin: 0; color: var(--primary)">404</h1>
    <p style="font-size: 1.2rem; color: var(--muted); margin: 12px 0 8px">Trang không tồn tại hoặc đã bị xóa.</p>
    <p style="font-size: .92rem; color: var(--muted); margin-bottom: 24px">Thử tìm kiếm hoặc quay về trang chủ.</p>
    <form style="max-width: 400px; margin: 0 auto 24px; display: flex; gap: 8px" @submit.prevent="onSearch">
      <input v-model="q" class="input" placeholder="Tìm đặc sản, trải nghiệm…" style="flex: 1" />
      <button class="btn btn-primary" type="submit">Tìm</button>
    </form>
    <NuxtLink to="/" class="btn btn-outline">Về trang chủ</NuxtLink>
  </section>
</template>

<script setup lang="ts">
if (import.meta.server) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, 404)
}

useSeoMeta({ title: '404 — vinhlong360', robots: 'noindex, nofollow' })

const q = ref('')
function onSearch() {
  if (q.value.trim()) navigateTo(`/tim-kiem?q=${encodeURIComponent(q.value.trim())}`)
}
</script>
