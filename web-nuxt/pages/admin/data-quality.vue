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
        <div class="stat-icon si-blue">&#127760;</div>
        <div>
          <div class="stat-value">{{ summary.data?.public_entities || 0 }}</div>
          <div class="stat-label">Entity public</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon si-orange">&#128218;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_source || 0 }}</div>
          <div class="stat-label">Thiếu nguồn</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon si-orange">&#128205;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_location || 0 }}</div>
          <div class="stat-label">Thiếu tọa độ</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon si-orange">&#127963;</div>
        <div>
          <div class="stat-value">{{ summary.data?.missing_place_id_non_place || 0 }}</div>
          <div class="stat-label">Thiếu placeId</div>
        </div>
      </div>
      <div class="stat-card ok">
        <div class="stat-icon si-green">&#9989;</div>
        <div>
          <div class="stat-value">{{ summary.candidates?.auto_apply || 0 }}</div>
          <div class="stat-label">Có thể auto-apply</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-purple">&#128065;</div>
        <div>
          <div class="stat-value">{{ summary.candidates?.needs_review || 0 }}</div>
          <div class="stat-label">Cần duyệt</div>
        </div>
      </div>
    </div>

    <p v-if="summary?.cache?.exists" class="dq-cache-info">
      Queue cache: {{ summary.cache.modified_at || 'unknown' }}
    </p>

    <JourneyActionRail
      v-if="dataQualityQueueActions.length"
      :actions="dataQualityQueueActions"
      title="Ưu tiên quality queue"
      subtitle="Xử lý theo evidence, review load và lỗ hổng dữ liệu đang ảnh hưởng tới public trust."
      aria-label="Hành động ưu tiên trong quality queue"
      compact
    />

    <div class="dq-toolbar">
      <select v-model="kind" class="input" aria-label="Lọc theo loại" @change="applyFilters">
        <option value="">Tất cả loại</option>
        <option value="source">Nguồn</option>
        <option value="location">Tọa độ</option>
        <option value="placeid">PlaceId</option>
        <option value="accuracy">Accuracy</option>
        <option value="relationship">Relationship</option>
      </select>
      <select v-model="bucket" class="input" aria-label="Lọc theo trạng thái" @change="applyFilters">
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

    <div v-if="loading && !candidates.length" class="dq-skeleton" role="status" aria-label="Đang tải danh sách candidate">
      <div v-for="i in 6" :key="i" class="dq-skel-row"><div class="skel skel-check"></div><div class="skel skel-sev"></div><div class="skel skel-entity"></div><div class="skel skel-field"></div><div class="skel skel-value"></div></div>
    </div>
    <div class="admin-table-wrap dq-table-wrap">
      <table class="admin-table dq-table" aria-label="Chất lượng dữ liệu">
        <thead>
          <tr>
            <th scope="col" class="dq-th-checkbox"></th>
            <th scope="col" class="dq-th-sev">Mức<span class="admin-help" data-tip="Auto (xanh) = apply tự động. Duyệt (cam) = cần kiểm tra. Loại (đỏ) = bỏ qua." tabindex="0" role="img" aria-label="Giải thích mức">?</span></th>
            <th scope="col">Entity</th>
            <th scope="col">Field</th>
            <th scope="col">Đề xuất</th>
            <th scope="col">Evidence</th>
            <th scope="col">Lý do</th>
            <th scope="col">Quyết định</th>
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
                :href="url.startsWith('http') ? url : '#'"
                :title="url"
                target="_blank"
                rel="noopener noreferrer"
              >{{ host(url) }}</a>
              <span v-if="(c.evidence_urls || []).length > 2" class="dq-evidence-more" :title="(c.evidence_urls || []).slice(2).map((u: string) => host(u)).join(', ')">+{{ (c.evidence_urls || []).length - 2 }} nữa</span>
              <span v-if="!(c.evidence_urls || []).length">—</span>
            </td>
            <td>{{ c.reason || c.status || '—' }}</td>
            <td class="dq-actions-cell">
              <span v-if="c.decision" class="dq-decision-badge" :class="`dq-decision-${c.decision}`">{{ decisionLabel(c.decision) }}</span>
              <div v-if="c.bucket !== 'auto_apply'" class="dq-row-actions">
                <button type="button" class="btn btn-success btn-sm" :disabled="decisionBusy === c.candidate_id" @click="decideCandidate(c, 'approve')">Duyệt & apply</button>
                <button type="button" class="btn btn-outline btn-sm" :disabled="decisionBusy === c.candidate_id" @click="decideCandidate(c, 'defer')">Hoãn</button>
                <button type="button" class="btn btn-danger btn-sm" :disabled="decisionBusy === c.candidate_id" @click="decideCandidate(c, 'reject')">Loại</button>
              </div>
            </td>
          </tr>
          <tr v-if="!loading && !candidates.length">
            <td colspan="8" class="dq-empty-cell">
              <div class="admin-empty-state">
                <div class="admin-empty-state-icon">{{ hasActiveFilters ? '🔍' : '✓' }}</div>
                <div class="admin-empty-state-text">{{ hasActiveFilters ? 'Không có vấn đề' : 'Chất lượng dữ liệu tốt' }}</div>
                <div class="admin-empty-state-hint">{{ hasActiveFilters ? 'Dữ liệu hiện tại đáp ứng tiêu chí lọc.' : 'Không còn candidate nào chờ kiểm duyệt.' }}</div>
              </div>
            </td>
          </tr>
          <tr v-if="loading">
            <td colspan="8" class="admin-empty-row">Đang tải dữ liệu…</td>
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
      <div v-if="decisionHistory.length" class="dq-decision-history">
        <div class="dq-subsection-head">
          <h3>Quyết định review gần đây</h3>
          <small>{{ decisionHistory.length }} quyết định mới nhất</small>
        </div>
        <article v-for="d in decisionHistory" :key="d.batch_id" class="dq-decision-card">
          <div class="dq-decision-card-head">
            <span class="dq-decision-badge" :class="`dq-decision-${d.decision}`">{{ decisionLabel(d.decision) }}</span>
            <strong>{{ (d.candidate_ids || []).length }} candidate</strong>
            <time v-if="d.decided_at" :datetime="d.decided_at">{{ d.decided_at }}</time>
          </div>
          <p class="dq-decision-meta">
            <span v-if="d.apply">Đã apply sau khi duyệt</span>
            <span v-if="d.reviewer">Reviewer: {{ d.reviewer }}</span>
            <span v-if="(d.missing_candidate_ids || []).length">Thiếu: {{ (d.missing_candidate_ids || []).length }}</span>
          </p>
          <p v-if="d.note" class="dq-decision-note">{{ d.note }}</p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useJourneyActions } from '~/composables/useJourneyActions'

