<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Kiểm duyệt</h1>
        <p class="mod-subtitle">Duyệt bài viết cộng đồng (gồm bài bị gắn cờ tự động)</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchQueue">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <!-- Status filter tabs -->
    <div class="mod-tabs" role="tablist" aria-label="Lọc theo trạng thái">
      <button
        v-for="t in STATUS_TABS" :key="t.key" type="button" role="tab"
        class="mod-tab" :class="{ active: status === t.key }" :aria-selected="status === t.key"
        @click="setStatus(t.key)"
      >
        {{ t.label }}
        <span v-if="tabCount(t.key) != null" class="mod-tab-count">{{ tabCount(t.key) }}</span>
      </button>
    </div>

    <!-- Stats row -->
    <div class="stat-grid">
      <div class="stat-card" :class="{ 'status-warn': (modStats.pending || 0) > 0 }">
        <div class="mod-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#9203;</div>
        <div><div class="stat-value">{{ modStats.pending || 0 }}</div><div class="stat-label">Chờ duyệt</div></div>
      </div>
      <div class="stat-card" :class="{ 'status-error': (modStats.flagged || 0) > 0 }">
        <div class="mod-icon" style="background: rgba(217,79,61,.1); color: #D94F3D;">&#9873;</div>
        <div><div class="stat-value">{{ modStats.flagged || 0 }}</div><div class="stat-label">Gắn cờ</div></div>
      </div>
      <div class="stat-card status-ok">
        <div class="mod-icon" style="background: rgba(33,150,83,.1); color: #219653;">&#9989;</div>
        <div><div class="stat-value">{{ modStats.approved || 0 }}</div><div class="stat-label">Đã duyệt</div></div>
      </div>
      <div class="stat-card">
        <div class="mod-icon" style="background: rgba(142,142,147,.12); color: var(--muted);">&#10060;</div>
        <div><div class="stat-value">{{ modStats.rejected || 0 }}</div><div class="stat-label">Từ chối</div></div>
      </div>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
    <!-- Queue table -->
    <div class="admin-table-wrap">
    <table class="admin-table">
      <thead>
        <tr>
          <th>Tác giả</th>
          <th>Nội dung</th>
          <th>Loại</th>
          <th>Trạng thái</th>
          <th>Ngày</th>
          <th>Thao tác</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="p in queue" :key="p.id">
          <tr>
            <td>
              <div class="mod-author">
                <div class="mod-author-avatar">{{ (p.display_name || p.author || '?')[0] }}</div>
                <span>{{ p.display_name || p.author || p.phone || '—' }}</span>
              </div>
            </td>
            <td class="mod-content-cell">
              <span :class="{ 'mod-content-truncate': !expanded.has(p.id) }">{{ p.content }}</span>
              <button v-if="(p.content || '').length > 90" type="button" class="mod-expand" @click="toggleExpand(p.id)">
                {{ expanded.has(p.id) ? 'Thu gọn' : 'Xem đầy đủ' }}
              </button>
            </td>
            <td><span class="mod-type-badge">{{ p.post_type }}</span></td>
            <td><span class="mod-badge" :class="badgeOf(p.moderation_status).cls">{{ badgeOf(p.moderation_status).label }}</span></td>
            <td class="admin-td-muted"><time :datetime="p.created_at">{{ formatDate(p.created_at) }}</time></td>
            <td class="admin-actions">
              <template v-if="p.moderation_status !== 'approved'">
                <button type="button" class="btn-success" :disabled="acting === p.id" @click="approve(p.id)">
                  <span v-if="acting === p.id" class="mod-btn-spin" aria-hidden="true"></span>{{ acting === p.id ? 'Đang duyệt' : 'Duyệt' }}
                </button>
              </template>
              <button v-if="p.moderation_status !== 'rejected'" type="button" class="btn-danger" :disabled="acting === p.id" @click="startReject(p.id)">Từ chối</button>
            </td>
          </tr>
          <tr v-if="rejectingId === p.id" class="mod-reject-row">
            <td colspan="6">
              <div class="mod-reject-container">
              <div class="mod-reject">
                <span class="mod-reject-label" aria-hidden="true">&#9888; Lý do:</span>
                <input
                  v-model="rejectReason" type="text" class="mod-reason-input"
                  placeholder="Lý do từ chối (tuỳ chọn, lưu vào nhật ký)…"
                  @keyup.enter="confirmReject(p.id)" @keyup.esc="cancelReject"
                />
                <button type="button" class="btn-danger" :disabled="acting === p.id" @click="confirmReject(p.id)">
                  <span v-if="acting === p.id" class="mod-btn-spin" aria-hidden="true"></span>{{ acting === p.id ? 'Đang xử lý' : 'Xác nhận từ chối' }}
                </button>
                <button type="button" class="btn-ghost-sm" @click="cancelReject">Huỷ</button>
              </div>
              </div>
            </td>
          </tr>
        </template>
        <tr v-if="!queue.length">
          <td colspan="6">
            <div class="admin-empty-state">
              <div class="admin-empty-state-icon">{{ emptyState.icon }}</div>
              <div class="admin-empty-state-text">{{ emptyState.text }}</div>
              <button
                v-if="status !== 'review'" type="button" class="mod-empty-action"
                @click="setStatus('review')"
              >Về hàng đợi cần duyệt &rarr;</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    </div>

    <!-- Load more -->
    <button type="button" v-if="hasMore" class="btn btn-outline mod-load-more" :disabled="loading" @click="loadMore">
      Xem thêm
    </button>

    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

