<template>
  <section class="page tb-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Thông báo' }]" />
    <header class="tb-head">
      <h1>Thông báo</h1>
      <button v-if="isLoggedIn && items.some(n => !n.is_read)" type="button" class="btn btn-ghost btn-sm" @click="readAll">Đọc tất cả</button>
    </header>

    <div v-if="!isLoggedIn" class="tb-guest">
      <EmptyState icon="🔔" title="Đăng nhập để xem thông báo" message="Theo dõi lượt thích, bình luận, trả lời và người theo dõi mới.">
        <template #actions>
          <button type="button" class="btn btn-primary btn-sm" @click="openAuth">Đăng nhập</button>
        </template>
      </EmptyState>
    </div>

    <template v-else>
      <div class="tb-filters">
        <button v-for="f in FILTERS" :key="f.key" type="button"
          :class="['chip', { active: filter === f.key }]"
          :aria-pressed="filter === f.key"
          @click="filter = f.key"
        >{{ f.icon }} {{ f.label }}</button>
      </div>

      <SkeletonList v-if="loading && !items.length" :count="6" />
      <EmptyState v-else-if="fetchError && !items.length" icon="⚠️" tone="error" title="Không thể tải thông báo" message="Không kết nối được máy chủ. Kiểm tra mạng và thử lại.">
        <template #actions><button type="button" class="btn btn-outline btn-sm" @click="load">Thử lại</button></template>
      </EmptyState>
      <EmptyState v-else-if="!filtered.length" icon="🔔" :title="filter === 'all' ? 'Chưa có thông báo' : 'Không có thông báo loại này'" message="Khi có hoạt động mới, bạn sẽ thấy ở đây." />
      <template v-else>
        <ul class="tb-list">
          <li v-for="n in filtered" :key="n.id">
            <button type="button" :class="['tb-item', { unread: !n.is_read }]" @click="open(n)">
              <span class="tb-icon" aria-hidden="true">{{ icon(n) }}</span>
              <span class="tb-body">
                <span class="tb-title">{{ n.title }}<span v-if="n.group_count > 1" class="tb-group"> +{{ n.group_count - 1 }}</span></span>
                <span v-if="n.body" class="tb-sub">{{ n.body }}</span>
                <time class="tb-time" :datetime="n.created_at">{{ timeAgo(n.created_at) }}</time>
              </span>
              <span v-if="!n.is_read" class="tb-dot" aria-label="Chưa đọc"></span>
            </button>
          </li>
        </ul>
        <button v-if="hasMore" type="button" class="btn btn-outline btn-sm tb-load-more" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? 'Đang tải...' : 'Xem thêm' }}
        </button>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
useReveal()
const { isLoggedIn, authHeaders } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()

const FILTERS = [
  { key: 'all', label: 'Tất cả', icon: '🔔' },
  { key: 'like', label: 'Thích', icon: '❤️' },
  { key: 'comment', label: 'Bình luận', icon: '💬' },
  { key: 'follow', label: 'Theo dõi', icon: '👤' },
  { key: 'mention', label: 'Nhắc đến', icon: '📣' },
] as const
type FilterKey = typeof FILTERS[number]['key']

const PAGE_SIZE = 50
const filter = ref<FilterKey>('all')
const items = ref<any[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const fetchError = ref(false)
const filtered = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter(n => n.type === filter.value)
})

async function load() {
  if (!isLoggedIn.value) { loading.value = false; return }
  loading.value = true
  fetchError.value = false
  try {
    const res = await $fetch<any>(`/api/notifications?limit=${PAGE_SIZE}`, { headers: authHeaders() })
    items.value = res.notifications || []
    hasMore.value = (res.notifications || []).length >= PAGE_SIZE
  } catch { fetchError.value = true } finally { loading.value = false }
}

async function loadMore() {
  loadingMore.value = true
  try {
    const res = await $fetch<any>(`/api/notifications?limit=${PAGE_SIZE}&offset=${items.value.length}`, { headers: authHeaders() })
    const more = res.notifications || []
    items.value.push(...more)
    hasMore.value = more.length >= PAGE_SIZE
  } catch { /* non-critical */ } finally { loadingMore.value = false }
}

function icon(n: any): string {
  if (n.type === 'like') return '❤️'
  if (n.type === 'comment') return '💬'
  if (n.type === 'follow') return '👤'
  if (n.type === 'mention') return '📣'
  if (n.type === 'repost') return '🔁'
  return '🔔'
}

async function open(n: any) {
  if (!n.is_read) {
    n.is_read = true
    try { await $fetch(`/api/notifications/${n.id}/read`, { method: 'POST', headers: authHeaders() }) } catch { /* ignore */ }
  }
  if (n.ref_type === 'post' && n.ref_id) navigateTo(`/bai-viet/${n.ref_id}`)
  else if (n.ref_type === 'entity' && n.ref_id) navigateTo(`/dia-diem/${n.ref_id}`)
  else if (n.ref_type === 'user' && n.ref_id) navigateTo(`/nguoi-dung/${n.ref_id}`)
}

async function readAll() {
  items.value.forEach(n => { n.is_read = true })
  try { await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() }) } catch { /* ignore */ }
}

onMounted(load)

useHead({
  title: 'Thông báo — vinhlong360',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/thong-bao') }],
})
</script>

<style scoped>
.tb-page { max-width: 640px; margin: 0 auto; }
.tb-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.tb-head h1 { margin: 0; }
.tb-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-1); }
.tb-item { display: flex; align-items: flex-start; gap: var(--space-3); width: 100%; text-align: left; padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); cursor: pointer; transition: background .2s var(--ease-out), border-color .2s var(--ease-out); }
.tb-item:hover { background: var(--bg-alt); }
.tb-item.unread { border-color: var(--primary); background: rgba(var(--primary-rgb), .04); }
.tb-icon { font-size: 1.25rem; flex-shrink: 0; line-height: 1.4; }
.tb-body { display: flex; flex-direction: column; gap: .15rem; flex: 1; min-width: 0; }
.tb-title { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink); }
.tb-group { font-size: .72rem; font-weight: 700; color: var(--primary, #219653); background: rgba(33,150,83,.1); padding: 1px 6px; border-radius: 100px; margin-left: 4px; }
.tb-sub { font-size: var(--text-sm); color: var(--ink-700); }
.tb-time { font-size: var(--text-xs); color: var(--muted); }
.tb-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary); flex-shrink: 0; margin-top: .35rem; }
.tb-guest { margin-top: var(--space-6); }
.tb-filters { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); overflow-x: auto; padding-bottom: var(--space-1); scrollbar-width: none; }
.tb-filters::-webkit-scrollbar { display: none; }
.tb-filters .chip { white-space: nowrap; }
.tb-load-more { display: block; width: 100%; margin-top: var(--space-3); }

/* ── Dark mode ── */
.dark .tb-item { background: var(--bg-alt); border-color: var(--line); }
.dark .tb-item:hover { background: color-mix(in srgb, var(--bg-alt) 80%, var(--ink) 5%); }
.dark .tb-item.unread { background: color-mix(in srgb, var(--primary) 8%, var(--bg-alt)); border-color: var(--primary); }

/* ── Mobile ── */
@media (max-width: 600px) {
  .tb-page { padding: var(--space-4) var(--space-3); }
  .tb-item { padding: var(--space-2) var(--space-3); gap: var(--space-2); }
  .tb-title { font-size: var(--text-xs); }
}
</style>
