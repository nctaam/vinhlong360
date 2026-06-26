<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Chất lượng dữ liệu</h1>
        <p class="admin-muted" style="margin-top: var(--space-1)">Kiểm duyệt candidate GPT-5.5 theo chính sách evidence-only trước khi cập nhật dữ liệu public.</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="refreshAll(true)">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div v-if="summary" class="stat-grid dq-stats">
      <div class="stat-card">
        <div class="dq-icon" style="background: rgba(52,120,246,.1); color: #3478F6;">&#127760;</div>
        <div>
          <div class="stat-value">{{ summary.data?.public_entities || 0 }}</div>
          <div class="stat-label">Entity public</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="dq-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#128218;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_source || 0 }}</div>
          <div class="stat-label">Thiếu nguồn</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="dq-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#128205;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_location || 0 }}</div>
          <div class="stat-label">Thiếu tọa độ</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="dq-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#127963;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_place_id_non_place || 0 }}</div>
          <div class="stat-label">Thiếu placeId</div>
        </div>
      </div>
      <div class="stat-card ok">
        <div class="dq-icon" style="background: rgba(33,150,83,.1); color: #219653;">&#9989;</div>
        <div>
          <div class="stat-value">{{ summary.candidates?.auto_apply || 0 }}</div>
          <div class="stat-label">Có thể auto-apply</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="dq-icon" style="background: rgba(175,82,222,.1); color: #AF52DE;">&#128065;</div>
        <div>
          <div class="stat-value">{{ summary.candidates?.needs_review || 0 }}</div>
          <div class="stat-label">Cần duyệt</div>
        </div>
      </div>
    </div>

    <p v-if="summary?.cache?.exists" class="dq-cache-info">
      Queue cache: {{ summary.cache.modified_at || 'unknown' }}
    </p>

    <div class="dq-toolbar">
      <select v-model="kind" class="input" aria-label="Lọc theo loại" @change="fetchCandidates(true)">
        <option value="">Tất cả loại</option>
        <option value="source">Nguồn</option>
        <option value="location">Tọa độ</option>
        <option value="placeid">PlaceId</option>
        <option value="accuracy">Accuracy</option>
        <option value="relationship">Relationship</option>
      </select>
      <select v-model="bucket" class="input" aria-label="Lọc theo trạng thái" @change="fetchCandidates(true)">
        <option value="needs_review">Cần duyệt</option>
        <option value="auto_apply">Auto-apply</option>
        <option value="reject">Reject</option>
        <option value="">Tất cả bucket</option>
      </select>
      <span class="admin-help" data-tip="Auto = đủ evidence, apply an toàn. Duyệt = cần admin kiểm tra. Loại = evidence yếu hoặc trùng." tabindex="0" role="img" aria-label="Giải thích bucket">?</span>
      <label v-if="pageAutoApplyIds.length" class="dq-select-all">
        <input
          type="checkbox"
          :checked="allPageAutoSelected"
          :aria-label="`Chọn tất cả ${pageAutoApplyIds.length} candidate auto-apply trên trang`"
          @change="toggleSelectAllAuto(($event.target as HTMLInputElement).checked)"
        />
        Chọn tất cả auto-apply
      </label>
      <span v-if="pageAutoApplyIds.length" class="dq-ready-hint">{{ pageAutoApplyIds.length }} sẵn sàng apply</span>
      <button type="button" class="btn btn-outline" :disabled="!autoApplyIds.length || applying" @click="dryRunSelected">
        Dry-run selected
      </button>
      <button type="button" class="btn btn-primary" :disabled="!autoApplyIds.length || applying" @click="applySelected">
        Apply selected
        <span v-if="autoApplyIds.length" class="dq-btn-count">{{ autoApplyIds.length }}</span>
      </button>
    </div>

    <div v-if="applyResult" class="dq-apply-result" :class="{ 'dq-apply-result--warn': Number(applyResult.skipped_count) > 0 && !Number(applyResult.applied_count) }" role="status">
      <div class="dq-apply-result-head">
        <span class="dq-apply-result-icon">{{ Number(applyResult.skipped_count) > 0 && !Number(applyResult.applied_count) ? '⚠' : '✓' }}</span>
        <strong>{{ applyResult.dry_run ? 'Dry-run hoàn tất' : 'Apply hoàn tất' }}</strong>
      </div>
      <div class="dq-apply-result-stats">
        <span class="dq-apply-result-stat"><b>{{ applyResult.applied_count }}</b> áp dụng</span>
        <span class="dq-apply-result-stat"><b>{{ applyResult.skipped_count }}</b> bỏ qua</span>
      </div>
      <div v-if="applyResult.batch_id" class="dq-apply-result-meta">
        Batch: <code class="dq-mono">{{ applyResult.batch_id }}</code>
        <button type="button" class="dq-copy-btn" :aria-label="`Sao chép batch ${applyResult.batch_id}`" @click="copyBatch(String(applyResult.batch_id))">{{ copiedBatch ? 'Đã chép' : 'Sao chép' }}</button>
      </div>
      <div v-if="applyResult.backup" class="dq-apply-result-meta">Backup: <code class="dq-mono">{{ applyResult.backup }}</code></div>
    </div>

    <div class="admin-table-wrap dq-table-wrap">
      <table class="admin-table dq-table">
        <thead>
          <tr>
            <th scope="col" class="dq-th-checkbox"></th>
            <th scope="col" class="dq-th-sev">Mức<span class="admin-help" data-tip="Auto (xanh) = apply tự động. Duyệt (cam) = cần kiểm tra. Loại (đỏ) = bỏ qua." tabindex="0" role="img" aria-label="Giải thích mức">?</span></th>
            <th scope="col">Entity</th>
            <th scope="col">Field</th>
            <th scope="col">Đề xuất</th>
            <th scope="col">Evidence</th>
            <th scope="col">Lý do</th>
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
              <span class="dq-sev-badge" :class="`dq-sev-${bucketSeverity(c.bucket)}`" :title="bucketLabel(c.bucket)">{{ bucketLabel(c.bucket) }}</span>
            </td>
            <td>
              <NuxtLink :to="`/dia-diem/${c.entity_id}`" target="_blank" rel="noopener">{{ c.entity_id }}</NuxtLink>
              <small>{{ c.bucket }}</small>
            </td>
            <td>{{ c.field }}</td>
            <td><code>{{ preview(c.suggested_value) }}</code></td>
            <td>
              <a
                v-for="url in (c.evidence_urls || []).slice(0, 2)"
                :key="url"
                :href="url"
                :title="url"
                target="_blank"
                rel="noopener noreferrer"
              >{{ host(url) }}</a>
              <span v-if="(c.evidence_urls || []).length > 2" class="dq-evidence-more" :title="(c.evidence_urls || []).slice(2).map((u: string) => host(u)).join(', ')">+{{ (c.evidence_urls || []).length - 2 }} nữa</span>
              <span v-if="!(c.evidence_urls || []).length">—</span>
            </td>
            <td>{{ c.reason || c.status || '—' }}</td>
          </tr>
          <tr v-if="!loading && !candidates.length">
            <td colspan="7" class="dq-empty-cell">
              <div class="admin-empty-state">
                <div class="admin-empty-state-icon">{{ hasActiveFilters ? '🔍' : '✓' }}</div>
                <div class="admin-empty-state-text">{{ hasActiveFilters ? 'Không có vấn đề' : 'Chất lượng dữ liệu tốt' }}</div>
                <div class="admin-empty-state-hint">{{ hasActiveFilters ? 'Dữ liệu hiện tại đáp ứng tiêu chí lọc.' : 'Không còn candidate nào chờ kiểm duyệt.' }}</div>
              </div>
            </td>
          </tr>
          <tr v-if="loading">
            <td colspan="7" class="admin-empty-row">Đang tải dữ liệu…</td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav class="admin-pagination" role="navigation" aria-label="Phân trang">
      <button type="button" :disabled="offset === 0 || loading" @click="prevPage">Trước</button>
      <span class="dq-page-info">{{ total ? `Hiển thị ${offset + 1}–${Math.min(offset + limit, total)} / ${total} candidate` : '0 candidate' }}</span>
      <button type="button" :disabled="offset + limit >= total || loading" @click="nextPage">Sau</button>
    </nav>

    <section class="dq-history">
      <div class="dq-section-head">
        <div>
          <h2>Lịch sử apply</h2>
          <p>Batch đã ghi vào dữ liệu public, kèm diff và backup để rollback khi cần.</p>
        </div>
        <button type="button" class="btn btn-outline btn-sm" :disabled="historyLoading" @click="fetchHistory">Tải lại</button>
      </div>
      <div v-if="historyLoading" class="dq-history-empty">Đang tải lịch sử…</div>
      <div v-else-if="!history.length" class="dq-history-empty">Chưa có batch nào được apply.</div>
      <div v-else class="dq-history-list">
        <article v-for="h in history" :key="h.batch_id" class="dq-history-card" :class="h.record_type === 'rollback' ? 'dq-history-card--rollback' : 'dq-history-card--apply'">
          <div class="dq-history-card-head">
            <div>
              <span class="dq-status-badge" :class="h.record_type === 'rollback' ? 'dq-sev-warning' : 'dq-sev-success'">{{ h.record_type === 'rollback' ? 'Đã rollback' : 'Đã apply' }}</span>
              <strong>{{ h.record_type === 'rollback' ? 'Rollback' : 'Apply' }} {{ h.batch_id }}</strong>
              <time v-if="h.applied_at || h.rolled_back_at" :datetime="h.applied_at || h.rolled_back_at"><small>{{ h.applied_at || h.rolled_back_at }}</small></time><small v-else>unknown time</small>
            </div>
            <button type="button"
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
                <small>{{ change.field }}</small>
              </div>
              <code>{{ preview(change.before) }} → {{ preview(change.after) }}</code>
            </div>
            <small v-if="h.changes.length > 4" class="dq-more">+{{ h.changes.length - 4 }} diff khác</small>
          </div>
          <div v-if="h.skipped?.length" class="dq-skipped-list">
            <strong>Skipped cần rà soát</strong>
            <div v-for="item in h.skipped.slice(0, 5)" :key="item.candidate_id" class="dq-skipped-item">
              <NuxtLink v-if="item.entity_id" :to="`/dia-diem/${item.entity_id}`" target="_blank" rel="noopener" class="dq-skipped-entity">{{ item.entity_id }}</NuxtLink>
              <span v-else class="dq-skipped-entity">{{ item.candidate_id }}</span>
              <small>
                {{ item.field || 'unknown' }}
                <span class="dq-skipped-reason" :class="`dq-sev-${reasonSeverity(item.reason)}`">{{ item.reason || 'skipped' }}</span>
                <template v-if="item.duplicate_of"> · trùng {{ item.duplicate_of }}</template>
              </small>
            </div>
            <small v-if="h.skipped.length > 5" class="dq-more">+{{ h.skipped.length - 5 }} skipped khác</small>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

