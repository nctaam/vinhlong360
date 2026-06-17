<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Chất lượng dữ liệu</h1>
        <p class="admin-muted" style="margin-top:4px">Kiểm duyệt candidate GPT-5.5 theo chính sách evidence-only trước khi cập nhật dữ liệu public.</p>
      </div>
      <button class="admin-refresh" :disabled="loading" @click="refreshAll(true)">🔄 Làm mới</button>
    </div>

    <div v-if="summary" class="stat-grid dq-stats">
      <div class="stat-card">
        <div class="stat-value">{{ summary.data?.public_entities || 0 }}</div>
        <div class="stat-label">Entity public</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-value">{{ summary.data?.missing_source || 0 }}</div>
        <div class="stat-label">Thiếu nguồn</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-value">{{ summary.data?.missing_location || 0 }}</div>
        <div class="stat-label">Thiếu tọa độ</div>
      </div>
      <div class="stat-card warn">
        <div class="stat-value">{{ summary.data?.missing_place_id_non_place || 0 }}</div>
        <div class="stat-label">Thiếu placeId</div>
      </div>
      <div class="stat-card ok">
        <div class="stat-value">{{ summary.candidates?.auto_apply || 0 }}</div>
        <div class="stat-label">Có thể auto-apply</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ summary.candidates?.needs_review || 0 }}</div>
        <div class="stat-label">Cần duyệt</div>
      </div>
    </div>

    <p v-if="summary?.cache?.exists" class="dq-cache-info">
      Queue cache: {{ summary.cache.modified_at || 'unknown' }}
    </p>

    <div class="dq-toolbar">
      <select v-model="kind" class="input" @change="fetchCandidates(true)">
        <option value="">Tất cả loại</option>
        <option value="source">Nguồn</option>
        <option value="location">Tọa độ</option>
        <option value="placeid">PlaceId</option>
        <option value="accuracy">Accuracy</option>
        <option value="relationship">Relationship</option>
      </select>
      <select v-model="bucket" class="input" @change="fetchCandidates(true)">
        <option value="needs_review">Cần duyệt</option>
        <option value="auto_apply">Auto-apply</option>
        <option value="reject">Reject</option>
        <option value="">Tất cả bucket</option>
      </select>
      <button class="btn btn-outline" :disabled="!autoApplyIds.length || applying" @click="dryRunSelected">
        Dry-run selected
      </button>
      <button class="btn btn-primary" :disabled="!autoApplyIds.length || applying" @click="applySelected">
        Apply selected
      </button>
    </div>

    <p v-if="applyResult" class="dq-apply-result">
      {{ applyResult.dry_run ? 'Dry-run' : 'Apply' }}: {{ applyResult.applied_count }} áp dụng, {{ applyResult.skipped_count }} bỏ qua.
      <span v-if="applyResult.batch_id">Batch: {{ applyResult.batch_id }}</span>
      <span v-if="applyResult.backup">Backup: {{ applyResult.backup }}</span>
    </p>

    <div class="admin-table-wrap dq-table-wrap">
      <table class="admin-table dq-table">
        <thead>
          <tr>
            <th class="dq-th-checkbox"></th>
            <th>Entity</th>
            <th>Field</th>
            <th>Confidence</th>
            <th>Đề xuất</th>
            <th>Evidence</th>
            <th>Lý do</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in candidates" :key="c.candidate_id">
            <td>
              <input
                v-if="c.bucket === 'auto_apply'"
                v-model="selectedIds"
                type="checkbox"
                :value="c.candidate_id"
                aria-label="Chọn candidate"
              />
            </td>
            <td>
              <NuxtLink :to="`/dia-diem/${c.entity_id}`" target="_blank">{{ c.entity_id }}</NuxtLink>
              <small>{{ c.bucket }}</small>
            </td>
            <td>{{ c.field }}</td>
            <td>
              <span :class="['dq-confidence', confidenceClass(c.confidence)]">{{ pct(c.confidence) }}</span>
            </td>
            <td><code>{{ preview(c.suggested_value) }}</code></td>
            <td>
              <a
                v-for="url in (c.evidence_urls || []).slice(0, 2)"
                :key="url"
                :href="url"
                target="_blank"
                rel="noopener noreferrer"
              >{{ host(url) }}</a>
              <span v-if="!(c.evidence_urls || []).length">—</span>
            </td>
            <td>{{ c.reason || c.status || '—' }}</td>
          </tr>
          <tr v-if="!loading && !candidates.length">
            <td colspan="7" class="admin-empty-row">Không có candidate phù hợp.</td>
          </tr>
          <tr v-if="loading">
            <td colspan="7" class="admin-empty-row">Đang tải dữ liệu…</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="admin-pagination">
      <button :disabled="offset === 0 || loading" @click="prevPage">Trước</button>
      <span>{{ offset + 1 }} - {{ Math.min(offset + limit, total) }} / {{ total }}</span>
      <button :disabled="offset + limit >= total || loading" @click="nextPage">Sau</button>
    </div>

    <section class="dq-history">
      <div class="dq-section-head">
        <div>
          <h2>Lịch sử apply</h2>
          <p>Batch đã ghi vào dữ liệu public, kèm diff và backup để rollback khi cần.</p>
        </div>
        <button class="btn btn-outline btn-sm" :disabled="historyLoading" @click="fetchHistory">Tải lại</button>
      </div>
      <div v-if="historyLoading" class="dq-history-empty">Đang tải lịch sử…</div>
      <div v-else-if="!history.length" class="dq-history-empty">Chưa có batch nào được apply.</div>
      <div v-else class="dq-history-list">
        <article v-for="h in history" :key="h.batch_id" class="dq-history-card">
          <div class="dq-history-card-head">
            <div>
              <strong>{{ h.record_type === 'rollback' ? 'Rollback' : 'Apply' }} {{ h.batch_id }}</strong>
              <small>{{ h.applied_at || h.rolled_back_at || 'unknown time' }}</small>
            </div>
            <button
              v-if="h.record_type === 'apply'"
              class="btn btn-outline btn-sm danger"
              :disabled="!!rollingBack"
              @click="rollbackBatch(h.batch_id)"
            >{{ rollingBack === h.batch_id ? 'Đang rollback…' : 'Rollback' }}</button>
          </div>
          <p class="dq-history-meta">
            {{ h.applied_count || h.restored_changes || 0 }} thay đổi
            <span v-if="h.skipped_count">· {{ h.skipped_count }} bỏ qua</span>
            <span v-if="h.backup">· backup: {{ h.backup }}</span>
            <span v-if="h.restored_from">· restored: {{ h.restored_from }}</span>
          </p>
          <div v-if="h.changes?.length" class="dq-diff-list">
            <div v-for="change in h.changes.slice(0, 4)" :key="change.candidate_id" class="dq-diff-item">
              <div>
                <strong>{{ change.entity_name || change.entity_id }}</strong>
                <small>{{ change.field }} · {{ pct(change.confidence) }}</small>
              </div>
              <code>{{ preview(change.before) }} → {{ preview(change.after) }}</code>
            </div>
            <small v-if="h.changes.length > 4" class="dq-more">+{{ h.changes.length - 4 }} diff khác</small>
          </div>
          <div v-if="h.skipped?.length" class="dq-skipped-list">
            <strong>Skipped cần rà soát</strong>
            <div v-for="item in h.skipped.slice(0, 5)" :key="item.candidate_id" class="dq-skipped-item">
              <span>{{ item.entity_id || item.candidate_id }}</span>
              <small>{{ item.field || 'unknown' }} · {{ item.reason || 'skipped' }}<template v-if="item.duplicate_of"> · trùng {{ item.duplicate_of }}</template></small>
            </div>
            <small v-if="h.skipped.length > 5" class="dq-more">+{{ h.skipped.length - 5 }} skipped khác</small>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const summary = ref<any>(null)
