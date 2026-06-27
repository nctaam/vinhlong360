<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Duyệt ảnh</h1>
        <p class="img-subtitle">
          Ứng viên ảnh từ nguồn cấp phép (Wikimedia/Commons). Khớp tên tự động sai ~50% —
          chỉ ảnh được duyệt mới lên trang. Nhớ kiểm tra giấy phép trước khi duyệt.
        </p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchQueue">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <!-- Status filter tabs -->
    <div class="img-tabs" role="tablist" aria-label="Lọc theo trạng thái">
      <button
        v-for="t in STATUS_TABS" :key="t.key" type="button" role="tab"
        class="img-tab" :class="{ active: status === t.key }" :aria-selected="status === t.key"
        @click="setStatus(t.key)"
      >
        {{ t.label }}
        <span v-if="tabCount(t.key) != null" class="img-tab-count">{{ tabCount(t.key) }}</span>
      </button>
    </div>

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải ảnh chờ duyệt"><div class="spinner"></div></div>
    <div v-else-if="loadError" class="admin-empty">
      <p>Không tải được hàng đợi ảnh.</p>
      <button type="button" class="btn btn-secondary" @click="fetchQueue()">Thử lại</button>
    </div>
    <template v-else>
      <!-- License legend: orient admins on which badges are safe to approve -->
      <div v-if="queue.length" class="img-legend" aria-hidden="true">
        <span class="img-legend-item"><span class="img-legend-dot img-legend-ok"></span> Giấy phép OK (CC0 / CC-BY / công cộng)</span>
        <span class="img-legend-item"><span class="img-legend-dot img-legend-warn"></span> Không rõ — kiểm tra trước khi duyệt</span>
        <span class="admin-help" data-tip="% = độ khớp tên entity với tên ảnh Wikipedia. Dưới 60% thường sai — luôn xem ảnh gốc trước khi duyệt." tabindex="0" role="img" aria-label="Giải thích độ khớp">?</span>
      </div>
      <!-- Card grid: visual review needs the thumbnail front and centre -->
      <div v-if="queue.length" class="img-grid">
        <div v-for="s in queue" :key="s.id" class="img-card">
          <div class="img-thumb-wrap">
            <!-- Candidate is an external licensed URL (not yet re-hosted) -->
            <img
              :src="s.candidate_url" :alt="`Ứng viên ảnh cho ${s.entity_name || s.entity_id}`"
              class="img-thumb" loading="lazy" referrerpolicy="no-referrer" width="200" height="150"
              @error="onImgError"
            />
            <span class="img-conf" :class="confClass(s.match_confidence)">
              {{ Math.round((s.match_confidence ?? 0) * 100) }}%
            </span>
          </div>
          <div class="img-meta">
            <div class="img-entity">{{ s.entity_name || s.entity_id }}</div>
            <div
              class="img-conf-bar" :class="confClass(s.match_confidence)"
              :title="`Độ khớp tên: ${Math.round((s.match_confidence ?? 0) * 100)}%`"
              role="progressbar" :aria-valuenow="Math.round((s.match_confidence ?? 0) * 100)" aria-valuemin="0" aria-valuemax="100" :aria-label="`Độ khớp tên ${Math.round((s.match_confidence ?? 0) * 100)} phần trăm`"
            >
              <span class="img-conf-fill" :style="{ width: Math.round((s.match_confidence ?? 0) * 100) + '%' }"></span>
            </div>
            <div class="img-row">
              <span class="img-type-badge">{{ s.entity_type || '—' }}</span>
              <span
                v-if="s.license" class="img-lic-badge" :class="{ 'lic-warn': !licenseLooksOk(s.license) }"
                :title="licenseLooksOk(s.license) ? 'Giấy phép cho phép dùng (vẫn nên ghi nguồn nếu là CC-BY).' : 'Giấy phép chưa rõ — xác minh trước khi duyệt.'"
                :aria-label="`Giấy phép ${s.license}${licenseLooksOk(s.license) ? ', cho phép dùng' : ', chưa rõ — cần xác minh'}`"
              >
                {{ s.license }}
              </span>
              <span
                v-else class="img-lic-badge lic-warn"
                title="Không có thông tin giấy phép — không nên duyệt khi chưa xác minh nguồn."
                aria-label="Không rõ giấy phép, cần xác minh nguồn"
              >không rõ giấy phép</span>
            </div>
            <div v-if="s.wp_title" class="img-detail">
              <span class="img-detail-k">Wikipedia:</span> {{ s.wp_title }}
            </div>
            <div v-if="s.author" class="img-detail">
              <span class="img-detail-k">Tác giả:</span> {{ s.author }}
            </div>
            <div class="img-links">
              <a
                v-if="s.entity_id" :href="`/admin/entities?id=${s.entity_id}`" target="_blank"
                rel="noopener" class="img-entity-link"
              >Xem entity &#8599;</a>
              <a :href="s.candidate_url" target="_blank" rel="noopener nofollow" class="img-src-link">
                Mở ảnh gốc &#8599;
              </a>
            </div>
            <div v-if="s.status === 'rejected' && s.rejection_reason" class="img-detail img-reject-note">
              Lý do từ chối: {{ s.rejection_reason }}
            </div>
          </div>

          <div v-if="s.status === 'pending'" class="img-actions">
            <button type="button" class="btn-success" :disabled="acting === s.id" @click="approve(s.id)">
              {{ acting === s.id ? '...' : 'Duyệt & gắn ảnh' }}
            </button>
            <button type="button" class="btn-danger" :disabled="acting === s.id" @click="startReject(s.id)">
              Từ chối
            </button>
          </div>
          <div v-else class="img-status-final">
            <span class="img-badge" :class="badgeOf(s.status).cls">{{ badgeOf(s.status).label }}</span>
          </div>

          <div v-if="rejectingId === s.id" class="img-reject">
            <input
              v-model="rejectReason" type="text" class="img-reason-input"
              placeholder="Lý do từ chối (tuỳ chọn)…"
              @keyup.enter="confirmReject(s.id)" @keyup.esc="cancelReject"
            />
            <div class="img-reject-btns">
              <button type="button" class="btn-danger" :disabled="acting === s.id" @click="confirmReject(s.id)">
                {{ acting === s.id ? '...' : 'Xác nhận' }}
              </button>
              <button type="button" class="btn-ghost-sm" @click="cancelReject">Huỷ</button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="admin-empty-state">
        <div class="admin-empty-state-icon">&#127752;</div>
        <div class="admin-empty-state-text">
          {{ status === 'pending' ? 'Không có ứng viên ảnh nào chờ duyệt.' : 'Không có ứng viên nào.' }}
        </div>
        <div class="admin-empty-state-hint">
          {{ status === 'pending' ? 'Tất cả ảnh đã được xử lý. Chuyển tab để xem ảnh đã duyệt hoặc bị từ chối.' : 'Chuyển tab “Chờ duyệt” để xử lý ứng viên mới.' }}
        </div>
      </div>

      <button type="button" v-if="hasMore" class="btn btn-outline img-load-more" :disabled="loading" @click="loadMore">
        Xem thêm
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Duyệt ảnh — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

