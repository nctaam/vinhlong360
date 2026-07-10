<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Quản lý Lịch trình</h1>
        <p class="lt-subtitle">{{ itineraries.length ? `${itineraries.length} lịch trình` : '' }}</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchItineraries"><span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới</button>
    </div>

    <div class="admin-toolbar">
      <button type="button" class="btn btn-primary" @click="openCreate">+ Tạo lịch trình</button>
      <input v-model="searchText" class="input" style="max-width: 260px" placeholder="Tìm lịch trình…" aria-label="Tìm lịch trình" />
    </div>

    <div v-if="loading" class="lt-skeleton" role="status" aria-label="Đang tải lịch trình">
      <div v-for="i in 5" :key="i" class="lt-skel-row"><div class="skel skel-id"></div><div class="skel skel-name"></div><div class="skel skel-area"></div><div class="skel skel-dur"></div><div class="skel skel-stops"></div></div>
    </div>
    <div v-else-if="loadError" class="admin-empty">
      <p>Không tải được danh sách lịch trình.</p>
      <button type="button" class="btn btn-secondary" @click="fetchItineraries">Thử lại</button>
    </div>
    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table" aria-label="Danh sách lịch trình">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Tên</th>
              <th scope="col">Khu vực</th>
              <th scope="col">Thời gian</th>
              <th scope="col">Điểm dừng</th>
              <th scope="col">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in filteredItineraries" :key="it.id">
              <td class="admin-td-id">{{ it.id }}</td>
              <td><strong>{{ itineraryDisplayName(it) }}</strong></td>
              <td>
                <div class="lt-area-cell">
                  <span v-if="it.area" class="lt-area-badge">{{ areaLabel(it.area) }}</span>
                  <span v-if="coverageLabel(it)" class="lt-coverage-badge">{{ coverageLabel(it) }}</span>
                  <span v-if="!it.area && !coverageLabel(it)" class="admin-td-muted">—</span>
                </div>
              </td>
              <td>
                <span v-if="it.duration" class="lt-duration"><span class="lt-duration-icon" aria-hidden="true">&#128338;</span> {{ it.duration }}</span>
                <span v-else class="admin-td-muted">—</span>
              </td>
              <td>
                <span class="lt-stops-badge">{{ it.stops?.length || 0 }}</span>
              </td>
              <td class="admin-actions">
                <button type="button" class="btn-success lt-row-btn" :aria-label="`Sửa lịch trình ${itineraryDisplayName(it)}`" @click="openEdit(it)">Sửa</button>
                <button type="button" class="btn-danger lt-row-btn" :aria-label="`Xóa lịch trình ${itineraryDisplayName(it)}`" :disabled="acting === it.id" @click="deleteItinerary(it.id)">Xóa</button>
              </td>
            </tr>
            <tr v-if="!filteredItineraries.length">
              <td colspan="6" class="admin-empty-row">
                <div class="admin-empty-state">
                  <span class="admin-empty-state-icon" aria-hidden="true">&#128506;</span>
                  <span class="admin-empty-state-text">Chưa có lịch trình. Tạo mới từ nút trên.</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Transition name="modal-fade">
    <div v-if="showModal" ref="ltModalRef" class="modal-overlay show" role="dialog" aria-modal="true" aria-labelledby="lt-modal-title" @click.self="showModal = false">
      <div class="modal admin-modal-md">
        <div class="modal-head">
          <h2 id="lt-modal-title">{{ editing ? 'Sửa Lịch trình' : 'Tạo Lịch trình' }}</h2>
        </div>
        <div class="modal-body admin-form-col">
          <input v-model="form.id" class="input" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editing" />
          <input v-model="form.name" class="input" placeholder="Tên lịch trình" aria-label="Tên lịch trình" />
          <select v-model="form.area" class="input" aria-label="Khu vực chính">
            <option value="">Chọn khu vực chính</option>
            <option v-for="area in itineraryAreaOptions" :key="area.key" :value="area.key">{{ area.label }}</option>
          </select>
          <fieldset class="lt-area-picker">
            <legend>Vùng bao phủ</legend>
            <label v-for="area in coverageAreaOptions" :key="area.key" class="lt-area-check">
              <input v-model="form.areas" type="checkbox" :value="area.key" />
              <span>{{ area.label }}</span>
            </label>
          </fieldset>
          <input v-model="form.duration" class="input" placeholder="Thời gian (VD: 1 ngày)" aria-label="Thời gian" />
          <textarea v-model="form.description" class="input admin-textarea" placeholder="Mô tả" aria-label="Mô tả lịch trình" rows="3"></textarea>

          <div class="lt-stops-head">
            <label class="admin-label lt-stops-label">Điểm dừng <span class="lt-stops-count">{{ stops.length }}</span></label>
            <button type="button" class="lt-mode-toggle" @click="toggleJsonMode">
              {{ jsonMode ? '☰ Dạng danh sách' : '{ } Dạng JSON' }}
            </button>
          </div>

          <textarea v-if="jsonMode" v-model="stopsJson" class="input admin-textarea admin-code" rows="8" aria-label="Stops dạng JSON"></textarea>

          <template v-else>
            <div v-if="!stops.length" class="lt-stops-empty">
              <span class="lt-stops-empty-icon" aria-hidden="true">&#128205;</span>
              <span>Chưa có điểm dừng nào. Thêm từ nút bên dưới.</span>
            </div>
            <ul v-else class="lt-stop-list">
              <li v-for="(s, i) in stops" :key="s._key" class="lt-stop-row" :class="`lt-stop-${stopStatus(s).kind}`">
                <div class="lt-stop-order">
                  <button type="button" class="lt-move" :disabled="i === 0" aria-label="Lên trên" title="Lên trên" @click="moveStop(i, -1)">&#9650;</button>
                  <span class="lt-stop-num">{{ i + 1 }}</span>
                  <button type="button" class="lt-move" :disabled="i === stops.length - 1" aria-label="Xuống dưới" title="Xuống dưới" @click="moveStop(i, 1)">&#9660;</button>
                  <span class="lt-stop-status" :class="`lt-stop-status-${stopStatus(s).kind}`" :title="stopStatus(s).title" :aria-label="stopStatus(s).title">{{ stopStatus(s).icon }}</span>
                </div>
                <div class="lt-stop-fields">
                  <div class="lt-stop-grid">
                    <input v-model="s.time" class="input lt-stop-input" placeholder="Thời điểm (VD: Sáng, Trưa)" aria-label="Thời điểm" />
                    <input v-model="s.entityId" class="input lt-stop-input" placeholder="ID điểm đến (slug)" aria-label="ID điểm đến" list="lt-entity-list" @input="onEntityInput" />
                  </div>
                  <input v-model="s.name" class="input lt-stop-input" placeholder="Tên hiển thị (tùy chọn)" aria-label="Tên hiển thị" />
                  <input v-model="s.note" class="input lt-stop-input" placeholder="Ghi chú (tùy chọn)" aria-label="Ghi chú" />
                </div>
                <button type="button" class="lt-stop-del" aria-label="Xóa điểm dừng" title="Xóa" @click="removeStop(i)">&#10005;</button>
              </li>
            </ul>
            <button type="button" class="lt-add-stop" @click="addStop">+ Thêm điểm dừng</button>
            <datalist id="lt-entity-list">
              <option v-for="ent in entitySuggestions" :key="ent.id" :value="ent.id">{{ ent.name }} ({{ ent.type }})</option>
            </datalist>
          </template>
        </div>
        <div class="admin-modal-actions lt-modal-actions">
          <span v-if="isDirty && !saving" class="lt-dirty-badge" role="status">Chưa lưu</span>
          <button type="button" class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button type="button" class="btn btn-primary" :disabled="saving || (!!editing && !isDirty)" @click="save">
            {{ saving ? 'Đang lưu...' : (editing ? (isDirty ? 'Cập nhật' : 'Không có thay đổi') : 'Tạo') }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Itinerary } from '~/types'
