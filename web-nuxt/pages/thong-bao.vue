<template>
  <section class="page tb-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Thông báo' }]" />
    <header class="tb-head">
      <div class="tb-head-text">
        <p class="dateline-eyebrow">HỘP THƯ · SỔ TAY CỦA BẠN</p>
        <h1>Thông báo</h1>
      </div>
      <button v-if="isLoggedIn && items.some(n => !n.is_read)" type="button" class="btn btn-ghost btn-sm" @click="readAll">Đọc tất cả</button>
    </header>

    <div v-if="!isLoggedIn" class="tb-guest">
      <EmptyState icon="🔔" title="Đăng nhập để xem thông báo" message="Theo dõi lượt thích, bình luận, trả lời và người theo dõi mới.">
        <template #actions>
          <button type="button" class="btn btn-primary btn-sm" @click="openAuth()">Đăng nhập</button>
        </template>
      </EmptyState>
    </div>

    <template v-else>
      <div class="tb-filters">
        <button v-for="f in FILTERS" :key="f.key" type="button" role="tab"
          :class="['chip', { active: filter === f.key }]"
          :aria-selected="filter === f.key"
          @click="filter = f.key"
        >{{ f.icon }} {{ f.label }}</button>
      </div>

      <SkeletonList v-if="loading && !items.length" :count="6" />
      <EmptyState v-else-if="fetchError && !items.length" icon="⚠️" tone="error" title="Không thể tải thông báo" message="Không kết nối được máy chủ. Kiểm tra mạng và thử lại.">
        <template #actions><button type="button" class="btn btn-outline btn-sm" @click="load">Thử lại</button></template>
      </EmptyState>
      <EmptyState v-else-if="!filtered.length" icon="🔔" :title="filter === 'all' ? 'Chưa có thông báo' : 'Không có thông báo loại này'" :message="emptyHint" />
      <template v-else>
        <ul class="tb-list">
          <li v-for="n in filtered" :key="n.id" :class="['tb-item', { unread: !n.is_read }]">
            <NuxtLink
              v-if="notificationTargetPath(n)"
              :to="notificationTargetPath(n)!"
              class="tb-item-link"
              @click="markReadOnOpen(n)"
            >
              <span class="tb-icon-chip" aria-hidden="true">{{ icon(n) }}</span>
              <span class="tb-body">
                <span class="tb-item-title">{{ n.title }}<span v-if="n.group_count > 1" class="tb-group"> +{{ n.group_count - 1 }}</span></span>
                <span v-if="n.body" class="tb-sub">{{ n.body }}</span>
                <time class="tb-time" :datetime="n.created_at">{{ timeAgo(n.created_at) }}</time>
              </span>
              <span v-if="!n.is_read" class="tb-dot" role="status" aria-label="Chưa đọc" title="Chưa đọc"></span>
            </NuxtLink>
            <div
              v-else
              class="tb-item-link"
              role="button"
              tabindex="0"
              @click="open(n)"
              @keydown.enter.prevent="open(n)"
              @keydown.space.prevent="open(n)"
            >
              <span class="tb-icon-chip" aria-hidden="true">{{ icon(n) }}</span>
              <span class="tb-body">
                <span class="tb-item-title">{{ n.title }}<span v-if="n.group_count > 1" class="tb-group"> +{{ n.group_count - 1 }}</span></span>
                <span v-if="n.body" class="tb-sub">{{ n.body }}</span>
                <time class="tb-time" :datetime="n.created_at">{{ timeAgo(n.created_at) }}</time>
              </span>
              <span v-if="!n.is_read" class="tb-dot" role="status" aria-label="Chưa đọc" title="Chưa đọc"></span>
            </div>
            <button type="button" class="tb-dismiss" aria-label="Xóa thông báo" @click.stop="dismiss(n)">✕</button>
          </li>
        </ul>
        <LoadMoreButton v-if="hasMore" :loading="loadingMore" @load="loadMore" />
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
const { isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
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
const emptyHint = computed(() => {
  const hints: Record<string, string> = {
    like: 'Thích bài viết để bắt đầu nhận thông báo lượt thích.',
    comment: 'Viết bình luận để nhận phản hồi từ cộng đồng.',
    follow: 'Theo dõi người dùng để nhận thông báo khi họ đăng bài mới.',
    mention: 'Khi ai đó nhắc đến bạn trong bài viết hoặc bình luận, bạn sẽ thấy ở đây.',
  }
  return hints[filter.value] || 'Khi có hoạt động mới, bạn sẽ thấy ở đây.'
})

async function load() {
  if (!isLoggedIn.value) { loading.value = false; return }
  loading.value = true
  fetchError.value = false
  try {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE) })
    const res = await $fetch<any>(`/api/notifications?${params}`, { headers: authHeaders() })
    items.value = res.notifications || []
    hasMore.value = (res.notifications || []).length >= PAGE_SIZE
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    fetchError.value = true
  } finally { loading.value = false }
}