const summary = ref<Record<string, unknown> | null>(null)
const candidates = ref<Entity[]>([])
const selectedIds = ref<string[]>([])
const applyResult = ref<Record<string, unknown> | null>(null)
const kind = ref('')
const bucket = ref('needs_review')
const total = ref(0)
const offset = ref(0)
const limit = 100
const loading = ref(false)
const applying = ref(false)
const history = ref<Entity[]>([])
const historyLoading = ref(false)
const rollingBack = ref('')

const copiedBatch = ref(false)

const autoApplyIds = computed(() => selectedIds.value.filter((id) => candidates.value.some((c) => c.candidate_id === id && c.bucket === 'auto_apply')))
const hasActiveFilters = computed(() => !!kind.value || !!bucket.value)
const pageAutoApplyIds = computed(() => candidates.value.filter((c) => c.bucket === 'auto_apply').map((c) => c.candidate_id))
const allPageAutoSelected = computed(() => pageAutoApplyIds.value.length > 0 && pageAutoApplyIds.value.every((id) => selectedIds.value.includes(id)))

function bucketSeverity(b?: string) {
  if (b === 'auto_apply') return 'success'
  if (b === 'reject') return 'error'
  return 'warning'
}

function bucketLabel(b?: string) {
  if (b === 'auto_apply') return 'Auto'
  if (b === 'reject') return 'Loại'
  return 'Duyệt'
}

