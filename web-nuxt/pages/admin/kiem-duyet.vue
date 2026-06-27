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

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải nội dung chờ duyệt"><div class="spinner"></div></div>
    <div v-else-if="loadError" class="admin-empty">
      <p>Không tải được hàng đợi kiểm duyệt.</p>
      <button type="button" class="btn btn-secondary" @click="fetchQueue()">Thử lại</button>
    </div>
    <template v-else>
    <!-- Keyboard shortcuts legend -->
    <div class="mod-kbd-legend">
      <span class="mod-kbd-hint">Phím tắt:</span>
      <kbd>j</kbd><kbd>k</kbd> di chuyển
      <kbd>a</kbd> duyệt
      <kbd>r</kbd> từ chối
      <kbd>p</kbd> xem trước
      <span v-if="sessionApproved || sessionRejected" class="mod-session-stats">
        &#9679; Phiên này: <b class="mod-session-ok">{{ sessionApproved }}</b> duyệt, <b class="mod-session-rej">{{ sessionRejected }}</b> từ chối
      </span>
    </div>

    <!-- Batch action bar -->
    <div v-if="batchSelected.size" class="bulk-bar">
      <span>Đã chọn {{ batchSelected.size }}</span>
      <button type="button" class="btn-success" :disabled="batchBusy" @click="batchAction('approve')">Duyệt tất cả</button>
      <button type="button" class="btn-danger" :disabled="batchBusy" @click="batchAction('reject')">Từ chối tất cả</button>
      <button type="button" class="btn btn-outline btn-sm" @click="batchSelected = new Set()">Bỏ chọn</button>
    </div>

    <!-- Queue table -->
    <div class="admin-table-wrap">
    <table class="admin-table">
      <thead>
        <tr>
          <th scope="col" class="admin-th-check"><input type="checkbox" :checked="allBatchSelected" @change="toggleBatchAll" aria-label="Chọn tất cả" /></th>
          <th scope="col">Tác giả</th>
          <th scope="col">Nội dung</th>
          <th scope="col">Loại</th>
          <th scope="col">Trạng thái<span class="admin-help" data-tip="Chờ duyệt → Đã duyệt (hiện public) hoặc Từ chối (ẩn). Gắn cờ = user báo cáo." tabindex="0" role="img" aria-label="Giải thích trạng thái">?</span></th>
          <th scope="col">Ngày</th>
          <th scope="col">Thao tác</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="(p, idx) in queue" :key="p.id">
          <tr :class="{ 'mod-focused': idx === focusIdx }" @click="focusIdx = idx">
            <td><input type="checkbox" :checked="batchSelected.has(p.id)" @change="toggleBatch(p.id)" :aria-label="`Chọn bài ${p.id}`" @click.stop /></td>
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
              <button type="button" class="btn btn-ghost btn-sm" @click="openPreview(p)">Xem</button>
              <template v-if="p.moderation_status !== 'approved'">
                <button type="button" class="btn-success" :disabled="acting === p.id" @click="approve(p.id)">
                  <span v-if="acting === p.id" class="mod-btn-spin" aria-hidden="true"></span>{{ acting === p.id ? 'Đang duyệt' : 'Duyệt' }}
                </button>
              </template>
              <button v-if="p.moderation_status !== 'rejected'" type="button" class="btn-danger" :disabled="acting === p.id" @click="startReject(p.id)">Từ chối</button>
            </td>
          </tr>
          <tr v-if="rejectingId === p.id" class="mod-reject-row">
            <td colspan="7">
              <div class="mod-reject-container">
              <div class="mod-reject">
                <span class="mod-reject-label" aria-hidden="true">&#9888; Lý do:</span>
                <div class="mod-reason-presets">
                  <button v-for="r in REJECT_PRESETS" :key="r" type="button" class="mod-reason-chip" :class="{ active: rejectReason === r }" :title="REJECT_HINTS[r]" @click="rejectReason = rejectReason === r ? '' : r">{{ r }}</button>
                </div>
                <input
                  v-model="rejectReason" type="text" class="mod-reason-input"
                  placeholder="Hoặc nhập lý do khác…"
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
          <td colspan="7">
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

    <!-- Content preview modal -->
    <Transition name="modal-fade">
    <div v-if="previewPost" ref="modModalRef" class="modal-overlay show" role="dialog" aria-modal="true" aria-label="Xem bài viết" @click.self="previewPost = null">
      <div class="modal admin-modal-md">
        <div class="mod-preview-header">
          <div class="mod-author">
            <div class="mod-author-avatar">{{ (previewPost.display_name || '?')[0] }}</div>
            <div>
              <strong>{{ previewPost.display_name || previewPost.author || '—' }}</strong>
              <div class="mod-preview-meta">{{ previewPost.post_type }} &middot; {{ formatDate(previewPost.created_at) }}</div>
            </div>
          </div>
          <span class="mod-badge" :class="badgeOf(previewPost.moderation_status).cls">{{ badgeOf(previewPost.moderation_status).label }}</span>
        </div>
        <div class="mod-preview-body">{{ previewPost.content }}</div>
        <div v-if="previewPost.images?.length" class="mod-preview-images">
          <img v-for="(img, i) in previewPost.images" :key="i" :src="img" :alt="`Ảnh ${i+1}`" loading="lazy" width="200" height="150" />
        </div>
        <!-- Moderation notes -->
        <div class="mod-notes-section">
          <strong class="mod-notes-title">Ghi chú nội bộ</strong>
          <div v-if="previewPost.moderation_notes?.length" class="mod-notes-list">
            <div v-for="(n, i) in previewPost.moderation_notes" :key="i" class="mod-note-item">
              <span class="mod-note-text">{{ n.text }}</span>
              <time class="mod-note-time">{{ formatDate(n.at) }}</time>
            </div>
          </div>
          <div v-else class="mod-notes-empty">Chưa có ghi chú</div>
          <div class="mod-note-add">
            <input v-model="newNote" type="text" class="mod-note-input" placeholder="Thêm ghi chú…" @keyup.enter="addNote(previewPost.id)" />
            <button type="button" class="btn btn-sm btn-outline" :disabled="!newNote.trim() || noteSaving" @click="addNote(previewPost.id)">Thêm</button>
          </div>
        </div>
        <div class="mod-preview-actions">
          <button v-if="previewPost.moderation_status !== 'approved'" type="button" class="btn btn-success" @click="approve(previewPost.id); previewPost = null">Duyệt</button>
          <button v-if="previewPost.moderation_status !== 'rejected'" type="button" class="btn btn-danger" @click="startReject(previewPost.id); previewPost = null">Từ chối</button>
          <button type="button" class="btn btn-ghost" @click="previewPost = null">Đóng</button>
        </div>
      </div>
    </div>
    </Transition>

    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Kiểm duyệt — Admin' })

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