async function loadMore() {
  if (loadingMore.value) return
  loadingMore.value = true
  try {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(items.value.length) })
    const res = await $fetch<any>(`/api/notifications?${params}`, { headers: authHeaders() })
    const more = res.notifications || []
    items.value.push(...more)
    hasMore.value = more.length >= PAGE_SIZE
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) handleSessionExpired()
  } finally { loadingMore.value = false }
}

function icon(n: any): string {
  if (n.type === 'like') return '❤️'
  if (n.type === 'comment') return '💬'
  if (n.type === 'follow') return '👤'
  if (n.type === 'mention') return '📣'
  if (n.type === 'repost') return '🔁'
  return '🔔'
}

async function markReadOnOpen(n: any) {
  if (n.is_read) return
  const wasRead = n.is_read
  n.is_read = true
  try {
    await $fetch(`/api/notifications/${encodePathId(n.id)}/read`, { method: 'POST', headers: authHeaders() })
  } catch (e: unknown) {
    n.is_read = wasRead
    if (getStatusCode(e) === 401) handleSessionExpired()
  }
}

async function open(n: any) {
  await markReadOnOpen(n)
  const target = notificationTargetPath(n)
  if (target) navigateTo(target)
}

async function readAll() {
  const previous = items.value.map(n => ({ n, is_read: n.is_read }))
  items.value.forEach(n => { n.is_read = true })
  try {
    await $fetch('/api/notifications/read-all', { method: 'POST', headers: authHeaders() })
  } catch (e: unknown) {
    previous.forEach(p => { p.n.is_read = p.is_read })
    if (getStatusCode(e) === 401) handleSessionExpired()
  }
}

async function dismiss(n: any) {
  const idx = items.value.indexOf(n)
  items.value = items.value.filter(x => x.id !== n.id)
  try {
    await $fetch(`/api/notifications/${encodePathId(n.id)}`, { method: 'DELETE', headers: authHeaders() })
  } catch (e: unknown) {
    if (idx >= 0) items.value.splice(idx, 0, n)
    if (getStatusCode(e) === 401) handleSessionExpired()
  }
}

onMounted(load)

watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    load()
  } else {
    items.value = []
    hasMore.value = false
    loading.value = false
    loadingMore.value = false
    fetchError.value = false
  }
})

useHead({
  title: 'Thông báo — vinhlong360',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/thong-bao') }],
})
</script>

<style scoped>
.tb-page { max-width: 640px; margin: 0 auto; }
.tb-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); gap: var(--space-3); }
.tb-head-text { min-width: 0; }
.tb-head h1 { margin: 0; font-family: var(--font-editorial); font-weight: 600; }
/* Local page masthead eyebrow — small-caps dateline + hairline tick, matches
   the site's area/ward eyebrow pattern (tai-khoan.vue/cai-dat.vue) but scoped
   here (not promoted global). */
.dateline-eyebrow {
  display: flex; align-items: center; gap: .4rem;
  font-family: var(--font-sans); font-size: .78rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; color: var(--ink-700);
  margin: 0 0 .25rem;
}
.dateline-eyebrow::before { content: ""; width: 14px; height: 1.5px; background: var(--primary); flex-shrink: 0; }
.tb-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-1); }
/* .tb-item is the card (li) — .tb-item-link is the inner "open notification"
   affordance (NuxtLink or role=button div). Kept as siblings, not nested,
   because .tb-dismiss is a real <button>: an <a href> must not contain other
   interactive content per the HTML spec (see EntityCard's .card-save, which
   sits alongside its NuxtLink for the same reason), so pulling the dismiss
   button out avoids invalid nesting and any native-navigation ambiguity. */