function reasonSeverity(reason?: string) {
  const r = (reason || '').toLowerCase()
  if (r.includes('duplicate') || r.includes('trùng')) return 'error'
  if (r.includes('override') || r.includes('manual')) return 'warning'
  return 'neutral'
}

function toggleSelectAllAuto(checked: boolean) {
  if (checked) {
    const next = new Set(selectedIds.value)
    pageAutoApplyIds.value.forEach((id) => next.add(id))
    selectedIds.value = Array.from(next)
  } else {
    const page = new Set(pageAutoApplyIds.value)
    selectedIds.value = selectedIds.value.filter((id) => !page.has(id))
  }
}

async function copyBatch(batchId: string) {
  try {
    await navigator.clipboard.writeText(batchId)
    copiedBatch.value = true
    setTimeout(() => { copiedBatch.value = false }, 1500)
  } catch {
    showToast('Không thể sao chép', 'error')
  }
}

async function fetchSummary(refresh = false) {
  try {
    summary.value = await $fetch<Record<string, unknown>>('/admin-api/data-quality/summary', {
      headers: authHeaders(),
      query: refresh ? { refresh: true } : {},
    })
  } catch {
    showToast('Không thể tải tổng quan chất lượng', 'error')
  }
}

async function fetchCandidates(reset = false, refresh = false) {
  if (reset) offset.value = 0
  loading.value = true
  applyResult.value = null
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/data-quality/review', {
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
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Không thể tải review queue', 'error')
  }
  loading.value = false
}