const candidates = ref<any[]>([])
const selectedIds = ref<string[]>([])
const applyResult = ref<any>(null)
const kind = ref('')
const bucket = ref('needs_review')
const total = ref(0)
const offset = ref(0)
const limit = 100
const loading = ref(false)
const applying = ref(false)
const history = ref<any[]>([])
const historyLoading = ref(false)
const rollingBack = ref('')

const autoApplyIds = computed(() => selectedIds.value.filter((id) => candidates.value.some((c) => c.candidate_id === id && c.bucket === 'auto_apply')))

async function fetchSummary(refresh = false) {
  summary.value = await $fetch<any>('/admin-api/data-quality/summary', {
    headers: authHeaders(),
    query: refresh ? { refresh: true } : {},
  })
}

async function fetchCandidates(reset = false, refresh = false) {
  if (reset) offset.value = 0
  loading.value = true
  applyResult.value = null
  try {
    const res = await $fetch<any>('/admin-api/data-quality/review', {
      headers: authHeaders(),
      query: {
        kind: kind.value || undefined,
        bucket: bucket.value || undefined,
        limit,
        offset: offset.value,
        ...(refresh ? { refresh: true } : {}),
      },
    })
    candidates.value = res.candidates || []
    total.value = res.total || 0
    selectedIds.value = selectedIds.value.filter((id) => candidates.value.some((c) => c.candidate_id === id))
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể tải review queue', 'error')
  }
  loading.value = false
}