import { AREA_META } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Lịch trình — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

interface ItineraryForm {
  id: string
  name: string
  area: string
  areas: string[]
  duration: string
  description: string
}

interface ItinerariesResponse {
  itineraries?: Itinerary[]
}

const EMPTY_ITINERARY_FORM: ItineraryForm = { id: '', name: '', area: '', areas: [], duration: '', description: '' }

const itineraries = ref<Itinerary[]>([])
const searchText = ref('')
const itineraryAreaOptions = computed(() => Object.entries(AREA_META).map(([key, meta]) => ({ key, label: `${meta.emoji} ${meta.name}` })))
const coverageAreaOptions = computed(() => itineraryAreaOptions.value.filter(area => area.key !== 'lien-vung'))
const filteredItineraries = computed(() => {
  const q = searchText.value.toLowerCase().trim()
  if (!q) return itineraries.value
  return itineraries.value.filter((it) => {
    const text = [
      itineraryDisplayName(it),
      it.area || '',
      areaLabel(it.area || ''),
      ...(it.areas || []),
      ...(it.areas || []).map(areaLabel),
      it.id,
    ].join(' ').toLowerCase()
    return text.includes(q)
  })
})
const showModal = ref(false)
const ltModalRef = ref<HTMLElement | null>(null)
useModalA11y(showModal, ltModalRef, { onClose: () => { showModal.value = false } })
const editing = ref<Itinerary | null>(null)
const form = ref<ItineraryForm>({ ...EMPTY_ITINERARY_FORM })
const stopsJson = ref('[]')
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const saving = ref(false)