async function refreshAll(refresh = false) {
  try {
    await Promise.all([fetchSummary(refresh), fetchCandidates(false, refresh), fetchHistory()])
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Không thể làm mới dữ liệu', 'error')
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/data-quality/history', {
      headers: authHeaders(),
      query: { limit: 20 },
    })
    history.value = res.history || []
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Không thể tải lịch sử apply', 'error')
  }
  historyLoading.value = false
}

async function runApply(dryRun: boolean) {
  if (!autoApplyIds.value.length) return
  applying.value = true
  try {
    applyResult.value = await $fetch<Record<string, unknown>>('/admin-api/data-quality/apply', {
      method: 'POST',
      headers: authHeaders(),
      body: { candidate_ids: autoApplyIds.value, dry_run: dryRun },
    })
    showToast(dryRun ? 'Dry-run hoàn tất' : 'Đã apply candidate được chọn', 'success')
    if (!dryRun) await refreshAll(true)
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Không thể apply candidate', 'error')
  }
  applying.value = false
}

function dryRunSelected() {
  runApply(true)
}

function applyFieldBreakdown() {
  const counts: Record<string, number> = {}
  for (const id of autoApplyIds.value) {
    const c = candidates.value.find((x) => x.candidate_id === id)
    const f = c?.field || 'khác'
    counts[f] = (counts[f] || 0) + 1
  }
  return Object.entries(counts).map(([f, n]) => `  • ${f}: ${n}`).join('\n')
}

async function applySelected() {
  const n = autoApplyIds.value.length
  if (!n) return
  const msg = [
    `Áp dụng ${n} candidate evidence-only vào web/data.json.`,
    '',
    'Theo field:',
    applyFieldBreakdown(),
    '',
    'Thao tác này ghi trực tiếp vào dữ liệu public và KHÔNG thể hoàn tác tự động (chỉ rollback thủ công bằng backup).',
    '',
    `Xác nhận apply ${n} candidate?`,
  ].join('\n')
  if (!await confirmDialog(msg, { danger: true })) return
  runApply(false)
}