type ModStatus = 'review' | 'pending' | 'flagged' | 'approved' | 'rejected'
const STATUS_TABS = [
  { key: 'review', label: 'Cần duyệt' },
  { key: 'pending', label: 'Chờ duyệt' },
  { key: 'flagged', label: 'Gắn cờ' },
  { key: 'approved', label: 'Đã duyệt' },
  { key: 'rejected', label: 'Từ chối' },
] as const
const BADGES: Record<string, { label: string; cls: string }> = {
  pending: { label: 'Chờ duyệt', cls: 'mb-pending' },
  flagged: { label: '⚑ Gắn cờ', cls: 'mb-flagged' },
  approved: { label: 'Đã duyệt', cls: 'mb-approved' },
  rejected: { label: 'Từ chối', cls: 'mb-rejected' },
}

const queue = ref<any[]>([])
const modStats = ref<Record<string, number>>({})
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const acting = ref<string | null>(null)
const status = ref<ModStatus>('review')
const expanded = ref<Set<string>>(new Set())
const rejectingId = ref<string | null>(null)
const rejectReason = ref('')

const hasMore = computed(() => queue.value.length < total.value)

function badgeOf(s: string) { return BADGES[s] || { label: s, cls: 'mb-pending' } }

const EMPTY_STATES: Record<string, { icon: string; text: string }> = {
  review: { icon: '🎉', text: 'Hàng đợi đã sạch. Tốt lắm!' },
  pending: { icon: '🎉', text: 'Không có bài nào đang chờ duyệt.' },
  flagged: { icon: '✓', text: 'Không có bài nào bị gắn cờ.' },
  approved: { icon: '📭', text: 'Chưa có bài viết nào đã duyệt.' },
  rejected: { icon: '📭', text: 'Chưa có bài viết nào bị từ chối.' },
}
const emptyState = computed(() => EMPTY_STATES[status.value] || { icon: '📭', text: 'Không có bài nào.' })

function tabCount(key: string): number | null {
  if (key === 'review') return (modStats.value.pending || 0) + (modStats.value.flagged || 0)
  const v = modStats.value[key]
  return typeof v === 'number' ? v : null
}

async function fetchQueue(append = false) {
  loading.value = true
  try {
    const [q, s] = await Promise.all([
      $fetch<any>(`/admin-api/moderation/queue?status=${status.value}&page=${page.value}&limit=20`, { headers: authHeaders() }),
      page.value === 1 ? $fetch<any>('/admin-api/moderation/stats', { headers: authHeaders() }) : Promise.resolve(null),
    ])
    const posts = q.posts || q || []
    queue.value = append ? [...queue.value, ...posts] : posts
    total.value = q.total ?? posts.length
    if (s) modStats.value = s.counts || s || {}
  } catch {
    showToast('Không thể tải hàng đợi kiểm duyệt', 'error')
  }
  loading.value = false
}

function setStatus(s: ModStatus) {
  if (status.value === s) return
  status.value = s
  page.value = 1
  expanded.value = new Set()
  rejectingId.value = null
  fetchQueue()
}

function loadMore() { page.value++; fetchQueue(true) }

function toggleExpand(id: string) {
  const n = new Set(expanded.value)
  n.has(id) ? n.delete(id) : n.add(id)
  expanded.value = n
}

async function approve(id: string) {
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/approve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã duyệt bài viết', 'success')
    await refreshSamePage()
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi duyệt', 'error')
  }
  acting.value = null
}

function startReject(id: string) { rejectingId.value = id; rejectReason.value = '' }
function cancelReject() { rejectingId.value = null; rejectReason.value = '' }

