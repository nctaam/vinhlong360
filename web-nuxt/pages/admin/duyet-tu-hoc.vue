<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Duyệt tự học & Tiện ích</h1>
        <p class="dth-subtitle">Duyệt entity provisional và công cụ dữ liệu</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="loadProvisional()"><span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới</button>
    </div>

    <!-- 1) Provisional review -->
    <div class="dth-section">
      <div class="dth-section-head">
        <h2 class="admin-section-title">Entity tự học chờ duyệt</h2>
        <span v-if="provisional.length" class="dth-count-badge dth-count-warn" role="status" :aria-label="`${provisional.length} entity chờ duyệt`">{{ provisional.length }}</span>
      </div>

      <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải danh sách tự học"><div class="spinner"></div></div>
      <div v-else-if="loadError" class="admin-empty">
        <p>Không tải được danh sách entity tự học.</p>
        <button type="button" class="btn btn-secondary" @click="loadProvisional()">Thử lại</button>
      </div>
      <template v-else>
        <div v-if="!provisional.length" class="dth-empty">
          <span class="dth-empty-icon">&#9989;</span>
          <p>Tất cả entity tự học đã được duyệt.</p>
          <small class="admin-muted">Quay lại kiểm tra sau, hoặc tải nguồn dữ liệu để xem thống kê.</small>
        </div>
        <div v-else class="dth-review-list" aria-label="Entity tự học chờ duyệt">
          <article
            v-for="{ review: e, imageRows, placeholder } in provisionalRows"
            :key="e.id"
            class="dth-review-card"
            :aria-labelledby="`review-title-${e.id}`"
            :aria-busy="acting === e.id"
          >
            <header class="dth-review-head">
              <div>
                <h3 :id="`review-title-${e.id}`">{{ e.entity.name || e.id }}</h3>
                <code>{{ e.id }}</code>
              </div>
              <div class="dth-review-badges">
                <span v-if="e.entity.type" class="dth-type-badge">{{ e.entity.type }}</span>
                <span
                  v-if="typeof e.entity.confidence === 'number'"
                  class="dth-conf-badge"
                  :class="e.entity.confidence >= 0.7 ? 'dth-conf-high' : 'dth-conf-low'"
                >{{ Math.round(e.entity.confidence * 100) }}%</span>
              </div>
            </header>

            <section v-if="e.entity.summary" class="dth-review-section" aria-label="Tóm tắt đầy đủ">
              <h4>Tóm tắt</h4>
              <p class="dth-summary">{{ e.entity.summary }}</p>
            </section>

            <dl class="dth-field-grid">
              <div>
                <dt>Địa chỉ</dt>
                <dd>{{ e.entity.address || '—' }}</dd>
              </div>
              <div>
                <dt>Khu vực</dt>
                <dd>{{ e.entity.area || '—' }}</dd>
              </div>
              <div>
                <dt>Place ID</dt>
                <dd>{{ e.entity.placeId || '—' }}</dd>
              </div>
              <div>
                <dt>Thời điểm học</dt>
                <dd>{{ e.entity.learned_at || '—' }}</dd>
              </div>
            </dl>

            <div class="dth-inspection-grid">
              <section class="dth-review-section">
                <h4>Nguồn</h4>
                <pre>{{ formatInspectable(e.entity.source) }}</pre>
              </section>
              <section class="dth-review-section">
                <h4>Tọa độ</h4>
                <pre>{{ formatInspectable(coordinateValue(e.entity)) }}</pre>
              </section>
              <section class="dth-review-section">
                <h4>Thuộc tính</h4>
                <pre>{{ formatInspectable(e.entity.attributes) }}</pre>
              </section>
            </div>

            <section class="dth-review-section" data-self-learning-inspector>
              <h4>Hình ảnh</h4>
              <ul v-if="imageRows.length" class="dth-image-list">
                <li v-for="row in imageRows" :key="`${e.id}-image-${row.index}`" data-provisional-image-row>
                  <template v-if="row.descriptor?.url">
                    <a
                      :href="row.descriptor.url"
                      :aria-describedby="provisionalDisclosureId(e.id, row.index)"
                      target="_blank"
                      rel="noopener noreferrer"
                      data-provisional-image-link
                    >{{ row.descriptor.url }}</a>
                    <ImageDisclosure
                      :id="provisionalDisclosureId(e.id, row.index)"
                      :descriptor="row.descriptor"
                      presentation="full"
                    />
                  </template>
                  <pre v-else>{{ formatInspectable(row.raw) }}</pre>
                </li>
              </ul>
              <span v-else class="dth-image-placeholder">
                <span class="admin-muted">—</span>
                <ImageDisclosure :descriptor="placeholder" presentation="full" />
              </span>
            </section>

            <details class="dth-snapshot" @toggle="onSnapshotToggle(e.id, $event)">
              <summary>Toàn bộ snapshot đã xem xét</summary>
              <pre v-if="expandedSnapshots.has(e.id)">{{ JSON.stringify(e.entity, null, 2) }}</pre>
            </details>

            <footer class="dth-review-actions">
              <button type="button" class="btn-success" :disabled="acting === e.id" @click="approve(e)">
                {{ acting === e.id ? '...' : 'Duyệt' }}
              </button>
              <button type="button" class="btn-danger" :disabled="acting === e.id" @click="reject(e)">Từ chối</button>
            </footer>
          </article>
        </div>
      </template>
    </div>

    <!-- 2) Tiện ích -->
    <div class="dth-section">
      <h2 class="admin-section-title">Tiện ích dữ liệu</h2>
      <div class="dth-tools-grid">
        <button type="button" class="dth-tool-card" :disabled="exporting" @click="exportJson">
          <span v-if="exporting" class="dth-tool-spinner" aria-hidden="true"></span>
          <span v-else class="dth-tool-icon">&#128230;</span>
          <span class="dth-tool-label">{{ exporting ? 'Đang xuất...' : 'Export JSON (DB)' }}</span>
          <small>Tải data.json từ DB</small>
        </button>
        <button type="button" class="dth-tool-card" :disabled="loadingSources" @click="loadSources">
          <span v-if="loadingSources" class="dth-tool-spinner" aria-hidden="true"></span>
          <span v-else class="dth-tool-icon">&#128218;</span>
          <span class="dth-tool-label">{{ loadingSources ? 'Đang tải...' : 'Xem nguồn dữ liệu' }}</span>
          <small>Thống kê theo nguồn</small>
        </button>
      </div>

      <div v-if="sources.length" class="dth-sources">
        <div class="admin-table-wrap">
          <table class="admin-table" aria-label="Nguồn dữ liệu tự học">
            <thead><tr><th scope="col">Nguồn</th><th scope="col">Số entity</th><th scope="col">URL mẫu</th></tr></thead>
            <tbody>
              <tr v-for="s in sources" :key="s.title">
                <td><strong>{{ s.title }}</strong></td>
                <td><span class="dth-source-count" :aria-label="`${s.count} entity`">{{ s.count }}</span></td>
                <td class="admin-td-muted"><small>{{ s.sample_url || '—' }}</small></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ImageDescriptor } from '~/types/image'