async function refreshAll(refresh = false) {
  try {
    await Promise.all([fetchSummary(refresh), fetchCandidates(false, refresh), fetchHistory()])
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể làm mới dữ liệu', 'error')
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await $fetch<any>('/admin-api/data-quality/history', {
      headers: authHeaders(),
      query: { limit: 20 },
    })
    history.value = res.history || []
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể tải lịch sử apply', 'error')
  }
  historyLoading.value = false
}

async function runApply(dryRun: boolean) {
  if (!autoApplyIds.value.length) return
  applying.value = true
  try {
    applyResult.value = await $fetch<any>('/admin-api/data-quality/apply', {
      method: 'POST',
      headers: authHeaders(),
      body: { candidate_ids: autoApplyIds.value, dry_run: dryRun },
    })
    showToast(dryRun ? 'Dry-run hoàn tất' : 'Đã apply candidate được chọn', 'success')
    if (!dryRun) await refreshAll(true)
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể apply candidate', 'error')
  }
  applying.value = false
}

function dryRunSelected() {
  runApply(true)
}

function applySelected() {
  if (!confirm(`Apply ${autoApplyIds.value.length} candidate evidence-only vào web/data.json?`)) return
  runApply(false)
}

async function rollbackBatch(batchId: string) {
  if (!batchId || !confirm(`Rollback batch ${batchId}? Dữ liệu hiện tại sẽ được backup trước khi khôi phục.`)) return
  rollingBack.value = batchId
  try {
    await $fetch(`/admin-api/data-quality/rollback/${encodeURIComponent(batchId)}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    showToast('Đã rollback batch', 'success')
    await refreshAll(true)
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể rollback batch', 'error')
  }
  rollingBack.value = ''
}

function prevPage() {
  offset.value = Math.max(offset.value - limit, 0)
  fetchCandidates(false)
}

function nextPage() {
  offset.value += limit
  fetchCandidates(false)
}

function preview(value: any) {
  const text = typeof value === 'string' ? value : JSON.stringify(value ?? null)
  if (!text) return '—'
  return text.length > 180 ? `${text.slice(0, 180)}…` : text
}

function pct(value: any) {
  const num = Number(value || 0)
  return `${Math.round(num * 100)}%`
}

function confidenceClass(value: any) {
  const num = Number(value || 0)
  if (num >= 0.9) return 'high'
  if (num >= 0.7) return 'mid'
  return 'low'
}

function host(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

onMounted(() => refreshAll())
</script>

<style scoped>
.dq-stats .stat-card.warn .stat-value { color: var(--warning, #e67e22); }
.dq-stats .stat-card.ok .stat-value { color: var(--primary, #219653); }
.dq-th-checkbox { width: 42px; }
.dq-cache-info { margin: 12px 0 0; color: var(--muted); font-size: .88rem; }
.dq-toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 16px 0; }
.dq-toolbar .input { flex: 0 0 170px; }
.dq-apply-result { background: var(--bg, #f3fbf5); border: 1px solid var(--primary, #219653); padding: 10px 12px; border-radius: 8px; color: var(--primary, #219653); }
.dq-apply-result span { display: block; margin-top: 3px; }
.dq-table-wrap { margin-top: 12px; }
.dq-table td { vertical-align: top; }
.dq-table td small { display: block; color: var(--muted); margin-top: 3px; }
.dq-table code { white-space: pre-wrap; word-break: break-word; font-size: .78rem; }
.dq-table a { display: block; color: var(--primary); font-weight: 600; word-break: break-word; }
.dq-confidence { display: inline-block; min-width: 48px; text-align: center; padding: 3px 7px; border-radius: 999px; font-size: .78rem; font-weight: 800; }
.dq-confidence.high { background: rgba(33, 150, 83, .1); color: var(--primary, #219653); }
.dq-confidence.mid { background: var(--warning-bg, rgba(230, 126, 34, .1)); color: var(--warning, #e67e22); }
.dq-confidence.low { background: var(--error-bg, rgba(217, 79, 61, .1)); color: var(--error, #D94F3D); }
.admin-pagination span { display: inline-flex; align-items: center; color: var(--muted); font-size: .88rem; }
.dq-history { margin-top: 28px; }
.dq-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
.dq-section-head h2 { margin: 0; font-size: 1.1rem; }
.dq-section-head p { margin: 4px 0 0; color: var(--muted); }
.dq-history-empty { padding: 16px; border: 1px dashed var(--line); border-radius: 8px; color: var(--muted); }
.dq-history-list { display: grid; gap: 10px; }
.dq-history-card { padding: 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); }
.dq-history-card-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.dq-history-card-head strong { display: block; word-break: break-word; }
.dq-history-card-head small, .dq-diff-item small, .dq-more { color: var(--muted); }
.dq-history-meta { margin: 8px 0; color: var(--muted); font-size: .86rem; word-break: break-word; }
.dq-diff-list { display: grid; gap: 8px; margin-top: 10px; }
.dq-diff-item { display: grid; grid-template-columns: minmax(160px, 240px) 1fr; gap: 10px; align-items: start; padding: 8px; background: var(--bg-alt, #f8faf9); border-radius: 6px; }
.dq-diff-item code { white-space: pre-wrap; word-break: break-word; font-size: .76rem; }
.dq-skipped-list { display: grid; gap: 6px; margin-top: 10px; padding: 10px; border: 1px solid var(--warning, #e67e22); border-radius: 6px; background: var(--warning-bg, rgba(230, 126, 34, .08)); }
.dq-skipped-list > strong { font-size: .86rem; color: var(--warning, #e67e22); }
.dq-skipped-item { display: grid; gap: 2px; }
.dq-skipped-item span { font-weight: 700; word-break: break-word; }
.dq-skipped-item small { color: var(--muted); word-break: break-word; }
.btn.danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }

@media (max-width: 780px) {
  .admin-page-head { flex-direction: column; }
  .dq-toolbar .input { flex: 1 1 150px; }
  .dq-section-head, .dq-history-card-head { flex-direction: column; }
  .dq-diff-item { grid-template-columns: 1fr; }
}
</style>
