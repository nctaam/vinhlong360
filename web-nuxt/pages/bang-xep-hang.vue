<template>
  <section class="page bxh-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cộng đồng', to: '/cong-dong' }, { label: 'Bảng xếp hạng' }]" />
    <header class="bxh-head">
      <p class="bxh-eyebrow">Sổ vàng cộng đồng · {{ periodEyebrowLabel }}</p>
      <h1 class="bxh-h1">Thành viên tích cực</h1>
      <p>Xếp hạng theo điểm danh tiếng — đánh giá, bài viết, ảnh và lượt theo dõi. <NuxtLink to="/huong-dan-thanh-vien" class="bxh-guide-link">Cách tính điểm?</NuxtLink></p>
    </header>

    <div class="bxh-filters">
      <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm thành viên…" aria-label="Tìm thành viên" class="bxh-search" />
      <FilterChips :filters="periodFilters" :model-value="[period]" single-select
        @update:model-value="v => period = ((v[0] as any) || 'all')" />
      <FilterChips :filters="categoryFilters" :model-value="[category]" single-select
        @update:model-value="v => category = ((v[0] as any) || 'total')" />
    </div>
    <div v-if="selfEntry" class="bxh-self">
      Hạng của bạn: <strong>#{{ selfEntry.rank }}</strong> · {{ selfEntry.points }} điểm
    </div>

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

    <template v-else>
      <!-- Bục vinh danh — top 3, biên tập chứ không phải leaderboard game hoá -->
      <ol v-if="podium.length" class="bxh-podium" :style="{ '--podium-count': podium.length }" aria-label="Top 3 thành viên tích cực nhất">
        <li v-for="m in podium" :key="m.id" class="podium-card reveal" :class="`podium-${m.rank}`">
          <NuxtLink :to="userPath(m.username || m.id)" class="podium-link">
            <span class="podium-rank" aria-hidden="true">{{ m.rank }}</span>
            <span class="avatar podium-avatar">{{ (m.display_name || '?').charAt(0).toUpperCase() }}</span>
            <span class="podium-name">{{ m.display_name }}</span>
            <span class="podium-level">{{ levelIcon(m.level) }} {{ m.level_label }}</span>
            <span class="podium-points">{{ m.points }}<small>điểm</small></span>
            <span class="podium-quote">{{ podiumQuote(m) }}</span>
          </NuxtLink>
        </li>
      </ol>

      <div v-if="podium.length" class="hairline-phusa" role="presentation" aria-hidden="true"></div>

      <ol class="bxh-list" :aria-label="podium.length ? 'Hạng 4 trở đi' : 'Bảng xếp hạng'">
        <li v-for="m in rest" :key="m.id" class="bxh-item" :class="{ 'is-self': m.id === currentUser?.id }">
          <NuxtLink :to="userPath(m.username || m.id)" class="bxh-row">
            <span class="bxh-rank" :class="`bxh-rank-${m.rank}`">{{ m.rank }}</span>
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
    </template>
  </section>
</template>

<script setup lang="ts">
useReveal()
const fetchFailed = ref(false)
const period = ref<'7d' | '30d' | 'all'>('all')
const category = ref<'total' | 'posts' | 'reviews' | 'photos'>('total')
const q = ref('')
const { user: currentUser } = useAuth()

const periodFilters = [
  { key: 'all', label: 'Tất cả' },
  { key: '30d', label: 'Tháng này' },
  { key: '7d', label: 'Tuần này' },
]
const categoryFilters = [
  { key: 'total', label: 'Tổng hợp' },
  { key: 'reviews', label: 'Đánh giá' },
  { key: 'posts', label: 'Bài viết' },
  { key: 'photos', label: 'Ảnh' },
]
const periodEyebrowLabel = computed(() => period.value === '7d' ? 'cập nhật tuần này' : period.value === '30d' ? 'cập nhật tháng này' : 'cập nhật mọi thời điểm')

const { data, pending, refresh } = await useAsyncData('leaderboard',
  () => apiFetch<any>(`/api/community/leaderboard?limit=50&period=${period.value}&category=${category.value}&q=${encodeURIComponent(q.value)}`)
    .catch(() => { fetchFailed.value = true; return { leaders: [], self: null } }),
  { watch: [period, category] })

const { debounced: debouncedRefresh } = useDebounce(() => refresh(), 350)
watch(q, () => debouncedRefresh())

// Danh sách gốc giữ nguyên thứ tự/dữ liệu từ API — chỉ thêm field `rank` hiển thị
// và cắt lát top-3 cho bục vinh danh. Không đổi logic xếp hạng, không gọi thêm API.
const leaders = computed(() => (data.value?.leaders || []).map((m: any, i: number) => ({ ...m, rank: i + 1 })))
const podium = computed(() => leaders.value.slice(0, 3))
const rest = computed(() => leaders.value.slice(3))
const selfEntry = computed(() => data.value?.self || null)