.tb-item { position: relative; display: flex; align-items: flex-start; gap: var(--space-3); width: 100%; padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); transition: background .2s var(--ease-out), border-color .2s var(--ease-out); }
.tb-item:hover { background: var(--bg-alt); }
.tb-item.unread { border-color: var(--primary); background: rgba(var(--primary-rgb), .04); }
/* Tri-province sediment tick — left-edge hairline echo of the site-wide
   river→amber→clay thread (same recipe as EntityCard .card-rule / PostCard
   .thread-rule), so the notification list ties into the shared system. */
.tb-item::before {
  content: ""; position: absolute; left: 3px; top: 50%; transform: translateY(-50%);
  width: 3px; height: 22px; border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.tb-item-link { display: flex; align-items: flex-start; gap: var(--space-3); flex: 1; min-width: 0; text-align: left; text-decoration: none; color: inherit; cursor: pointer; border-radius: var(--radius-sm); }
.tb-item-link:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.tb-icon-chip {
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; flex-shrink: 0; border-radius: 50%;
  font-size: 1.05rem; line-height: 1; background: var(--bg-alt);
}
.tb-item.unread .tb-icon-chip { background: rgba(var(--primary-rgb), .12); }
.tb-body { display: flex; flex-direction: column; gap: .15rem; flex: 1; min-width: 0; }
.tb-item-title { font-size: var(--text-sm); font-family: var(--font-editorial); font-weight: 600; color: var(--ink); }
.tb-group { font-size: .72rem; font-weight: 700; color: var(--primary); background: rgba(var(--primary-rgb, 33,150,83), .1); padding: 1px 6px; border-radius: 100px; margin-left: var(--space-1); }
.tb-sub { font-size: var(--text-sm); color: var(--ink-700); }
.tb-time { font-size: var(--text-xs); color: var(--muted); }
.tb-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary); flex-shrink: 0; margin-top: .35rem; }
.tb-dismiss {
  flex-shrink: 0; min-width: 44px; min-height: 44px; border: none; background: none;
  color: var(--ink-700); cursor: pointer; font-size: .75rem; border-radius: var(--radius-full);
  opacity: 0; transition: opacity .15s, background .15s, color .15s;
  display: flex; align-items: center; justify-content: center; align-self: center;
}
.tb-item:hover .tb-dismiss, .tb-dismiss:focus-visible { opacity: 1; }
.tb-dismiss:hover { background: var(--bg-alt); color: var(--error); }
.tb-dismiss:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.tb-guest { margin-top: var(--space-6); }
.tb-filters { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); overflow-x: auto; padding-bottom: var(--space-1); scrollbar-width: none; }
.tb-filters::-webkit-scrollbar { display: none; }
.tb-filters .chip { white-space: nowrap; }

/* ── Dark mode ── */
.dark .tb-item { background: var(--bg-alt); border-color: var(--line); }
.dark .tb-item:hover { background: color-mix(in srgb, var(--bg-alt) 80%, var(--ink) 5%); }
.dark .tb-item.unread { background: color-mix(in srgb, var(--primary) 8%, var(--bg-alt)); border-color: var(--primary); }
.dark .tb-item::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.dark .tb-icon-chip { background: rgba(var(--white-rgb),.06); }
.dark .tb-item.unread .tb-icon-chip { background: color-mix(in srgb, var(--primary) 18%, transparent); }

/* ── Mobile ── */
@media (max-width: 600px) {
  .tb-page { padding: var(--space-4) var(--space-3); }
  .tb-item { padding: var(--space-2) var(--space-3); gap: var(--space-2); }
  .tb-item-link { gap: var(--space-2); }
  .tb-item::before { left: 2px; width: 2px; height: 18px; }
  .tb-item-title { font-size: var(--text-xs); }
}
</style>