import { describeEntityImages, describeEntityPlaceholder, normalizeEntityEditorialUpload } from '~/utils/imageDescriptors'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Duyệt tự học — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

interface DataSourceSummary {
  title: string
  count: number
  sample_url?: string
}

interface ProvisionalEntitySnapshot extends Record<string, unknown> {
  id: string
  name?: string
  type?: string
  summary?: string
  confidence?: number
  source?: unknown
  coordinates?: unknown
  coords?: unknown
  images?: unknown
  attributes?: unknown
  address?: string
  area?: string
  placeId?: string
  learned_at?: string
}

interface ProvisionalReview {
  id: string
  review_token: string
  entity: ProvisionalEntitySnapshot
}

interface ProvisionalListResponse {
  provisional?: ProvisionalReview[]
}

const provisional = ref<ProvisionalReview[]>([])
const sources = ref<DataSourceSummary[]>([])
const exporting = ref(false)
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const loadingSources = ref(false)
const expandedSnapshots = ref(new Set<string>())
const provisionalRows = computed(() => provisional.value.map(review => ({
  review,
  imageRows: provisionalImageRows(review.entity),
  placeholder: describeEntityPlaceholder(review.entity),
})))

async function loadProvisional(preserveCurrent = false) {
  if (!preserveCurrent) {
    loading.value = true
    loadError.value = false
  }
  try {
    const r = await $fetch<ProvisionalListResponse>('/admin-api/provisional', { headers: authHeaders() })
    provisional.value = r.provisional || []
  } catch {
    if (!preserveCurrent) loadError.value = true
    showToast('Không thể tải danh sách entity tự học', 'error')
  } finally {
    if (!preserveCurrent) loading.value = false
  }
}
async function approve(e: ProvisionalReview) {
  const name = e.entity.name || e.id
  if (!await confirmDialog(`Duyệt "${name}" vào hệ thống?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/approve`, {
      method: 'POST',
      headers: authHeaders(),
      body: { review_token: e.review_token },
    })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast(`Đã duyệt ${name}`, 'success')
  } catch (err: unknown) {
    if (getStatusCode(err) === 409 && getErrorDetail(err) === 'stale_review') {
      showToast('Dữ liệu đã thay đổi. Vui lòng xem lại snapshot mới trước khi duyệt.', 'error')
      await loadProvisional(true)
    } else {
      showToast(getErrorDetail(err, 'Duyệt lỗi'), 'error')
    }
  } finally {
    acting.value = null
  }
}
async function reject(e: ProvisionalReview) {
  const name = e.entity.name || e.id
  if (!await confirmDialog(`Từ chối + xóa "${name}"?`, { danger: true })) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/reject`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast('Đã từ chối', 'success')
  } catch (err: unknown) { showToast(getErrorDetail(err, 'Từ chối lỗi'), 'error') }
  acting.value = null
}

function formatInspectable(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function coordinateValue(entity: ProvisionalEntitySnapshot): unknown {
  return entity.coordinates ?? entity.coords
}

function imageValues(value: unknown): unknown[] {
  if (value === null || value === undefined) return []
  return Array.isArray(value) ? value : [value]
}

function provisionalImageDescriptor(entity: ProvisionalEntitySnapshot, value: unknown): Readonly<ImageDescriptor> | null {
  const described = value && typeof value === 'object' && !Array.isArray(value)
    ? describeEntityImages({ ...entity, image_descriptor: value })[0]
    : describeEntityImages({ ...entity, images: [value] })[0]
  if (!described) return null
  try {
    return normalizeEntityEditorialUpload(described)
  } catch {
    return null
  }
}

function provisionalImageRows(entity: ProvisionalEntitySnapshot) {
  return imageValues(entity.images).map((raw, index) => ({
    raw,
    index,
    descriptor: provisionalImageDescriptor(entity, raw),
  }))
}

function provisionalDisclosureId(entityId: string, index: number): string {
  const token = entityId.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'entity'
  return `admin-provisional-${token}-${index}-disclosure`
}

function onSnapshotToggle(entityId: string, event: Event) {
  const next = new Set(expandedSnapshots.value)
  if ((event.currentTarget as HTMLDetailsElement).open) next.add(entityId)
  else next.delete(entityId)
  expandedSnapshots.value = next
}

async function loadSources() {
  loadingSources.value = true
  try {
    const r = await $fetch<{ sources?: Record<string, Omit<DataSourceSummary, 'title'>> }>('/admin-api/sources', { headers: authHeaders() })
    sources.value = Object.entries(r.sources || {})
      .map(([title, v]) => ({ title, count: Number(v.count) || 0, sample_url: v.sample_url }))
      .sort((a, b) => b.count - a.count)
  } catch { showToast('Tải nguồn lỗi', 'error') }
  loadingSources.value = false
}

async function exportJson() {
  exporting.value = true
  try {
    const data = await $fetch<Record<string, unknown>>('/admin-api/export', { method: 'POST', headers: authHeaders() })
    downloadBlob(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }), `vinhlong360-export-${new Date().toISOString().slice(0, 10)}.json`)
  } catch { showToast('Export lỗi', 'error') }
  exporting.value = false
}

onMounted(loadProvisional)
</script>

<style scoped>
.dth-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

.dth-section { margin-bottom: var(--space-6); }
.dth-section-head {
  display: flex; align-items: center; gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.dth-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 8px;
  border-radius: 100px; font-size: .72rem; font-weight: 700;
}
.dth-count-warn { background: rgba(var(--warning-rgb),.1); color: var(--warning); }

.dth-review-list { display: grid; gap: var(--space-4); }
.dth-review-card {
  padding: var(--space-4); border: .5px solid var(--line); border-radius: 14px;
  background: var(--bg); box-shadow: 0 2px 10px rgba(var(--black-rgb),.03);
}
.dth-review-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: var(--space-3); padding-bottom: var(--space-3); border-bottom: .5px solid var(--line);
}
.dth-review-head h3 { margin: 0 0 3px; font-size: 1rem; color: var(--ink); }
.dth-review-head code { font-size: .72rem; color: var(--muted); overflow-wrap: anywhere; }
.dth-review-badges { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); }
.dth-summary { margin: 0; color: var(--ink); font-size: .86rem; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
.dth-review-section { min-width: 0; margin-top: var(--space-3); }
.dth-review-section h4 { margin: 0 0 var(--space-2); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.dth-review-section pre,
.dth-snapshot pre,
.dth-image-list pre {
  margin: 0; padding: var(--space-3); border-radius: 10px;
  background: rgba(var(--gray-rgb),.06); color: var(--ink);
  font: .75rem/1.55 ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: pre-wrap; overflow-wrap: anywhere;
}
.dth-field-grid,
.dth-inspection-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); }
.dth-field-grid { margin: var(--space-3) 0 0; }
.dth-field-grid > div { min-width: 0; padding: var(--space-3); border-radius: 10px; background: rgba(var(--gray-rgb),.04); }
.dth-field-grid dt { font-size: .7rem; font-weight: 700; text-transform: uppercase; color: var(--muted); }
.dth-field-grid dd { margin: 4px 0 0; font-size: .82rem; color: var(--ink); overflow-wrap: anywhere; }
.dth-image-list { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }
.dth-image-list li { display: grid; gap: var(--space-1); }
.dth-image-list a { color: var(--primary); font-size: .78rem; overflow-wrap: anywhere; }
.dth-image-placeholder { display: grid; gap: var(--space-1); }
.dth-snapshot { margin-top: var(--space-4); border-top: .5px solid var(--line); padding-top: var(--space-3); }
.dth-snapshot summary { cursor: pointer; font-size: .8rem; font-weight: 650; color: var(--primary); }
.dth-snapshot pre { margin-top: var(--space-3); max-height: 480px; overflow: auto; }
.dth-review-actions { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-4); }
.dth-type-badge {
  display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 600;
  background: rgba(var(--gray-rgb),.08); color: var(--muted);
}

/* ── Confidence badge ── */
.dth-conf-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 40px; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 700; font-variant-numeric: tabular-nums;
}
.dth-conf-high { background: rgba(var(--primary-rgb),.1); color: var(--success); }
.dth-conf-low { background: rgba(var(--warning-rgb),.12); color: var(--warning); }

/* ── Empty state ── */
.dth-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-6); text-align: center;
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
}
.dth-empty-icon { font-size: 2rem; }
.dth-empty p { margin: 0; font-weight: 500; color: var(--success); }
.dth-empty small { max-width: 500px; line-height: 1.5; }

/* ── Tools grid ── */
.dth-tools-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3); margin-bottom: var(--space-4);
}
.dth-tool-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-5) var(--space-4); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  cursor: pointer; text-align: center;
  transition: transform .3s var(--ease-soft), box-shadow .3s, border-color .3s;
}
.dth-tool-card:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(var(--black-rgb),.06); border-color: var(--primary); }
.dth-tool-card:active:not(:disabled) { transform: scale(.97); }
.dth-tool-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dth-tool-card:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }
.dth-tool-icon { font-size: 1.6rem; }
.dth-tool-spinner {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid rgba(var(--primary-rgb),.2); border-top-color: var(--primary);
  animation: dth-spin .7s linear infinite;
}
@keyframes dth-spin { to { transform: rotate(360deg); } }
.dth-tool-label { font-size: .88rem; font-weight: 600; color: var(--ink); }
.dth-tool-card small { font-size: .75rem; color: var(--muted); }

.dth-sources { margin-top: var(--space-3); }
.dth-source-count { font-weight: 700; color: var(--primary); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .dth-tool-card:hover:not(:disabled) { transform: none; }
  .dth-tool-card:active:not(:disabled) { transform: none; }
  .dth-tool-spinner { animation: none; }
}

/* ── Dark ── */
.dark .dth-empty { background: var(--card); border-color: rgba(var(--white-rgb),.06); }
.dark .dth-review-card { background: var(--card); border-color: rgba(var(--white-rgb),.06); box-shadow: none; }
.dark .dth-tool-card { background: var(--card); border-color: rgba(var(--white-rgb),.06); }
.dark .dth-tool-card:hover:not(:disabled) { box-shadow: 0 4px 16px rgba(var(--black-rgb),.4); }
.dark .dth-conf-high { background: rgba(var(--primary-rgb),.18); color: rgb(var(--success-rgb)); }
.dark .dth-conf-low { background: rgba(var(--warning-rgb),.14); color: var(--accent-text); }
.dark .dth-tool-label { color: var(--ink); }
.dark .dth-count-warn { background: rgba(var(--warning-rgb),.12); color: var(--accent-text); }
.dark .dth-type-badge { background: rgba(var(--white-rgb),.06); }

@media (max-width: 720px) {
  .dth-review-head { flex-direction: column; }
  .dth-field-grid,
  .dth-inspection-grid { grid-template-columns: 1fr; }
  .dth-review-actions { justify-content: stretch; }
  .dth-review-actions button { flex: 1; }
}
</style>