async function confirmReject(id: string) {
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/reject`, {
      method: 'POST', headers: authHeaders(),
      body: { reason: rejectReason.value.trim() || undefined },
    })
    showToast('Đã từ chối bài viết', 'success')
    rejectingId.value = null
    rejectReason.value = ''
    await refreshSamePage()
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi từ chối', 'error')
  }
  acting.value = null
}

// After an action, reload from page 1 up to the current page count so the list
// stays consistent without losing the user's scroll position entirely.
async function refreshSamePage() {
  page.value = 1
  await fetchQueue()
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchQueue())
</script>

<style scoped>
.mod-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Status tabs ── */
.mod-tabs { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-5); }
.mod-tab {
  display: inline-flex; align-items: center; gap: 6px; min-height: 38px;
  padding: 7px 14px; border-radius: 100px; border: .5px solid var(--line);
  background: var(--bg); color: var(--muted); font-size: .82rem; font-weight: 500; cursor: pointer;
  transition: background .2s, color .2s, border-color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.mod-tab:hover { border-color: var(--primary, #219653); color: var(--ink); }
.mod-tab:active { transform: scale(.97); }
.mod-tab.active { background: var(--primary, #219653); color: #fff; border-color: var(--primary, #219653); }
.mod-tab:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.mod-tab-count { font-size: .72rem; font-weight: 700; padding: 0 6px; border-radius: 100px; background: var(--line); color: var(--muted); }
.mod-tab.active .mod-tab-count { background: rgba(255,255,255,.2); color: #fff; }

/* ── Stat card icon ── */
.stat-card { display: flex; align-items: center; gap: var(--space-4); }
.mod-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0; transition: transform .25s cubic-bezier(.2,1,.4,1); }
.stat-card:hover .mod-icon { transform: scale(1.08); }
/* Urgency accent for queue cards with pending/flagged items (dashboard-at-a-glance) */
.stat-card.status-warn { border-left: 4px solid var(--warning, #FF9F0A); }
.stat-card.status-error { border-left: 4px solid var(--error, #D94F3D); }
.stat-card.status-warn .mod-icon,
.stat-card.status-error .mod-icon { font-size: 1.3rem; font-weight: 700; }

/* ── Author cell ── */
.mod-author { display: flex; align-items: center; gap: var(--space-3); }
.mod-author-avatar { width: 32px; height: 32px; border-radius: 50%; background: rgba(52,120,246,.1); color: #3478F6; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .76rem; flex-shrink: 0; text-transform: uppercase; }
.mod-author > span { font-weight: 600; color: var(--ink); }

/* ── Content cell ── */
.mod-content-cell { max-width: 420px; }
.mod-content-truncate { display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.mod-expand { display: inline-block; margin-top: 4px; background: none; border: none; padding: 0; color: var(--primary-fg, #219653); font-size: .76rem; font-weight: 600; cursor: pointer; }
.mod-expand:hover { text-decoration: underline; }
.mod-expand:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; border-radius: 4px; }

/* Keyboard affordance: highlight the row whose action button is focused (mirrors tr:hover) */
.admin-table tbody tr:focus-within td { background: rgba(0,0,0,.04); }
.dark .admin-table tbody tr:focus-within td { background: rgba(255,255,255,.05); }

/* ── Type + status badges ── */
.mod-type-badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: .72rem; font-weight: 600; background: rgba(142,142,147,.08); color: var(--muted); }
.mod-badge { display: inline-block; padding: 2px 9px; border-radius: 100px; font-size: .72rem; font-weight: 700; white-space: nowrap; }
.mb-pending { background: rgba(255,159,10,.12); color: #C98A1A; }
.mb-flagged { background: rgba(217,79,61,.13); color: #D94F3D; }
.mb-approved { background: rgba(33,150,83,.12); color: #219653; }
.mb-rejected { background: rgba(142,142,147,.15); color: var(--muted); }

/* ── Reject reason inline ── */
.mod-reject-row td { background: rgba(217,79,61,.04); }
.mod-reject-container { background: var(--bg); border: 1px solid rgba(217,79,61,.2); border-radius: 10px; padding: var(--space-3); margin: var(--space-2) 0; }
.mod-reject-label { font-size: .8rem; font-weight: 600; color: #D94F3D; white-space: nowrap; flex-shrink: 0; }
.mod-reject { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }

/* Inline action spinner (reuses global admin-spin keyframe) */
.mod-btn-spin { display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: -1px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: admin-spin .6s linear infinite; }
.mod-reason-input { flex: 1; min-width: 200px; padding: 9px 12px; border: .5px solid var(--line); border-radius: 10px; font-size: .85rem; background: var(--bg); color: var(--ink); min-height: 40px; }
.mod-reason-input:focus { outline: none; border-color: #D94F3D; box-shadow: 0 0 0 3px rgba(217,79,61,.1); }
.btn-ghost-sm { background: none; border: none; color: var(--muted); font-size: .82rem; cursor: pointer; padding: 8px 12px; border-radius: 8px; }
.btn-ghost-sm:hover { background: var(--bg-alt); color: var(--ink); }

.mod-load-more { margin-top: var(--space-4); }
.mod-empty-action {
  background: none; border: .5px solid var(--line); border-radius: 8px;
  padding: 7px 14px; font-size: .82rem; font-weight: 500; color: var(--primary, #219653);
  cursor: pointer; min-height: 36px;
  transition: border-color .25s, background .25s, transform .15s cubic-bezier(.2,1,.4,1);
}
.mod-empty-action:hover { border-color: var(--primary, #219653); background: rgba(33,150,83,.04); }
.mod-empty-action:active { transform: scale(.96); }
.mod-empty-action:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { .mod-empty-action:active { transform: none; } }

@media (prefers-reduced-motion: reduce) {
  .stat-card:hover .mod-icon { transform: none; }
  .mod-tab:active { transform: none; }
  .mod-btn-spin { animation: none; }
}
.dark .mod-author-avatar { background: rgba(52,120,246,.15); }
.dark .mod-type-badge { background: rgba(255,255,255,.06); }
.dark .mod-tab.active .mod-tab-count { background: rgba(255,255,255,.2); color: #fff; }
</style>