type ImgStatus = 'pending' | 'approved' | 'rejected'
const STATUS_TABS = [
  { key: 'pending', label: 'Chờ duyệt' },
  { key: 'approved', label: 'Đã duyệt' },
  { key: 'rejected', label: 'Từ chối' },
] as const
const BADGES: Record<string, { label: string; cls: string }> = {
  pending: { label: 'Chờ duyệt', cls: 'ib-pending' },
  approved: { label: 'Đã duyệt', cls: 'ib-approved' },
  rejected: { label: 'Từ chối', cls: 'ib-rejected' },
}
const LICENSE_OK = ['cc0', 'public domain', 'cc by', 'cc-by', 'creative commons', 'pdm', 'cc-by-sa']

const queue = ref<any[]>([])
const counts = ref<Record<string, number>>({})
const total = ref(0)
const offset = ref(0)
const limit = 30
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const status = ref<ImgStatus>('pending')
const rejectingId = ref<string | null>(null)
const rejectReason = ref('')

const hasMore = computed(() => queue.value.length < total.value)

function badgeOf(s: string) { return BADGES[s] || { label: s, cls: 'ib-pending' } }
function tabCount(key: string): number | null {
  const v = counts.value[key]
  return typeof v === 'number' ? v : null
}
function licenseLooksOk(lic: string): boolean {
  const l = (lic || '').toLowerCase()
  return LICENSE_OK.some(k => l.includes(k))
}
function confClass(c: number | undefined): string {
  const v = c ?? 0
  if (v >= 0.8) return 'conf-high'
  if (v >= 0.6) return 'conf-mid'
  return 'conf-low'
}
function onImgError(ev: Event) {
  const el = ev.target as HTMLImageElement
  el.classList.add('img-broken')
}

