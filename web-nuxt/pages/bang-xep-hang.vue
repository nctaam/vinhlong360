<template>
  <section class="page bxh-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: 'Bảng xếp hạng' }]" />
    <header class="bxh-head">
      <h1>Thành viên tích cực</h1>
      <p>Xếp hạng theo điểm danh tiếng — đánh giá, bài viết, ảnh và lượt theo dõi. <NuxtLink to="/huong-dan-thanh-vien" class="bxh-guide-link">Cách tính điểm?</NuxtLink></p>
    </header>

    <SkeletonList v-if="pending" :count="6" />

    <EmptyState
      v-else-if="fetchFailed && !leaders.length"
      icon="⚠️" tone="error" title="Không thể tải bảng xếp hạng"
      message="Lỗi kết nối. Vui lòng thử lại."
    >
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('leaderboard')">Thử lại</button>
      </template>
    </EmptyState>

    <EmptyState
      v-else-if="!leaders.length"
      icon="🏆" title="Chưa có dữ liệu xếp hạng"
      message="Hãy chia sẻ và đánh giá để trở thành thành viên tích cực đầu tiên!"
    >
      <template #actions>
        <NuxtLink to="/cong-dong" class="btn btn-primary btn-sm">Tham gia cộng đồng</NuxtLink>
      </template>
    </EmptyState>

    <ol v-else class="bxh-list">
      <li v-for="(m, i) in leaders" :key="m.id" class="bxh-item">
        <NuxtLink :to="`/nguoi-dung/${m.id}`" class="bxh-row">
          <span class="bxh-rank" :class="`bxh-rank-${i + 1}`">{{ i + 1 }}</span>
          <span class="avatar bxh-avatar">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
          <span class="bxh-main">
            <span class="bxh-name">{{ m.display_name }}</span>
            <span class="bxh-meta">
              <span class="bxh-level">{{ levelIcon(m.level) }} {{ m.level_label }}</span>
              <span class="bxh-sub">{{ m.reviews }} đánh giá · {{ m.posts }} bài</span>
            </span>
          </span>
          <span class="bxh-points">{{ m.points }}<small>điểm</small></span>
        </NuxtLink>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
useReveal()
const fetchFailed = ref(false)
const { data, pending } = await useAsyncData('leaderboard',
  () => apiFetch<any>('/api/community/leaderboard?limit=50').catch(() => { fetchFailed.value = true; return { leaders: [] } }))
const leaders = computed(() => data.value?.leaders || [])

function levelIcon(level: number): string {
  return ({ 1: '🌱', 2: '🤝', 3: '🌟', 4: '👑' } as Record<number, string>)[level] || '🌱'
}

useSeoMeta({
  title: 'Thành viên tích cực — Bảng xếp hạng — vinhlong360',
  description: 'Bảng xếp hạng thành viên đóng góp tích cực nhất cộng đồng vinhlong360: đánh giá, bài viết, ảnh và lượt theo dõi.',
  ogTitle: 'Bảng xếp hạng — vinhlong360',
  ogDescription: 'Thành viên đóng góp tích cực nhất cộng đồng vinhlong360.',
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/bang-xep-hang') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Cộng đồng', item: 'https://vinhlong360.vn/cong-dong' },
        { '@type': 'ListItem', position: 3, name: 'Bảng xếp hạng' },
      ],
    }),
  }],
})
</script>

<style scoped>
.bxh-page { max-width: 680px; margin: 0 auto; }
.bxh-head { margin-bottom: var(--space-5); }
.bxh-head h1 { margin: 0 0 var(--space-2); }
.bxh-head p { color: var(--muted); margin: 0; }
.bxh-guide-link { color: var(--primary-fg); font-weight: var(--weight-medium); text-decoration: underline; text-decoration-color: transparent; text-underline-offset: 2px; transition: text-decoration-color .2s; }
.bxh-guide-link:hover { text-decoration-color: var(--primary-fg); }
.bxh-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.bxh-row { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); min-height: 56px; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); text-decoration: none; color: var(--ink); transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle); }
.bxh-row:hover { border-color: var(--primary-fg); transform: translateY(-1px); }
.bxh-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.bxh-row:active { transform: scale(.98); transition-duration: .08s; }
.bxh-rank { flex-shrink: 0; width: 28px; text-align: center; font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--muted); }
.bxh-rank-1 { color: var(--rank-gold, #d4a017); } .bxh-rank-2 { color: var(--rank-silver, #8a8d91); } .bxh-rank-3 { color: var(--rank-bronze, #b07b4f); }
.dark .bxh-rank-1 { --rank-gold: #f0c040; } .dark .bxh-rank-2 { --rank-silver: #b0b3b8; } .dark .bxh-rank-3 { --rank-bronze: #d4956a; }
.bxh-avatar { width: 44px; height: 44px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary); color: var(--primary-fg, #fff); font-weight: var(--weight-semibold); flex-shrink: 0; }
.bxh-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: .1rem; }
.bxh-name { font-weight: var(--weight-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bxh-meta { display: flex; flex-wrap: wrap; gap: var(--space-2); font-size: var(--text-xs); color: var(--muted); }
.bxh-level { color: var(--ink-700); }
.bxh-points { flex-shrink: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--primary-fg); display: flex; flex-direction: column; align-items: center; line-height: 1; }
.bxh-points small { font-size: var(--text-xs); font-weight: var(--weight-normal); color: var(--muted); }
@media (max-width: 480px) {
  .bxh-row { padding: var(--space-3) var(--space-2); gap: var(--space-2); }
  .bxh-name { font-size: var(--text-sm); }
}
@media (prefers-reduced-motion: reduce) {
  .bxh-row:hover { transform: none; }
  .bxh-row:active { transform: none; }
}
</style>