function areaLabel(area?: string) {
  if (!area) return ''
  return AREA_META[area]?.name || area
}

function normalizeAreas(values: unknown[]): string[] {
  const allowed = new Set(coverageAreaOptions.value.map(area => area.key))
  const seen = new Set<string>()
  const out: string[] = []
  for (const value of values) {
    const area = typeof value === 'string' ? value.trim() : ''
    if (!area || !allowed.has(area) || seen.has(area)) continue
    seen.add(area)
    out.push(area)
  }
  return out
}

function itineraryDisplayName(it: Itinerary) {
  return it.name || it.title || it.id
}

function coverageLabel(it: Itinerary) {
  const areas = normalizeAreas(it.areas || [])
  return areas.length ? areas.map(areaLabel).join(', ') : ''
}

// Visual stop editor state. Each row keeps the known fields plus _key (UI) and
// _extra (any unrecognised keys from the original stop, preserved on save).
interface StopRow {
  _key: number
  _idKey: 'id' | 'entityId' | 'entity_id'
  _extra: Record<string, unknown>
  time: string
  entityId: string
  name: string
  note: string
}
const stops = ref<StopRow[]>([])
const jsonMode = ref(false)
let stopKeySeq = 0

// Entity typeahead for stop entityId inputs
const entitySuggestions = ref<{ id: string; name: string; type?: string }[]>([])
let entitySearchTimer: ReturnType<typeof setTimeout> | null = null
function onEntityInput(e: Event) {
  const val = (e.target as HTMLInputElement).value.trim()
  if (entitySearchTimer) clearTimeout(entitySearchTimer)
  if (val.length < 2) { entitySuggestions.value = []; return }
  entitySearchTimer = setTimeout(async () => {
    try {
      const res = await $fetch<{ entities: any[] }>(`/admin-api/entities?q=${encodeURIComponent(val)}&limit=12`, { headers: authHeaders() })
      entitySuggestions.value = (res.entities || []).map((ent: any) => ({ id: ent.id, name: ent.name, type: ent.type || '' }))
    } catch { entitySuggestions.value = [] }
  }, 300)
}

// Dirty-state tracking (display + accidental-save guard only; never alters the
// save/data path). Snapshot is captured when the modal opens.
const initialSnapshot = ref('{}')
function buildSnapshot(): string {
  try {
    // Canonicalise stops to compact JSON so merely toggling between the list and
    // JSON editor (which pretty-prints) does not register as a change.
    let stopsPart: string
    if (jsonMode.value) {
      try { stopsPart = JSON.stringify(JSON.parse(stopsJson.value)) }
      catch { stopsPart = stopsJson.value }
    } else {
      stopsPart = JSON.stringify(stops.value.map(fromStopRow))
    }
    return JSON.stringify({ form: form.value, stops: stopsPart })
  } catch {
    return Math.random().toString() // never matches snapshot -> treated as dirty
  }
}
const isDirty = computed(() => buildSnapshot() !== initialSnapshot.value)