interface DataQualitySummary {
  data?: {
    public_entities?: number
    missing_source?: number
    missing_location?: number
    missing_place_id_non_place?: number
  }
  candidates?: {
    auto_apply?: number
    needs_review?: number
    reject?: number
  }
  cache?: {
    exists?: boolean
    modified_at?: string
  }
}

interface DataQualityCandidate {
  candidate_id: string
  entity_id: string
  bucket: string
  decision?: 'approve' | 'reject' | 'defer' | string
  decision_note?: string
  decision_at?: string
  field: string
  suggested_value?: unknown
  evidence_urls?: string[]
  reason?: string
  status?: string
}

interface DataQualityApplyResult {
  dry_run?: boolean
  applied_count?: number
  skipped_count?: number
  batch_id?: string
  backup?: string
}

interface DataQualityChange {
  candidate_id: string
  entity_id?: string
  entity_name?: string
  field?: string
  before?: unknown
  after?: unknown
}

interface DataQualitySkipped {
  candidate_id: string
  entity_id?: string
  field?: string
  reason?: string
  duplicate_of?: string
}

interface DataQualityHistoryRecord {
  batch_id: string
  record_type: 'apply' | 'rollback' | string
  applied_at?: string
  rolled_back_at?: string
  applied_count?: number
  restored_changes?: number
  skipped_count?: number
  backup?: string
  restored_from?: string
  changes?: DataQualityChange[]
  skipped?: DataQualitySkipped[]
}

interface DataQualityDecisionRecord {
  batch_id: string
  decision: string
  decided_at?: string
  reviewer?: string
  note?: string
  apply?: boolean
  candidate_ids?: string[]
  missing_candidate_ids?: string[]
}

interface DataQualityReviewResponse {
  candidates?: DataQualityCandidate[]
  total?: number
}