async function fetchQueue(append = false) {
  loading.value = true
  if (!append) loadError.value = false
  try {
    const q = await $fetch<any>(
      `/admin-api/image-suggestions?status=${status.value}&limit=${limit}&offset=${offset.value}`,
      { headers: authHeaders() },
    )
    const items = q.suggestions || []
    queue.value = append ? [...queue.value, ...items] : items
    total.value = q.total ?? items.length
    if (q.counts) counts.value = q.counts
  } catch {
    if (!append) loadError.value = true
    showToast('Không thể tải hàng đợi ảnh', 'error')
  } finally {
    loading.value = false
  }
}

function setStatus(s: ImgStatus) {
  if (status.value === s) return
  status.value = s
  offset.value = 0
  rejectingId.value = null
  fetchQueue()
}

function loadMore() { offset.value += limit; fetchQueue(true) }

async function approve(id: string) {
  if (acting.value) return
  acting.value = id
  try {
    await $fetch(`/admin-api/image-suggestions/${id}/approve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã duyệt và gắn ảnh vào entity', 'success')
    await refresh()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi duyệt ảnh'), 'error')
  } finally {
    acting.value = null
  }
}

function startReject(id: string) { rejectingId.value = id; rejectReason.value = '' }
function cancelReject() { rejectingId.value = null; rejectReason.value = '' }

async function confirmReject(id: string) {
  if (acting.value) return
  acting.value = id
  try {
    await $fetch(`/admin-api/image-suggestions/${id}/reject`, {
      method: 'POST', headers: authHeaders(),
      body: { reason: rejectReason.value.trim() || undefined },
    })
    showToast('Đã từ chối ứng viên ảnh', 'success')
    rejectingId.value = null
    rejectReason.value = ''
    await refresh()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi từ chối'), 'error')
  } finally {
    acting.value = null
  }
}

// Reload from the top so counts + list stay consistent after an action.
async function refresh() {
  offset.value = 0
  await fetchQueue()
}

onMounted(() => fetchQueue())
</script>

<style scoped>
.img-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; max-width: 60ch; line-height: 1.45; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Status tabs (match kiem-duyet) ── */
.img-tabs {
  display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-5);
  position: sticky; top: 0; z-index: 10;
  padding: var(--space-2) 0; background: var(--bg);
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
}
.img-tab {
  display: inline-flex; align-items: center; gap: 6px; min-height: 38px;
  padding: 7px 14px; border-radius: 100px; border: .5px solid var(--line);
  background: var(--bg); color: var(--muted); font-size: .82rem; font-weight: 500; cursor: pointer;
  transition: background .2s, color .2s, border-color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.img-tab:hover { border-color: var(--primary, #219653); color: var(--ink); }
.img-tab:active { transform: scale(.97); }
.img-tab.active { background: var(--primary, #219653); color: #fff; border-color: var(--primary, #219653); }
.img-tab:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.img-tab-count { font-size: .72rem; font-weight: 700; padding: 0 6px; border-radius: 10px; background: rgba(0,0,0,.08); }
.img-tab.active .img-tab-count { background: rgba(255,255,255,.25); }

/* ── Card grid ── */
.img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--space-4); }
.img-card {
  display: flex; flex-direction: column; border: .5px solid var(--line); border-radius: 14px;
  background: var(--bg); overflow: hidden;
}
.img-thumb-wrap { position: relative; aspect-ratio: 4 / 3; background: var(--bg-alt, #f2f2f2); overflow: hidden; }
.img-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.img-thumb.img-broken { object-fit: contain; opacity: .35; }
.img-conf {
  position: absolute; top: 8px; right: 8px; font-size: .68rem; font-weight: 700;
  padding: 2px 8px; border-radius: 100px; color: #fff; backdrop-filter: blur(4px);
}
.conf-high { background: rgba(var(--primary-rgb),.9); }
.conf-mid { background: rgba(201,138,26,.9); }
.conf-low { background: rgba(217,79,61,.9); }

.img-meta { padding: var(--space-3) var(--space-3) 0; display: flex; flex-direction: column; gap: 6px; }
.img-entity { font-weight: 600; font-size: .9rem; color: var(--ink); line-height: 1.3; }
.img-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.img-type-badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: .7rem; font-weight: 600; background: rgba(142,142,147,.1); color: var(--muted); }
.img-lic-badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: .7rem; font-weight: 700; background: rgba(var(--primary-rgb),.12); color: #219653; }
.img-lic-badge.lic-warn { background: rgba(217,79,61,.13); color: #D94F3D; }
.img-detail { font-size: .76rem; color: var(--muted); line-height: 1.4; }
.img-detail-k { font-weight: 600; color: var(--ink); }
.img-reject-note { color: #D94F3D; }
.img-src-link { font-size: .76rem; font-weight: 600; color: var(--primary-fg, #219653); text-decoration: none; }
.img-src-link:hover { text-decoration: underline; }

.img-actions { display: flex; gap: var(--space-2); padding: var(--space-3); margin-top: auto; }
.img-actions .btn-success, .img-actions .btn-danger { flex: 1; }
.img-status-final { padding: var(--space-3); margin-top: auto; }
.img-badge { display: inline-block; padding: 2px 9px; border-radius: 100px; font-size: .72rem; font-weight: 700; }
.ib-pending { background: rgba(var(--warning-rgb),.12); color: #C98A1A; }
.ib-approved { background: rgba(var(--primary-rgb),.12); color: #219653; }
.ib-rejected { background: rgba(142,142,147,.15); color: var(--muted); }

.img-reject { padding: 0 var(--space-3) var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); }
.img-reason-input { padding: 9px 12px; border: .5px solid var(--line); border-radius: 10px; font-size: .85rem; background: var(--bg); color: var(--ink); min-height: 40px; }
.img-reason-input:focus { outline: none; border-color: #D94F3D; box-shadow: 0 0 0 3px rgba(217,79,61,.1); }
.img-reject-btns { display: flex; gap: var(--space-2); }
.img-reject-btns .btn-danger { flex: 1; }
.btn-ghost-sm { background: none; border: none; color: var(--muted); font-size: .82rem; cursor: pointer; padding: 8px 12px; border-radius: 8px; }
.btn-ghost-sm:hover { background: var(--bg-alt); color: var(--ink); }

.img-load-more { margin-top: var(--space-5); }

/* ── License legend ── */
.img-legend { display: flex; flex-wrap: wrap; gap: var(--space-4); margin-bottom: var(--space-4); font-size: .76rem; color: var(--muted); }
.img-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.img-legend-dot { display: inline-block; width: 9px; height: 9px; border-radius: 3px; }
.img-legend-ok { background: #219653; }
.img-legend-warn { background: #D94F3D; }

/* ── Confidence bar (additive visual of match_confidence) ── */
.img-conf-bar { height: 4px; border-radius: 100px; background: rgba(142,142,147,.18); overflow: hidden; }
.img-conf-fill { display: block; height: 100%; border-radius: 100px; background: var(--muted); transition: width .3s cubic-bezier(.2,1,.4,1); }
.img-conf-bar.conf-high .img-conf-fill { background: #219653; }
.img-conf-bar.conf-mid .img-conf-fill { background: #C98A1A; }
.img-conf-bar.conf-low .img-conf-fill { background: #D94F3D; }

/* ── Meta links row ── */
.img-links { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.img-entity-link { font-size: .76rem; font-weight: 600; color: var(--primary-fg, #219653); text-decoration: none; }
.img-entity-link:hover { text-decoration: underline; }

/* ── Broken-image affordance ── */
.img-thumb-wrap::after {
  content: "Ảnh không tải được"; position: absolute; inset: 0;
  display: none; align-items: center; justify-content: center; text-align: center;
  font-size: .76rem; font-weight: 600; color: #D94F3D; padding: var(--space-3);
  background: rgba(217,79,61,.08);
}
.img-thumb-wrap:has(.img-broken)::after { display: flex; }

@media (prefers-reduced-motion: reduce) {
  .img-tab:active { transform: none; }
  .img-conf-fill { transition: none; }
}
.dark .img-type-badge { background: rgba(255,255,255,.06); }
.dark .img-tab-count { background: rgba(255,255,255,.12); }
.dark .img-tabs { background: var(--bg); }
.dark .img-conf-bar { background: rgba(255,255,255,.12); }
</style>