const REJECT_PRESETS = ['Spam', 'Vi phạm quy tắc', 'Nội dung không phù hợp', 'Quảng cáo', 'Trùng lặp'] as const
const REJECT_HINTS: Record<string, string> = {
  'Spam': 'Link lặp, nội dung vô nghĩa, bot',
  'Vi phạm quy tắc': 'Ngôn ngữ thù ghét, quấy rối, bạo lực',
  'Nội dung không phù hợp': 'Không liên quan du lịch/OCOP/cộng đồng',
  'Quảng cáo': 'Quảng cáo trá hình, tiếp thị lộ liễu',
  'Trùng lặp': 'Đăng lại bài đã có, copy-paste',
}

const queue = ref<any[]>([])
const modStats = ref<Record<string, number>>({})
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const previewPost = ref<any>(null)
const modModalRef = ref<HTMLElement | null>(null)
const modModalOpen = computed(() => !!previewPost.value)
useModalA11y(modModalOpen, modModalRef, { onClose: () => { previewPost.value = null } })
function openPreview(p: any) { previewPost.value = { ...p, moderation_notes: [...(p.moderation_notes || [])] } }
const status = ref<ModStatus>('review')
const expanded = ref<Set<string>>(new Set())
const rejectingId = ref<string | null>(null)
const rejectReason = ref('')
const batchSelected = ref<Set<string>>(new Set())
const batchBusy = ref(false)
const newNote = ref('')
const noteSaving = ref(false)

const allBatchSelected = computed(() => queue.value.length > 0 && queue.value.every(p => batchSelected.value.has(p.id)))
function toggleBatch(id: string) { batchSelected.value.has(id) ? batchSelected.value.delete(id) : batchSelected.value.add(id); batchSelected.value = new Set(batchSelected.value) }
function toggleBatchAll() { if (allBatchSelected.value) { batchSelected.value = new Set() } else { batchSelected.value = new Set(queue.value.map(p => p.id)) } }

