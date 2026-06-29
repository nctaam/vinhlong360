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

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải lịch trình"><div class="spinner"></div></div>
    <div v-else-if="loadError" class="admin-empty">
      <p>Không tải được danh sách lịch trình.</p>
      <button type="button" class="btn btn-secondary" @click="fetchItineraries">Thử lại</button>
    </div>
    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table">
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
              <td><strong>{{ it.name }}</strong></td>
              <td><span v-if="it.area" class="lt-area-badge">{{ it.area }}</span><span v-else class="admin-td-muted">—</span></td>
              <td>
                <span v-if="it.duration" class="lt-duration"><span class="lt-duration-icon" aria-hidden="true">&#128338;</span> {{ it.duration }}</span>
                <span v-else class="admin-td-muted">—</span>
              </td>
              <td>
                <span class="lt-stops-badge">{{ it.stops?.length || 0 }}</span>
              </td>
              <td class="admin-actions">
                <button type="button" class="btn-success lt-row-btn" :aria-label="`Sửa lịch trình ${it.name}`" @click="openEdit(it)">Sửa</button>
                <button type="button" class="btn-danger lt-row-btn" :aria-label="`Xóa lịch trình ${it.name}`" :disabled="acting === it.id" @click="deleteItinerary(it.id)">Xóa</button>
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
          <input v-model="form.area" class="input" placeholder="Khu vực (vinh-long / ben-tre / tra-vinh)" aria-label="Khu vực" />
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
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Lịch trình — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()
const itineraries = ref<Itinerary[]>([])
const searchText = ref('')
const filteredItineraries = computed(() => {
  const q = searchText.value.toLowerCase().trim()
  if (!q) return itineraries.value
  return itineraries.value.filter(it => (it.name || '').toLowerCase().includes(q) || (it.area || '').toLowerCase().includes(q) || it.id.toLowerCase().includes(q))
})
const showModal = ref(false)
const ltModalRef = ref<HTMLElement | null>(null)
useModalA11y(showModal, ltModalRef, { onClose: () => { showModal.value = false } })
const editing = ref<Record<string, unknown> | null>(null)
const form = ref<Record<string, unknown>>({})
const stopsJson = ref('[]')
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const saving = ref(false)

// Visual stop editor state. Each row keeps the known fields plus _key (UI) and
// _extra (any unrecognised keys from the original stop, preserved on save).
interface StopRow {
  _key: number
  _idKey: 'id' | 'entityId'
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
    } catch { /* ignore */ }
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

const KNOWN_STOP_KEYS = ['time', 'id', 'entityId', 'name', 'note']

function toStopRow(raw: unknown): StopRow {
  const s = (raw && typeof raw === 'object') ? raw as Record<string, unknown> : {}
  const idKey: 'id' | 'entityId' = ('entityId' in s && !('id' in s)) ? 'entityId' : 'id'
  const extra: Record<string, unknown> = {}
  for (const k of Object.keys(s)) {
    if (!KNOWN_STOP_KEYS.includes(k)) extra[k] = s[k]
  }
  return {
    _key: stopKeySeq++,
    _idKey: idKey,
    _extra: extra,
    time: typeof s.time === 'string' ? s.time : (s.time == null ? '' : String(s.time)),
    entityId: String((s.entityId ?? s.id ?? '') as string),
    name: typeof s.name === 'string' ? s.name : (s.name == null ? '' : String(s.name)),
    note: typeof s.note === 'string' ? s.note : (s.note == null ? '' : String(s.note)),
  }
}