async function rollbackBatch(batchId: string) {
  if (!batchId) return
  const rec = history.value.find((h) => h.batch_id === batchId)
  const changed = rec ? (rec.applied_count || rec.restored_changes || 0) : 0
  const msg = [
    `Rollback batch ${batchId}.`,
    changed ? `Số thay đổi sẽ được khôi phục: ${changed}.` : '',
    '',
    'Dữ liệu hiện tại sẽ được backup TRƯỚC khi khôi phục từ snapshot của batch này.',
    '',
    'Xác nhận rollback?',
  ].filter(Boolean).join('\n')
  if (!await confirmDialog(msg, { danger: true })) return
  rollingBack.value = batchId
  try {
    await $fetch(`/admin-api/data-quality/rollback/${encodeURIComponent(batchId)}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    showToast('Đã rollback batch', 'success')
    await refreshAll(true)
  } catch (e: unknown) {
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

function preview(value: unknown) {
  const text = typeof value === 'string' ? value : JSON.stringify(value ?? null)
  if (!text) return '—'
  return text.length > 180 ? `${text.slice(0, 180)}…` : text
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
.dq-stats .stat-card { display: flex; align-items: center; gap: var(--space-4); }
.dq-stats .stat-card.warn .stat-value { color: var(--warning, #e67e22); }
.dq-stats .stat-card.ok .stat-value { color: var(--primary, #219653); }
.dq-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; flex-shrink: 0;
}
.dq-th-checkbox { width: 42px; }
.dq-th-sev { width: 64px; }
.dq-cache-info { margin: var(--space-3) 0 0; color: var(--muted); font-size: .88rem; }
.dq-toolbar { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; margin: var(--space-4) 0; }
.dq-toolbar .input { flex: 0 0 170px; }
.dq-select-all { display: inline-flex; align-items: center; gap: var(--space-2); font-size: .85rem; color: var(--ink, #1c1c1e); cursor: pointer; min-height: 44px; }
.dq-select-all input { width: 18px; height: 18px; }
.dq-ready-hint { font-size: .78rem; font-weight: 600; color: var(--primary, #219653); background: rgba(33,150,83,.1); padding: 2px 8px; border-radius: 999px; }
.dq-btn-count { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; margin-left: 6px; border-radius: 999px; background: rgba(255,255,255,.25); font-size: .72rem; font-weight: 700; font-variant-numeric: tabular-nums; }

/* Severity / status badges (derived from existing bucket / record_type data) */
.dq-sev-badge, .dq-status-badge { display: inline-flex; align-items: center; justify-content: center; font-size: .68rem; font-weight: 700; letter-spacing: .02em; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.dq-sev-success { background: rgba(33,150,83,.12); color: var(--primary, #219653); }
.dq-sev-warning { background: rgba(255,159,10,.14); color: #C77700; }
.dq-sev-error { background: rgba(217,79,61,.12); color: var(--error, #D94F3D); }
.dq-sev-neutral { background: rgba(142,142,147,.14); color: var(--muted); }

.dq-evidence-more { display: inline-block; font-size: .72rem; font-weight: 600; color: var(--muted); cursor: help; }

/* Apply result status card */
.dq-apply-result { background: var(--bg-alt, #f3fbf5); border: .5px solid var(--primary, #219653); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm, 10px); color: var(--ink, #1c1c1e); display: grid; gap: var(--space-2); }
.dq-apply-result--warn { border-color: var(--warning, #e67e22); background: var(--warning-bg, rgba(230,126,34,.08)); }
.dq-apply-result-head { display: flex; align-items: center; gap: var(--space-2); }
.dq-apply-result-icon { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 999px; background: rgba(33,150,83,.14); color: var(--primary, #219653); font-size: .8rem; }
.dq-apply-result--warn .dq-apply-result-icon { background: rgba(230,126,34,.16); color: var(--warning, #e67e22); }
.dq-apply-result-head strong { font-size: .95rem; }
.dq-apply-result-stats { display: flex; gap: var(--space-4); font-size: .85rem; color: var(--muted); }
.dq-apply-result-stat b { color: var(--ink, #1c1c1e); font-variant-numeric: tabular-nums; }
.dq-apply-result-meta { display: flex; align-items: center; gap: var(--space-2); font-size: .8rem; color: var(--muted); flex-wrap: wrap; }
.dq-mono { font-family: var(--font-mono, ui-monospace, monospace); font-size: .76rem; word-break: break-all; }
.dq-copy-btn { font-size: .72rem; padding: 2px 8px; min-height: 28px; border: .5px solid var(--line); border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; }
.dq-copy-btn:hover { color: var(--primary, #219653); border-color: var(--primary, #219653); }
.dq-copy-btn:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.dq-table-wrap { margin-top: var(--space-3); }
.dq-table td { vertical-align: top; }
.dq-table td small { display: block; color: var(--muted); margin-top: 3px; }
.dq-table code { white-space: pre-wrap; word-break: break-word; font-size: .78rem; }
.dq-table a { display: block; color: var(--primary); font-weight: 600; word-break: break-word; }
.dq-empty-cell { padding: 0 !important; }
.admin-pagination span { display: inline-flex; align-items: center; color: var(--muted); font-size: .88rem; }
.dq-page-info { font-weight: 600; color: var(--ink, #1c1c1e); font-variant-numeric: tabular-nums; }
.dq-history { margin-top: var(--space-8); }
.dq-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-3); }
.dq-section-head h2 { margin: 0; font-size: 1.1rem; }
.dq-section-head p { margin: 4px 0 0; color: var(--muted); }
.dq-history-empty { padding: var(--space-4); border: .5px dashed var(--line); border-radius: var(--radius-sm); color: var(--muted); }
.dq-history-list { display: grid; gap: var(--space-3); }
.dq-history-card {
  padding: var(--space-4); border: .5px solid var(--line); border-radius: 14px;
  background: var(--card); box-shadow: var(--shadow-xs);
  transition: transform .25s cubic-bezier(.2,1,.4,1), box-shadow .25s, border-color .25s;
}
.dq-history-card:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.dq-history-card--apply { border-left: 3px solid var(--primary, #219653); }
.dq-history-card--rollback { border-left: 3px solid var(--warning, #e67e22); }
.dq-history-card-head { display: flex; justify-content: space-between; gap: var(--space-3); align-items: flex-start; }
.dq-history-card-head strong { display: block; word-break: break-word; margin-top: var(--space-1); }
.dq-status-badge { margin-bottom: 2px; }
.dq-history-card-head small, .dq-diff-item small, .dq-more { color: var(--muted); }
.dq-history-meta { margin: var(--space-2) 0; color: var(--muted); font-size: .86rem; word-break: break-word; }
.dq-diff-list { display: grid; gap: var(--space-2); margin-top: var(--space-3); }
.dq-diff-item { display: grid; grid-template-columns: minmax(160px, 240px) 1fr; gap: var(--space-3); align-items: start; padding: var(--space-2); background: var(--bg-alt, #f8faf9); border-radius: 8px; transition: background .15s; }
.dq-diff-item:hover { background: rgba(52,120,246,.04); }
.dq-diff-item code { white-space: pre-wrap; word-break: break-word; font-size: .76rem; }
.dq-skipped-list { display: grid; gap: var(--space-2); margin-top: var(--space-3); padding: var(--space-3); border: .5px solid var(--warning, #e67e22); border-radius: var(--radius-sm); background: var(--warning-bg, rgba(230, 126, 34, .08)); }
.dq-skipped-list > strong { font-size: .86rem; color: var(--warning, #e67e22); }
.dq-skipped-item { display: grid; gap: 2px; }
.dq-skipped-item .dq-skipped-entity { font-weight: 700; word-break: break-word; color: var(--primary, #219653); }
.dq-skipped-item small { color: var(--muted); word-break: break-word; }
.dq-skipped-reason { display: inline-block; font-size: .68rem; font-weight: 600; padding: 1px 6px; border-radius: 999px; }
.btn.danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }

@media (prefers-reduced-motion: reduce) {
  .dq-history-card:hover { transform: none; }
}

.dark .dq-history-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dq-diff-item { background: rgba(255,255,255,.03); }
.dark .dq-diff-item:hover { background: rgba(52,120,246,.08); }
.dark .dq-select-all { color: var(--ink, #e5e5e7); }
.dark .dq-apply-result { background: rgba(33,150,83,.1); color: var(--ink, #e5e5e7); }
.dark .dq-apply-result--warn { background: rgba(230,126,34,.12); }
.dark .dq-apply-result-stat b { color: var(--ink, #e5e5e7); }
.dark .dq-page-info { color: var(--ink, #e5e5e7); }
.dark .dq-sev-warning { color: #FFB340; }
.dark .dq-copy-btn { border-color: rgba(255,255,255,.12); }

@media (max-width: 780px) {
  .admin-page-head { flex-direction: column; }
  .dq-toolbar .input { flex: 1 1 150px; }
  .dq-section-head, .dq-history-card-head { flex-direction: column; }
  .dq-diff-item { grid-template-columns: 1fr; }
}
</style>