async function batchAction(action: 'approve' | 'reject') {
  if (batchBusy.value || acting.value) return
  batchBusy.value = true
  try {
    await $fetch('/admin-api/moderation/batch', { method: 'POST', headers: authHeaders(), body: { post_ids: [...batchSelected.value], action } })
    showToast(`${batchSelected.value.size} bài đã ${action === 'approve' ? 'duyệt' : 'từ chối'}`, 'success')
    batchSelected.value = new Set()
    fetchQueue()
    fetchStats()
  } catch { showToast('Lỗi batch moderation', 'error') } finally {
    batchBusy.value = false
  }
}

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
  if (!append) loadError.value = false
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
    if (!append) loadError.value = true
    showToast('Không thể tải hàng đợi kiểm duyệt', 'error')
  } finally {
    loading.value = false
  }
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
  if (acting.value || batchBusy.value) return
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/approve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã duyệt bài viết', 'success')
    sessionApproved.value++
    removeFromQueue(id)
    fetchStats()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi duyệt'), 'error')
  } finally {
    acting.value = null
  }
}

function startReject(id: string) { rejectingId.value = id; rejectReason.value = '' }
function cancelReject() { rejectingId.value = null; rejectReason.value = '' }

async function confirmReject(id: string) {
  if (acting.value || batchBusy.value) return
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/reject`, {
      method: 'POST', headers: authHeaders(),
      body: { reason: rejectReason.value.trim() || undefined },
    })
    showToast('Đã từ chối bài viết', 'success')
    rejectingId.value = null
    rejectReason.value = ''
    sessionRejected.value++
    removeFromQueue(id)
    fetchStats()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi từ chối'), 'error')
  } finally {
    acting.value = null
  }
}

const sessionApproved = ref(0)
const sessionRejected = ref(0)

function removeFromQueue(id: string) {
  const idx = queue.value.findIndex(p => p.id === id)
  if (idx === -1) return
  queue.value.splice(idx, 1)
  total.value = Math.max(0, total.value - 1)
  batchSelected.value.delete(id)
  batchSelected.value = new Set(batchSelected.value)
  if (focusIdx.value >= queue.value.length) focusIdx.value = queue.value.length - 1
}

async function fetchStats() {
  try {
    const s = await $fetch<any>('/admin-api/moderation/stats', { headers: authHeaders() })
    modStats.value = s.counts || s || {}
  } catch { /* ignore */ }
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

const focusIdx = ref(-1)
const focusedPost = computed(() => queue.value[focusIdx.value] || null)

function onKeydown(e: KeyboardEvent) {
  if ((e.target as HTMLElement)?.tagName === 'INPUT' || (e.target as HTMLElement)?.tagName === 'TEXTAREA') return
  if (e.key === 'j') { focusIdx.value = Math.min(focusIdx.value + 1, queue.value.length - 1); e.preventDefault(); nextTick(() => document.querySelector('.mod-focused')?.scrollIntoView({ block: 'nearest' })) }
  else if (e.key === 'k') { focusIdx.value = Math.max(focusIdx.value - 1, 0); e.preventDefault(); nextTick(() => document.querySelector('.mod-focused')?.scrollIntoView({ block: 'nearest' })) }
  else if (e.key === 'a' && focusedPost.value && focusedPost.value.moderation_status !== 'approved') { approve(focusedPost.value.id); e.preventDefault() }
  else if (e.key === 'r' && focusedPost.value && focusedPost.value.moderation_status !== 'rejected') { startReject(focusedPost.value.id); e.preventDefault() }
  else if ((e.key === 'p' || e.key === 'Enter') && focusedPost.value && !previewPost.value) { openPreview(focusedPost.value); e.preventDefault() }
  else if (e.key === 'Escape' && previewPost.value) { previewPost.value = null; e.preventDefault() }
}

async function addNote(postId: string) {
  const text = newNote.value.trim()
  if (!text) return
  noteSaving.value = true
  try {
    await $fetch(`/admin-api/moderation/${postId}/note`, { method: 'POST', headers: authHeaders(), body: { note: text } })
    if (previewPost.value) {
      if (!previewPost.value.moderation_notes) previewPost.value.moderation_notes = []
      previewPost.value.moderation_notes.push({ text, at: new Date().toISOString() })
    }
    const q = queue.value.find(p => p.id === postId)
    if (q) {
      if (!q.moderation_notes) q.moderation_notes = []
      q.moderation_notes.push({ text, at: new Date().toISOString() })
    }
    newNote.value = ''
    showToast('Đã thêm ghi chú', 'success')
  } catch { showToast('Lỗi thêm ghi chú', 'error') }
  noteSaving.value = false
}

onMounted(() => {
  fetchQueue()
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.mod-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Keyboard shortcuts ── */
.mod-kbd-legend {
  display: flex; align-items: center; gap: .5rem; font-size: .75rem; color: var(--muted);
  margin-bottom: var(--space-3); flex-wrap: wrap;
}
.mod-kbd-hint { font-weight: 600; }
.mod-kbd-legend kbd {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; padding: 0 5px; border-radius: 4px;
  background: var(--bg-alt); border: 1px solid var(--line); font-size: .7rem;
  font-family: var(--font-mono, monospace); font-weight: 600;
}
.mod-session-stats { margin-left: auto; font-size: .72rem; }
.mod-session-ok { color: #219653; }
.mod-session-rej { color: #D94F3D; }
.mod-focused td { background: rgba(33,150,83,.06) !important; }
.mod-focused td:first-child { box-shadow: inset 3px 0 0 var(--primary, #219653); }

/* ── Status tabs ── */
.mod-tabs { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-5); }
.mod-tab {
  display: inline-flex; align-items: center; gap: 6px; min-height: 44px;
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
.mod-reason-presets { display: flex; flex-wrap: wrap; gap: 4px; width: 100%; }
.mod-reason-chip {
  padding: 4px 10px; border-radius: 100px; border: .5px solid var(--line);
  background: var(--bg); font-size: .76rem; font-weight: 500; color: var(--muted);
  cursor: pointer; transition: all .15s;
}
.mod-reason-chip:hover { border-color: #D94F3D; color: #D94F3D; }
.mod-reason-chip.active { background: rgba(217,79,61,.12); border-color: #D94F3D; color: #D94F3D; font-weight: 600; }
.mod-reason-input { flex: 1; min-width: 200px; padding: 9px 12px; border: .5px solid var(--line); border-radius: 10px; font-size: .85rem; background: var(--bg); color: var(--ink); min-height: 40px; }
.mod-reason-input:focus { outline: none; border-color: #D94F3D; box-shadow: 0 0 0 3px rgba(217,79,61,.1); }
.btn-ghost-sm { background: none; border: none; color: var(--muted); font-size: .82rem; cursor: pointer; padding: 8px 12px; border-radius: 8px; }
.btn-ghost-sm:hover { background: var(--bg-alt); color: var(--ink); }

.mod-load-more { margin-top: var(--space-4); }
.mod-empty-action {
  background: none; border: .5px solid var(--line); border-radius: 8px;
  padding: 7px 14px; font-size: .82rem; font-weight: 500; color: var(--primary, #219653);
  cursor: pointer; min-height: 44px;
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
.mod-preview-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.mod-preview-meta { font-size: .78rem; color: var(--muted); }
.mod-preview-body { white-space: pre-wrap; line-height: 1.7; margin-bottom: var(--space-4); }
.mod-preview-images { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-bottom: var(--space-4); }
.mod-preview-images img { max-width: 200px; max-height: 200px; border-radius: 8px; object-fit: cover; }
.mod-preview-actions { display: flex; gap: var(--space-2); justify-content: flex-end; }
.mod-notes-section { border-top: 1px solid var(--line); padding-top: var(--space-3); margin-bottom: var(--space-4); }
.mod-notes-title { font-size: .82rem; display: block; margin-bottom: var(--space-2); }
.mod-notes-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: var(--space-2); }
.mod-note-item { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-3); padding: 6px 10px; background: var(--bg-alt); border-radius: 8px; font-size: .82rem; }
.mod-note-text { flex: 1; }
.mod-note-time { font-size: .72rem; color: var(--muted); white-space: nowrap; }
.mod-notes-empty { font-size: .78rem; color: var(--muted); font-style: italic; margin-bottom: var(--space-2); }
.mod-note-add { display: flex; gap: var(--space-2); }
.mod-note-input { flex: 1; padding: 7px 12px; border: .5px solid var(--line); border-radius: 8px; font-size: .82rem; background: var(--bg); color: var(--ink); }
.mod-note-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(33,150,83,.1); }
</style>