const KNOWN_STOP_KEYS = ['time', 'id', 'entityId', 'entity_id', 'name', 'note']

function toStopRow(raw: unknown): StopRow {
  const s = (raw && typeof raw === 'object') ? raw as Record<string, unknown> : {}
  const idKey: 'id' | 'entityId' | 'entity_id' =
    ('entityId' in s && !('id' in s)) ? 'entityId' :
    ('entity_id' in s && !('id' in s)) ? 'entity_id' : 'id'
  const extra: Record<string, unknown> = {}
  for (const k of Object.keys(s)) {
    if (!KNOWN_STOP_KEYS.includes(k)) extra[k] = s[k]
  }
  return {
    _key: stopKeySeq++,
    _idKey: idKey,
    _extra: extra,
    time: typeof s.time === 'string' ? s.time : (s.time == null ? '' : String(s.time)),
    entityId: String((s.entityId ?? s.entity_id ?? s.id ?? '') as string),
    name: typeof s.name === 'string' ? s.name : (s.name == null ? '' : String(s.name)),
    note: typeof s.note === 'string' ? s.note : (s.note == null ? '' : String(s.note)),
  }
}

// Serialize a row back to the backend stop shape, preserving the original id key
// (id/entityId/entity_id) and any unknown keys, and omitting empty optional fields.
function fromStopRow(r: StopRow): Record<string, unknown> {
  const out: Record<string, unknown> = { ...r._extra }
  const time = r.time.trim()
  const id = r.entityId.trim()
  const name = r.name.trim()
  const note = r.note.trim()
  if (time) out.time = time
  if (id) out[r._idKey] = id
  if (name) out.name = name
  if (note) out.note = note
  return out
}

function rowsFromStops(raw: unknown): StopRow[] {
  const arr = Array.isArray(raw) ? raw : []
  return arr.map(toStopRow)
}

// Lightweight per-row validation for the visual editor (display only; never
// blocks save). ok = has both time + id; warn = missing one of them.
function stopStatus(s: StopRow): { kind: 'ok' | 'warn'; icon: string; title: string } {
  const hasTime = !!s.time.trim()
  const hasId = !!s.entityId.trim()
  if (hasTime && hasId) return { kind: 'ok', icon: '✓', title: 'Đầy đủ thời điểm và ID điểm đến' }
  if (!hasTime && !hasId) return { kind: 'warn', icon: '⚠', title: 'Thiếu thời điểm và ID điểm đến' }
  if (!hasId) return { kind: 'warn', icon: '⚠', title: 'Thiếu ID điểm đến' }
  return { kind: 'warn', icon: '⚠', title: 'Thiếu thời điểm' }
}

function addStop() {
  stops.value.push({ _key: stopKeySeq++, _idKey: 'id', _extra: {}, time: '', entityId: '', name: '', note: '' })
}
function removeStop(i: number) { stops.value.splice(i, 1) }
function moveStop(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= stops.value.length) return
  const moved = stops.value.splice(i, 1)[0]
  if (moved) stops.value.splice(j, 0, moved)
}

// Switch between the visual list and the raw-JSON fallback, syncing state.
function toggleJsonMode() {
  if (jsonMode.value) {
    // Leaving JSON mode -> parse back into rows. If invalid, stay in JSON mode.
    try {
      stops.value = rowsFromStops(JSON.parse(stopsJson.value))
      jsonMode.value = false
    } catch {
      showToast('JSON stops không hợp lệ, không thể chuyển sang dạng danh sách', 'error')
    }
  } else {
    stopsJson.value = JSON.stringify(stops.value.map(fromStopRow), null, 2)
    jsonMode.value = true
  }
}