// Serialize a row back to the backend stop shape, preserving the original id key
// (id vs entityId) and any unknown keys, and omitting empty optional fields.
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
    const res = await $fetch<Record<string, unknown>>('/admin-api/itineraries', { headers: authHeaders() })
    itineraries.value = (res.itineraries || res || []) as Itinerary[]
  } catch {
    loadError.value = true
    showToast('Không thể tải danh sách lịch trình', 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { id: '', name: '', area: '', duration: '', description: '' }
  stops.value = []
  stopsJson.value = '[]'
  jsonMode.value = false
  initialSnapshot.value = buildSnapshot()
  showModal.value = true
}

function openEdit(it: Itinerary) {
  editing.value = it
  form.value = { id: it.id, name: it.name, area: it.area || '', duration: it.duration || '', description: it.description || '' }
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
  const body = { ...form.value, stops: stopsPayload }
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
  transition: background .2s, transform .2s cubic-bezier(.2,1,.4,1);
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
  transition: transform .2s cubic-bezier(.2,1,.4,1);
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
  appearance: none; border: 1px solid var(--border, rgba(0,0,0,.12));
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
  border: 1px dashed var(--border, rgba(0,0,0,.14)); border-radius: 10px;
}
.lt-stops-empty-icon { font-size: 2rem; opacity: .4; line-height: 1; }

.lt-stop-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.lt-stop-row {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: var(--space-2); border: 1px solid var(--border, rgba(0,0,0,.1));
  border-radius: 12px; background: rgba(0,0,0,.015);
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
  width: 28px; height: 24px; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s, color .2s, transform .2s cubic-bezier(.2,1,.4,1);
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
  width: 32px; height: 32px; min-width: 32px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s, color .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.lt-stop-del:hover { background: rgba(var(--danger-rgb),.12); color: var(--error); transform: scale(1.1); }
.lt-stop-del:focus-visible { outline: 2px solid var(--error); outline-offset: 1px; }

.lt-add-stop {
  appearance: none; cursor: pointer; margin-top: var(--space-2);
  border: 1px dashed rgba(var(--blue-rgb),.4); background: rgba(var(--blue-rgb),.04);
  color: var(--info); font-size: .84rem; font-weight: 600;
  padding: 10px 14px; border-radius: 10px; width: 100%; min-height: 44px;
  transition: background .2s, border-color .2s, transform .2s cubic-bezier(.2,1,.4,1);
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
.lt-row-btn:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }

/* Duration cell: isolate the clock glyph so it can be tuned per theme. */
.lt-duration-icon { opacity: .65; }

/* Dirty-state badge (mirrors SettingsForm .sf-dirty-badge; that class is scoped
   to its own component, so the visual is redefined page-locally here). */
.lt-modal-actions { align-items: center; flex-wrap: wrap; }
.lt-dirty-badge {
  margin-right: auto;
  display: inline-flex; align-items: center;
  padding: var(--space-1) 10px; border-radius: 999px;
  font-size: .72rem; font-weight: 600; color: var(--primary, #219653);
  background: rgba(var(--primary-rgb),.1); border: .5px solid rgba(var(--primary-rgb),.25);
}

@media (prefers-reduced-motion: reduce) {
  .lt-row-btn { transition: none; }
}

.dark .lt-stops-count { background: rgba(var(--primary-rgb),.15); }
.dark .lt-stop-row { background: rgba(255,255,255,.02); border-color: rgba(255,255,255,.08); }
.dark .lt-stop-row:hover { background: rgba(var(--blue-rgb),.08); }
.dark .lt-stop-ok { border-left-color: rgba(var(--primary-rgb),.6); }
.dark .lt-stop-warn { border-left-color: rgba(var(--warning-rgb),.65); }
.dark .lt-stops-empty { border-color: rgba(255,255,255,.14); }
.dark .lt-stop-status-ok { background: rgba(var(--primary-rgb),.2); color: rgb(var(--success-rgb)); }
.dark .lt-stop-status-warn { background: rgba(var(--warning-rgb),.22); color: var(--warning); }
.dark .lt-duration { color: rgba(255,255,255,.55); }
.dark .lt-duration-icon { opacity: .8; }
.dark .lt-dirty-badge { color: rgb(var(--success-rgb)); background: rgba(var(--primary-rgb),.18); border-color: rgba(var(--success-rgb),.3); }
</style>