interface DataQualityHistoryResponse {
  history?: DataQualityHistoryRecord[]
  decisions?: DataQualityDecisionRecord[]
}

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Chất lượng dữ liệu — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()
const route = useRoute()
const router = useRouter()
const { dataQualityQueueActions: buildDataQualityQueueActions } = useJourneyActions()

const summary = ref<DataQualitySummary | null>(null)
const candidates = ref<DataQualityCandidate[]>([])
const selectedIds = ref<string[]>([])
const applyResult = ref<DataQualityApplyResult | null>(null)
const kind = ref(queryValue(route.query.kind))
const bucket = ref(normalizeBucketQuery(route.query.bucket, 'needs_review'))
const total = ref(0)
const offset = ref(0)
const limit = 100
const loading = ref(false)
const applying = ref(false)
const decisionBusy = ref('')
const history = ref<DataQualityHistoryRecord[]>([])
const decisionHistory = ref<DataQualityDecisionRecord[]>([])
const historyLoading = ref(false)
const rollingBack = ref('')

const copiedBatch = ref(false)

const autoApplySet = computed(() => new Set(candidates.value.filter(c => c.bucket === 'auto_apply').map(c => c.candidate_id)))
const autoApplyIds = computed(() => selectedIds.value.filter(id => autoApplySet.value.has(id)))
const hasActiveFilters = computed(() => !!kind.value || !!bucket.value)
const pageAutoApplyIds = computed(() => candidates.value.filter((c) => c.bucket === 'auto_apply').map((c) => c.candidate_id))
const allPageAutoSelected = computed(() => pageAutoApplyIds.value.length > 0 && pageAutoApplyIds.value.every((id) => selectedIds.value.includes(id)))
const dataQualityQueueActions = computed(() => buildDataQualityQueueActions({
  autoApply: summary.value?.candidates?.auto_apply ?? 0,
  needsReview: summary.value?.candidates?.needs_review ?? 0,
  reject: summary.value?.candidates?.reject ?? 0,
  missingSource: summary.value?.data?.missing_source ?? 0,
  missingLocation: summary.value?.data?.missing_location ?? 0,
  missingPlaceId: summary.value?.data?.missing_place_id_non_place ?? 0,
  selectedAuto: autoApplyIds.value.length,
  bucket: bucket.value,
}))

function queryValue(value: unknown) {
  const v = Array.isArray(value) ? value[0] : value
  return typeof v === 'string' ? v : ''
}

function normalizeBucketQuery(value: unknown, fallback = '') {
  const v = queryValue(value)
  if (v === 'all') return ''
  return v || fallback
}

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