async function fetchItineraries() {
  loading.value = true
  loadError.value = false
  try {
    const res = await $fetch<ItinerariesResponse | Itinerary[]>('/admin-api/itineraries', { headers: authHeaders() })
    itineraries.value = Array.isArray(res) ? res : (res.itineraries || [])
  } catch {
    loadError.value = true
    showToast('Không thể tải danh sách lịch trình', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { ...EMPTY_ITINERARY_FORM }
  stops.value = []
  stopsJson.value = '[]'
  jsonMode.value = false
  initialSnapshot.value = buildSnapshot()
  showModal.value = true
}

function openEdit(it: Itinerary) {
  editing.value = it
  form.value = {
    id: it.id,
    name: it.name || it.title || '',
    area: it.area || it.region || '',
    areas: normalizeAreas(it.areas || []),
    duration: it.duration || '',
    description: it.description || it.summary || '',
  }
  const rawStops = it.stops || []
  stops.value = rowsFromStops(rawStops)
  stopsJson.value = JSON.stringify(rawStops, null, 2)
  jsonMode.value = false
  initialSnapshot.value = buildSnapshot()
  showModal.value = true
}

async function save() {
  if (saving.value) return
  if (!form.value.name?.trim()) { showToast('Tên không được để trống', 'error'); return }
  if (!editing.value && !form.value.id?.trim()) { showToast('ID không được để trống', 'error'); return }
  let stopsPayload: unknown[]
  if (jsonMode.value) {
    try { stopsPayload = JSON.parse(stopsJson.value) } catch { showToast('JSON stops không hợp lệ', 'error'); return }
  } else {
    stopsPayload = stops.value.map(fromStopRow)
  }
  const primaryArea = form.value.area.trim()
  const areas = normalizeAreas([
    ...form.value.areas,
    primaryArea !== 'lien-vung' ? primaryArea : '',
  ])
  const summary = form.value.description.trim()
  const body = {
    id: form.value.id.trim(),
    title: form.value.name.trim(),
    area: primaryArea || undefined,
    areas,
    duration: form.value.duration.trim() || undefined,
    description: summary,
    summary,
    stops: stopsPayload,
  }
  saving.value = true
  try {
    if (editing.value) {
      await $fetch(`/admin-api/itineraries/${form.value.id}`, { method: 'PUT', headers: authHeaders(), body })
      showToast('Đã cập nhật lịch trình', 'success')
    } else {
      await $fetch('/admin-api/itineraries', { method: 'POST', headers: authHeaders(), body })
      showToast('Đã tạo lịch trình mới', 'success')
    }
    showModal.value = false
    await fetchItineraries()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi lưu lịch trình'), 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItinerary(id: string) {
  if (!await confirmDialog(`Xóa lịch trình "${id}"?`, { danger: true })) return
  acting.value = id
  try {
    await $fetch(`/admin-api/itineraries/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa lịch trình', 'success')
    await fetchItineraries()
  } catch (e: unknown) {
    showToast(getErrorDetail(e, 'Lỗi khi xóa'), 'error')
  } finally {
    acting.value = null
  }
}

onMounted(() => fetchItineraries())
onUnmounted(() => { if (entitySearchTimer) clearTimeout(entitySearchTimer) })
</script>

<style scoped>
.lt-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

.lt-area-badge {
  display: inline-block; padding: 2px 10px; border-radius: 100px;
  font-size: .72rem; font-weight: 600; letter-spacing: .3px;
  background: rgba(var(--blue-rgb),.08); color: var(--info);
  transition: background .2s, transform .2s var(--ease-soft);
}
.lt-area-badge:hover { background: rgba(var(--blue-rgb),.14); transform: scale(1.04); }
.lt-duration {
  font-size: .82rem; color: var(--muted);
  display: inline-flex; align-items: center; gap: var(--space-1);
}
.lt-stops-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 6px;
  border-radius: 8px; font-size: .78rem; font-weight: 700;
  background: rgba(var(--primary-rgb),.08); color: var(--secondary-fg);
  transition: transform .2s var(--ease-soft);
}
tr:hover .lt-stops-badge { transform: scale(1.1); }

.lt-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.lt-empty-icon { font-size: 2rem; opacity: .3; }

@media (prefers-reduced-motion: reduce) {
  .lt-area-badge:hover, tr:hover .lt-stops-badge { transform: none; }
}

.dark .lt-area-badge { background: rgba(var(--blue-rgb),.12); }
.dark .lt-area-badge:hover { background: rgba(var(--blue-rgb),.2); }
.dark .lt-stops-badge { background: rgba(var(--primary-rgb),.15); }

.lt-area-cell { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.lt-coverage-badge {
  display: inline-flex; align-items: center; max-width: 220px;
  padding: 2px 8px; border-radius: 8px; font-size: .7rem;
  color: var(--muted); background: rgba(var(--primary-rgb), .06);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.lt-area-picker {
  border: 1px solid var(--border, rgba(var(--black-rgb),.12));
  border-radius: 10px; padding: 10px 12px; margin: 0;
  display: flex; flex-wrap: wrap; gap: 8px 12px;
}
.lt-area-picker legend {
  padding: 0 4px; color: var(--muted); font-size: .78rem; font-weight: 700;
}
.lt-area-check {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: .82rem; color: var(--text);
}
.lt-area-check input { width: 16px; height: 16px; accent-color: var(--primary); }
.dark .lt-coverage-badge { background: rgba(var(--primary-rgb), .12); }

/* --- Visual stops editor --- */
.lt-stops-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-2); margin-top: var(--space-1);
}
.lt-stops-label { margin: 0; display: inline-flex; align-items: center; gap: var(--space-2); }
.lt-stops-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; padding: 0 6px;
  border-radius: 7px; font-size: .74rem; font-weight: 700;
  background: rgba(var(--primary-rgb),.08); color: var(--secondary-fg);
}
.lt-mode-toggle {
  appearance: none; border: 1px solid var(--border, rgba(var(--black-rgb),.12));
  background: transparent; color: var(--muted);
  font-size: .76rem; font-weight: 600; padding: 6px 10px; border-radius: 8px;
  cursor: pointer; transition: background .2s, color .2s, border-color .2s;
}
.lt-mode-toggle:hover { background: rgba(var(--blue-rgb),.08); color: var(--info); border-color: rgba(var(--blue-rgb),.3); }
.lt-mode-toggle:focus-visible { outline: 2px solid var(--info); outline-offset: 2px; }

.lt-stops-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-2);
  font-size: .82rem; color: var(--muted);
  padding: var(--space-4); text-align: center;
  border: 1px dashed var(--border, rgba(var(--black-rgb),.14)); border-radius: 10px;
}
.lt-stops-empty-icon { font-size: 2rem; opacity: .4; line-height: 1; }

.lt-stop-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.lt-stop-row {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: var(--space-2); border: 1px solid var(--border, rgba(var(--black-rgb),.1));
  border-radius: 12px; background: rgba(var(--black-rgb),.015);
  transition: border-color .2s, background .2s;
}
.lt-stop-row:hover { border-color: rgba(var(--blue-rgb),.28); background: rgba(var(--blue-rgb),.03); }
/* Status colour-coding: a left accent bar for quick scanning. */
.lt-stop-row { border-left-width: 3px; }
.lt-stop-ok { border-left-color: rgba(var(--primary-rgb),.5); }
.lt-stop-warn { border-left-color: rgba(var(--warning-rgb),.55); }

.lt-stop-order { display: flex; flex-direction: column; align-items: center; gap: 2px; flex: 0 0 auto; padding-top: 2px; }
.lt-stop-num {
  font-size: .8rem; font-weight: 700; color: var(--muted);
  min-width: 22px; text-align: center;
}
.lt-stop-status {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; margin-top: 2px;
  border-radius: 50%; font-size: .68rem; font-weight: 700; line-height: 1;
}
.lt-stop-status-ok { background: rgba(var(--primary-rgb),.12); color: var(--secondary-fg); }
.lt-stop-status-warn { background: rgba(var(--warning-rgb),.14); color: var(--warning); }
.lt-move {
  appearance: none; border: none; background: transparent; cursor: pointer;
  color: var(--muted); font-size: .7rem; line-height: 1;
  width: 44px; height: 44px; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s, color .2s, transform .2s var(--ease-soft);
}
.lt-move:hover:not(:disabled) { background: rgba(var(--blue-rgb),.1); color: var(--info); transform: scale(1.12); }
.lt-move:focus-visible { outline: 2px solid var(--info); outline-offset: 1px; }
.lt-move:disabled { opacity: .25; cursor: not-allowed; }

.lt-stop-fields { flex: 1 1 auto; display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
.lt-stop-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); }
.lt-stop-input { width: 100%; }

.lt-stop-del {
  flex: 0 0 auto; appearance: none; border: none; background: transparent; cursor: pointer;
  color: var(--muted); font-size: .9rem; line-height: 1;
  width: 44px; height: 44px; min-width: 44px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s, color .2s, transform .2s var(--ease-soft);
}
.lt-stop-del:hover { background: rgba(var(--danger-rgb),.12); color: var(--error); transform: scale(1.1); }
.lt-stop-del:focus-visible { outline: 2px solid var(--error); outline-offset: 1px; }

.lt-add-stop {
  appearance: none; cursor: pointer; margin-top: var(--space-2);
  border: 1px dashed rgba(var(--blue-rgb),.4); background: rgba(var(--blue-rgb),.04);
  color: var(--info); font-size: .84rem; font-weight: 600;
  padding: 10px 14px; border-radius: 10px; width: 100%; min-height: 44px;
  transition: background .2s, border-color .2s, transform .2s var(--ease-soft);
}
.lt-add-stop:hover { background: rgba(var(--blue-rgb),.1); border-color: rgba(var(--blue-rgb),.6); transform: translateY(-1px); }
.lt-add-stop:focus-visible { outline: 2px solid var(--info); outline-offset: 2px; }

@media (max-width: 540px) {
  .lt-stop-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .lt-move:hover:not(:disabled), .lt-stop-del:hover, .lt-add-stop:hover { transform: none; }
}

/* Table-row action buttons: comfortable touch target + clear focus ring. */
.lt-row-btn { min-height: 44px; }
.lt-row-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* Duration cell: isolate the clock glyph so it can be tuned per theme. */
.lt-duration-icon { opacity: .65; }

/* Dirty-state badge (mirrors SettingsForm .sf-dirty-badge; that class is scoped
   to its own component, so the visual is redefined page-locally here). */
.lt-modal-actions { align-items: center; flex-wrap: wrap; }
.lt-dirty-badge {
  margin-right: auto;
  display: inline-flex; align-items: center;
  padding: var(--space-1) 10px; border-radius: 999px;
  font-size: .72rem; font-weight: 600; color: var(--primary);
  background: rgba(var(--primary-rgb),.1); border: .5px solid rgba(var(--primary-rgb),.25);
}

@media (prefers-reduced-motion: reduce) {
  .lt-row-btn { transition: none; }
}

.dark .lt-stops-count { background: rgba(var(--primary-rgb),.15); }
.dark .lt-stop-row { background: rgba(var(--white-rgb),.02); border-color: rgba(var(--white-rgb),.08); }
.dark .lt-stop-row:hover { background: rgba(var(--blue-rgb),.08); }
.dark .lt-stop-ok { border-left-color: rgba(var(--primary-rgb),.6); }
.dark .lt-stop-warn { border-left-color: rgba(var(--warning-rgb),.65); }
.dark .lt-stops-empty { border-color: rgba(var(--white-rgb),.14); }
.dark .lt-stop-status-ok { background: rgba(var(--primary-rgb),.2); color: rgb(var(--success-rgb)); }
.dark .lt-stop-status-warn { background: rgba(var(--warning-rgb),.22); color: var(--warning); }
.dark .lt-duration { color: rgba(var(--white-rgb),.55); }
.dark .lt-duration-icon { opacity: .8; }
.dark .lt-dirty-badge { color: rgb(var(--success-rgb)); background: rgba(var(--primary-rgb),.18); border-color: rgba(var(--success-rgb),.3); }

/* ── Skeleton loading ── */
.lt-skeleton { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-4) 0; }
.lt-skel-row { display: flex; gap: var(--space-3); padding: var(--space-2) 0; }
.skel { height: 14px; border-radius: 6px; background: var(--line, #e5e5ea); animation: ltSkelPulse 1.2s ease-in-out infinite; }
.skel-id { width: 60px; }
.skel-name { flex: 1; max-width: 200px; }
.skel-area { width: 80px; }
.skel-dur { width: 70px; }
.skel-stops { width: 40px; }
@keyframes ltSkelPulse { 0%, 100% { opacity: .4; } 50% { opacity: 1; } }
</style>