// Trích dẫn tự động cho bục vinh danh — dựng từ số liệu sẵn có (đóng góp nổi bật
// nhất), không cần field backend mới. Giọng biên tập, không phải liệt kê KPI.
function podiumQuote(m: any): string {
  const reviews = m.reviews || 0
  const posts = m.posts || 0
  if (reviews && posts) return `${reviews} đánh giá, ${posts} bài viết — đóng góp đều tay`
  if (reviews) return `${reviews} đánh giá để lại cho cộng đồng`
  if (posts) return `${posts} bài viết chia sẻ với cộng đồng`
  return `${m.points || 0} điểm danh tiếng tích lũy`
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
.bxh-filters { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-3); }
.bxh-search { flex: 1 1 200px; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-input); border-radius: var(--radius-sm); background: var(--surface); color: var(--ink); }
.bxh-self { padding: var(--space-2) var(--space-3); background: color-mix(in srgb, var(--primary) 8%, transparent); border-radius: var(--radius-sm); margin-bottom: var(--space-2); font-size: var(--text-sm); }
.bxh-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.bxh-list li.is-self .bxh-row { outline: 2px solid var(--primary); outline-offset: -1px; }
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
.bxh-points { flex-shrink: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--primary-fg); display: flex; flex-direction: column; align-items: center; line-height: 1; font-variant-numeric: tabular-nums; }
.bxh-points small { font-size: var(--text-xs); font-weight: var(--weight-normal); color: var(--muted); }
@media (max-width: 480px) {
  .bxh-row { padding: var(--space-3) var(--space-2); gap: var(--space-2); }
  .bxh-name { font-size: var(--text-sm); }
}
@media (prefers-reduced-motion: reduce) {
  .bxh-row:hover { transform: none; }
  .bxh-row:active { transform: none; }
}

/* ── Masthead eyebrow — "Sổ vàng cộng đồng" ─────────────────────────────────
   Small-caps dateline above <h1>, echoes .cine-kicker tracking without
   importing that hero-only class. H1 gets the serif voice (--font-editorial)
   used site-wide for named/titled things. */
.bxh-eyebrow {
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--muted); margin: 0 0 var(--space-2);
}
.bxh-h1 { font-family: var(--font-editorial); font-weight: 600; }

/* ── Bục vinh danh (podium strip) — top 3, biên tập chứ không phải leaderboard
   game hoá. Ba thẻ ngang trên desktop, xếp so le trên mobile (huy chương giữa
   cao hơn 2 bên, thứ tự 1-2-3 rõ ràng bằng số lớn). ── */
.bxh-podium { list-style: none; margin: 0 0 var(--space-5); padding: 0; display: grid; grid-template-columns: repeat(var(--podium-count, 3), 1fr); gap: var(--space-3); align-items: end; }
.podium-card { position: relative; }
.podium-link {
  display: flex; flex-direction: column; align-items: center; text-align: center; gap: var(--space-1);
  padding: var(--space-5) var(--space-3) var(--space-4); border-radius: var(--radius-lg);
  background: var(--card); border: .5px solid var(--line); text-decoration: none; color: var(--ink);
  transition: border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle), box-shadow .25s var(--ease-out);
}
.podium-link:hover { border-color: var(--primary-fg); transform: translateY(-2px); box-shadow: var(--shadow-sm); }
.podium-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.podium-link:active { transform: scale(.98); transition-duration: .08s; }
/* Huy chương giữa (rank #1) nhô cao hơn — cả desktop lẫn mobile so le */
.podium-1 { order: 2; }
.podium-2 { order: 1; }
.podium-3 { order: 3; }
.podium-1 .podium-link { padding-top: var(--space-6); background: linear-gradient(180deg, color-mix(in srgb, var(--rank-gold, #d4a017) 8%, var(--card)) 0%, var(--card) 60%); }
.podium-rank {
  font-family: var(--font-editorial); font-size: var(--text-2xl); font-weight: 600; line-height: 1;
  font-variant-numeric: tabular-nums; color: var(--muted);
}
.podium-1 .podium-rank { color: var(--rank-gold, #d4a017); font-size: var(--text-3xl); }
.podium-2 .podium-rank { color: var(--rank-silver, #8a8d91); }
.podium-3 .podium-rank { color: var(--rank-bronze, #b07b4f); }
.dark .podium-1 .podium-rank { color: #f0c040; }
.dark .podium-2 .podium-rank { color: #b0b3b8; }
.dark .podium-3 .podium-rank { color: #d4956a; }
.podium-avatar { width: 56px; height: 56px; font-size: var(--text-lg); }
.podium-1 .podium-avatar { width: 68px; height: 68px; font-size: var(--text-xl); }
.podium-name { font-weight: var(--weight-semibold); overflow-wrap: anywhere; }
.podium-level { font-size: var(--text-xs); color: var(--ink-700); }
.podium-points { font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--primary-fg); line-height: 1; font-variant-numeric: tabular-nums; margin-top: var(--space-1); }
.podium-points small { font-size: var(--text-2xs); font-weight: var(--weight-normal); color: var(--muted); margin-left: 2px; }
/* Trích dẫn tự động — .pull-quote-lite: serif, italic, cỡ nhỏ hơn bản gốc */
.podium-quote {
  font-family: var(--font-editorial); font-style: italic; font-size: var(--text-xs);
  color: var(--ink-secondary, var(--muted)); line-height: var(--leading-snug); margin-top: var(--space-2);
}

/* ── Hairline phù-sa — river→amber→clay, thon 2 đầu. Ngăn bục vinh danh
   khỏi danh sách #4 trở đi, đúng công thức đã chuẩn hoá (sediment-head/
   tc-label), không tự chế biến thể mới. ── */
.hairline-phusa {
  height: 2px; margin: 0 0 var(--space-5); border-radius: var(--radius-full);
  background: linear-gradient(90deg, transparent 0%, var(--river-600) 15%, var(--amber-600) 50%, var(--clay-600) 85%, transparent 100%);
  opacity: .55;
}
.dark .hairline-phusa { background: linear-gradient(90deg, transparent 0%, #74ABB5 15%, var(--amber-500) 50%, var(--clay-400) 85%, transparent 100%); }

@media (max-width: 620px) {
  .bxh-podium { grid-template-columns: 1fr; gap: var(--space-2); }
  .podium-1, .podium-2, .podium-3 { order: initial; }
  .podium-1 .podium-link { padding-top: var(--space-5); }
}

@media (prefers-reduced-motion: reduce) {
  .podium-link:hover { transform: none; }
  .podium-link:active { transform: none; }
}
</style>