function decisionLabel(d?: string) {
  if (d === 'approve') return 'Đã duyệt'
  if (d === 'reject') return 'Đã loại'
  if (d === 'defer') return 'Đã hoãn'
  return d || ''
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

function applyFilters() {
  const query = { ...route.query, kind: kind.value || undefined, bucket: bucket.value || 'all' }
  router.replace({ query }).catch(() => {})
  fetchCandidates(true)
}

watch(() => [route.query.kind, route.query.bucket], ([kindQuery, bucketQuery]) => {
  const nextKind = queryValue(kindQuery)
  const nextBucket = normalizeBucketQuery(bucketQuery, 'needs_review')
  if (nextKind === kind.value && nextBucket === bucket.value) return
  kind.value = nextKind
  bucket.value = nextBucket
  fetchCandidates(true)
})

async function fetchSummary(refresh = false) {
  try {
    summary.value = await $fetch<DataQualitySummary>('/admin-api/data-quality/summary', {
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
    const res = await $fetch<DataQualityReviewResponse>('/admin-api/data-quality/review', {
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
    showToast(getErrorDetail(e, 'Không thể tải review queue'), 'error')
  }
  loading.value = false
}

async function refreshAll(refresh = false) {
  try {
    await Promise.all([fetchSummary(refresh), fetchCandidates(false, refresh), fetchHistory()])
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Không thể làm mới dữ liệu'), 'error')
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await $fetch<DataQualityHistoryResponse>('/admin-api/data-quality/history', {
      headers: authHeaders(),
      query: { limit: 20 },
    })
    history.value = res.history || []
    decisionHistory.value = res.decisions || []
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Không thể tải lịch sử apply'), 'error')
  }
  historyLoading.value = false
}

async function runApply(dryRun: boolean) {
  if (!autoApplyIds.value.length || applying.value) return
  applying.value = true
  try {
    applyResult.value = await $fetch<DataQualityApplyResult>('/admin-api/data-quality/apply', {
      method: 'POST',
      headers: authHeaders(),
      body: { candidate_ids: autoApplyIds.value, dry_run: dryRun },
    })
    showToast(dryRun ? 'Dry-run hoàn tất' : 'Đã apply candidate được chọn', 'success')
    if (!dryRun) await refreshAll(true)
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Không thể apply candidate'), 'error')
  } finally {
    applying.value = false
  }
}

async function dryRunSelected() {
  await runApply(true)
}

function applyFieldBreakdown() {
  const byId = new Map(candidates.value.map(c => [c.candidate_id, c]))
  const counts: Record<string, number> = {}
  for (const id of autoApplyIds.value) {
    const f = byId.get(id)?.field || 'khác'
    counts[f] = (counts[f] || 0) + 1
  }
  return Object.entries(counts).map(([f, n]) => `  • ${f}: ${n}`).join('\n')
}

async function applySelected() {
  const n = autoApplyIds.value.length
  if (!n) return
  const msg = [
    `Áp dụng ${n} candidate evidence-only vào dữ liệu hệ thống.`,
    '',
    'Theo field:',
    applyFieldBreakdown(),
    '',
    'Hệ thống sẽ ghi snapshot theo batch để có thể rollback từ lịch sử apply nếu cần.',
    '',
    `Xác nhận apply ${n} candidate?`,
  ].join('\n')
  if (!await confirmDialog(msg, { danger: true })) return
  await runApply(false)
}

async function decideCandidate(c: DataQualityCandidate, decision: 'approve' | 'reject' | 'defer') {
  if (decisionBusy.value) return
  const labels = { approve: 'duyệt và apply', reject: 'loại', defer: 'hoãn' }
  const danger = decision === 'approve' || decision === 'reject'
  const msg = decision === 'approve'
    ? `Duyệt và apply candidate ${c.candidate_id} vào dữ liệu hệ thống?`
    : `Xác nhận ${labels[decision]} candidate ${c.candidate_id}?`
  if (!await confirmDialog(msg, { danger })) return
  decisionBusy.value = c.candidate_id
  try {
    const res = await $fetch<{ apply_result?: DataQualityApplyResult }>('/admin-api/data-quality/decision', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        candidate_ids: [c.candidate_id],
        decision,
        apply: decision === 'approve',
      },
    })
    c.decision = decision
    if (res.apply_result) applyResult.value = res.apply_result
    if (decision === 'approve' && Number(res.apply_result?.applied_count || 0) > 0) {
      candidates.value = candidates.value.filter((item) => item.candidate_id !== c.candidate_id)
      selectedIds.value = selectedIds.value.filter((id) => id !== c.candidate_id)
      total.value = Math.max(0, total.value - 1)
    }
    showToast(decision === 'approve' ? 'Đã duyệt và apply candidate' : `Đã ${labels[decision]} candidate`, 'success')
    await Promise.all([fetchSummary(decision === 'approve'), fetchHistory()])
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Không thể ghi quyết định'), 'error')
  } finally {
    decisionBusy.value = ''
  }
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
    showToast(getErrorDetail(e, 'Không thể rollback batch'), 'error')
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
.dq-stats .stat-card.warn .stat-value { color: var(--warning, #e67e22); }
.dq-stats .stat-card.ok .stat-value { color: var(--primary); }
.dq-th-checkbox { width: 42px; }
.dq-th-sev { width: 64px; }
.dq-cache-info { margin: var(--space-3) 0 0; color: var(--muted); font-size: .88rem; }
.dq-toolbar { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; margin: var(--space-4) 0; }
.dq-toolbar .input { flex: 0 0 170px; }
.dq-select-all { display: inline-flex; align-items: center; gap: var(--space-2); font-size: .85rem; color: var(--ink, #1c1c1e); cursor: pointer; min-height: 44px; }
.dq-select-all input { width: 18px; height: 18px; }
.dq-ready-hint { font-size: .78rem; font-weight: 600; color: var(--primary); background: rgba(var(--primary-rgb),.1); padding: 2px 8px; border-radius: 999px; }
.dq-btn-count { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; margin-left: 6px; border-radius: 999px; background: rgba(255,255,255,.25); font-size: .72rem; font-weight: 700; font-variant-numeric: tabular-nums; }

/* Severity / status badges (derived from existing bucket / record_type data) */
.dq-sev-badge, .dq-status-badge { display: inline-flex; align-items: center; justify-content: center; font-size: .68rem; font-weight: 700; letter-spacing: .02em; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.dq-sev-success { background: rgba(var(--primary-rgb),.12); color: var(--primary); }
.dq-sev-warning { background: rgba(var(--warning-rgb),.14); color: var(--warning); }
.dq-sev-error { background: rgba(var(--danger-rgb),.12); color: var(--error, #D94F3D); }
.dq-sev-neutral { background: rgba(142,142,147,.14); color: var(--muted); }

.dq-evidence-more { display: inline-block; font-size: .72rem; font-weight: 600; color: var(--muted); cursor: help; }
.dq-actions-cell { min-width: 180px; }
.dq-row-actions {
  display: flex; flex-wrap: wrap; gap: var(--space-1);
  align-items: center; margin-top: var(--space-1);
}
.dq-row-actions .btn { min-height: 32px; padding: 5px 8px; font-size: .72rem; line-height: 1.2; }
.dq-decision-badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 2px 8px; border-radius: 999px; font-size: .68rem;
  font-weight: 700; white-space: nowrap; border: .5px solid transparent;
}
.dq-decision-approve { background: rgba(var(--primary-rgb),.12); color: var(--primary); border-color: rgba(var(--primary-rgb),.24); }
.dq-decision-reject { background: rgba(var(--danger-rgb),.1); color: var(--error, #D94F3D); border-color: rgba(var(--danger-rgb),.22); }
.dq-decision-defer { background: rgba(var(--warning-rgb),.13); color: var(--warning, #e67e22); border-color: rgba(var(--warning-rgb),.24); }

/* Apply result status card */
.dq-apply-result { background: var(--bg-alt, #f3fbf5); border: .5px solid var(--primary); padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm, 10px); color: var(--ink, #1c1c1e); display: grid; gap: var(--space-2); }
.dq-apply-result--warn { border-color: var(--warning, #e67e22); background: var(--warning-bg, rgba(230,126,34,.08)); }
.dq-apply-result-head { display: flex; align-items: center; gap: var(--space-2); }
.dq-apply-result-icon { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 999px; background: rgba(var(--primary-rgb),.14); color: var(--primary); font-size: .8rem; }
.dq-apply-result--warn .dq-apply-result-icon { background: rgba(var(--warning-rgb),.16); color: var(--warning, #e67e22); }
.dq-apply-result-head strong { font-size: .95rem; }
.dq-apply-result-stats { display: flex; gap: var(--space-4); font-size: .85rem; color: var(--muted); }
.dq-apply-result-stat b { color: var(--ink, #1c1c1e); font-variant-numeric: tabular-nums; }
.dq-apply-result-meta { display: flex; align-items: center; gap: var(--space-2); font-size: .8rem; color: var(--muted); flex-wrap: wrap; }
.dq-mono { font-family: var(--font-mono, ui-monospace, monospace); font-size: .76rem; word-break: break-all; }
.dq-copy-btn { font-size: .72rem; padding: 2px 8px; min-height: 44px; border: .5px solid var(--line); border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; }
.dq-copy-btn:hover { color: var(--primary); border-color: var(--primary); }
.dq-copy-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
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
.dq-section-head p { margin: var(--space-1) 0 0; color: var(--muted); }
.dq-history-empty { padding: var(--space-4); border: .5px dashed var(--line); border-radius: var(--radius-sm); color: var(--muted); }
.dq-history-list { display: grid; gap: var(--space-3); }
.dq-decision-history { display: grid; gap: var(--space-2); margin-top: var(--space-5); }
.dq-subsection-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); }
.dq-subsection-head h3 { margin: 0; font-size: .95rem; }
.dq-subsection-head small { color: var(--muted); }
.dq-decision-card { padding: var(--space-3); border: .5px solid var(--line); border-radius: 10px; background: var(--bg-alt, #f8faf9); }
.dq-decision-card-head { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.dq-decision-card-head strong { font-size: .84rem; color: var(--ink); }
.dq-decision-card-head time { margin-left: auto; color: var(--muted); font-size: .75rem; }
.dq-decision-meta { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: var(--space-2) 0 0; color: var(--muted); font-size: .78rem; }
.dq-decision-note { margin: var(--space-2) 0 0; color: var(--ink); font-size: .82rem; line-height: 1.45; }
.dq-history-card {
  padding: var(--space-4); border: .5px solid var(--line); border-radius: 14px;
  background: var(--card); box-shadow: var(--shadow-xs);
  transition: transform .25s var(--ease-soft), box-shadow .25s, border-color .25s;
}
.dq-history-card:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.dq-history-card--apply { border-left: 3px solid var(--primary); }
.dq-history-card--rollback { border-left: 3px solid var(--warning, #e67e22); }
.dq-history-card-head { display: flex; justify-content: space-between; gap: var(--space-3); align-items: flex-start; }
.dq-history-card-head strong { display: block; word-break: break-word; margin-top: var(--space-1); }
.dq-status-badge { margin-bottom: 2px; }
.dq-history-card-head small, .dq-diff-item small, .dq-more { color: var(--muted); }
.dq-history-meta { margin: var(--space-2) 0; color: var(--muted); font-size: .86rem; word-break: break-word; }
.dq-diff-list { display: grid; gap: var(--space-2); margin-top: var(--space-3); }
.dq-diff-item { display: grid; grid-template-columns: minmax(160px, 240px) 1fr; gap: var(--space-3); align-items: start; padding: var(--space-2); background: var(--bg-alt, #f8faf9); border-radius: 8px; transition: background .15s; }
.dq-diff-item:hover { background: rgba(var(--blue-rgb),.04); }
.dq-diff-item code { white-space: pre-wrap; word-break: break-word; font-size: .76rem; }
.dq-skipped-list { display: grid; gap: var(--space-2); margin-top: var(--space-3); padding: var(--space-3); border: .5px solid var(--warning, #e67e22); border-radius: var(--radius-sm); background: var(--warning-bg, rgba(230, 126, 34, .08)); }
.dq-skipped-list > strong { font-size: .86rem; color: var(--warning, #e67e22); }
.dq-skipped-item { display: grid; gap: 2px; }
.dq-skipped-item .dq-skipped-entity { font-weight: 700; word-break: break-word; color: var(--primary); }
.dq-skipped-item small { color: var(--muted); word-break: break-word; }
.dq-skipped-reason { display: inline-block; font-size: .68rem; font-weight: 600; padding: 1px 6px; border-radius: 999px; }
.btn.danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }

@media (prefers-reduced-motion: reduce) {
  .dq-history-card:hover { transform: none; }
}

.dark .dq-history-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dq-diff-item { background: rgba(255,255,255,.03); }
.dark .dq-diff-item:hover { background: rgba(var(--blue-rgb),.08); }
.dark .dq-decision-card { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.08); }
.dark .dq-select-all { color: var(--ink, #e5e5e7); }
.dark .dq-apply-result { background: rgba(var(--primary-rgb),.1); color: var(--ink, #e5e5e7); }
.dark .dq-apply-result--warn { background: rgba(var(--warning-rgb),.12); }
.dark .dq-apply-result-stat b { color: var(--ink, #e5e5e7); }
.dark .dq-page-info { color: var(--ink, #e5e5e7); }
.dark .dq-sev-warning { color: var(--accent-text); }
.dark .dq-copy-btn { border-color: rgba(255,255,255,.12); }

@media (max-width: 780px) {
  .admin-page-head { flex-direction: column; }
  .dq-toolbar .input { flex: 1 1 150px; }
  .dq-section-head, .dq-history-card-head { flex-direction: column; }
  .dq-decision-card-head time { margin-left: 0; width: 100%; }
  .dq-diff-item { grid-template-columns: 1fr; }
}

/* ── Skeleton loading ── */
.dq-skeleton { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-4) 0; }
.dq-skel-row { display: flex; gap: var(--space-3); padding: var(--space-2) 0; }
.dq-skeleton .skel { height: 14px; border-radius: 6px; background: var(--line, #e5e5ea); animation: dqSkelPulse 1.2s ease-in-out infinite; }
.skel-check { width: 18px; }
.skel-sev { width: 50px; }
.skel-entity { width: 120px; }
.skel-field { width: 70px; }
.skel-value { flex: 1; max-width: 200px; }
@keyframes dqSkelPulse { 0%, 100% { opacity: .4; } 50% { opacity: 1; } }
</style>
