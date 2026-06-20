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
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Khu vực</th>
              <th>Thời gian</th>
              <th>Điểm dừng</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in itineraries" :key="it.id">
              <td class="admin-td-id">{{ it.id }}</td>
              <td><strong>{{ it.name }}</strong></td>
              <td><span v-if="it.area" class="lt-area-badge">{{ it.area }}</span><span v-else class="admin-td-muted">—</span></td>
              <td>
                <span v-if="it.duration" class="lt-duration">&#128338; {{ it.duration }}</span>
                <span v-else class="admin-td-muted">—</span>
              </td>
              <td>
                <span class="lt-stops-badge">{{ it.stops?.length || 0 }}</span>
              </td>
              <td class="admin-actions">
                <button type="button" class="btn-success" @click="openEdit(it)">Sửa</button>
                <button type="button" class="btn-danger" :disabled="acting === it.id" @click="deleteItinerary(it.id)">Xóa</button>
              </td>
            </tr>
            <tr v-if="!itineraries.length">
              <td colspan="6" class="admin-empty-row">
                <div class="lt-empty">
                  <span class="lt-empty-icon">&#128506;</span>
                  <span>Chưa có lịch trình. Tạo mới từ nút trên.</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Transition name="modal-fade">
    <div v-if="showModal" class="modal-overlay show" role="dialog" aria-modal="true" :aria-label="editing ? 'Sửa Lịch trình' : 'Tạo Lịch trình'" @click.self="showModal = false" @keyup.escape="showModal = false">
      <div class="modal admin-modal-md">
        <h2>{{ editing ? 'Sửa Lịch trình' : 'Tạo Lịch trình' }}</h2>
        <div class="admin-form-col">
          <input v-model="form.id" class="input" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editing" />
          <input v-model="form.name" class="input" placeholder="Tên lịch trình" aria-label="Tên lịch trình" />
          <input v-model="form.area" class="input" placeholder="Khu vực (vinh-long / ben-tre / tra-vinh)" aria-label="Khu vực" />
          <input v-model="form.duration" class="input" placeholder="Thời gian (VD: 1 ngày)" aria-label="Thời gian" />
          <textarea v-model="form.description" class="input admin-textarea" placeholder="Mô tả" rows="3"></textarea>

          <div class="lt-stops-head">
            <label class="admin-label lt-stops-label">Điểm dừng <span class="lt-stops-count">{{ stops.length }}</span></label>
            <button type="button" class="lt-mode-toggle" @click="toggleJsonMode">
              {{ jsonMode ? '☰ Dạng danh sách' : '{ } Dạng JSON' }}
            </button>
          </div>

          <textarea v-if="jsonMode" v-model="stopsJson" class="input admin-textarea admin-code" rows="8" aria-label="Stops dạng JSON"></textarea>

          <template v-else>
            <div v-if="!stops.length" class="lt-stops-empty">Chưa có điểm dừng nào.</div>
            <ul v-else class="lt-stop-list">
              <li v-for="(s, i) in stops" :key="s._key" class="lt-stop-row">
                <div class="lt-stop-order">
                  <button type="button" class="lt-move" :disabled="i === 0" aria-label="Lên trên" title="Lên trên" @click="moveStop(i, -1)">&#9650;</button>
                  <span class="lt-stop-num">{{ i + 1 }}</span>
                  <button type="button" class="lt-move" :disabled="i === stops.length - 1" aria-label="Xuống dưới" title="Xuống dưới" @click="moveStop(i, 1)">&#9660;</button>
                </div>
                <div class="lt-stop-fields">
                  <div class="lt-stop-grid">
                    <input v-model="s.time" class="input lt-stop-input" placeholder="Thời điểm (VD: Sáng, Trưa)" aria-label="Thời điểm" />
                    <input v-model="s.entityId" class="input lt-stop-input" placeholder="ID điểm đến (slug)" aria-label="ID điểm đến" />
                  </div>
                  <input v-model="s.name" class="input lt-stop-input" placeholder="Tên hiển thị (tùy chọn)" aria-label="Tên hiển thị" />
                  <input v-model="s.note" class="input lt-stop-input" placeholder="Ghi chú (tùy chọn)" aria-label="Ghi chú" />
                </div>
                <button type="button" class="lt-stop-del" aria-label="Xóa điểm dừng" title="Xóa" @click="removeStop(i)">&#10005;</button>
              </li>
            </ul>
            <button type="button" class="lt-add-stop" @click="addStop">+ Thêm điểm dừng</button>
          </template>
        </div>
        <div class="admin-modal-actions">
          <button type="button" class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? 'Đang lưu...' : (editing ? 'Cập nhật' : 'Tạo') }}
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

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const itineraries = ref<Itinerary[]>([])
const showModal = ref(false)
const editing = ref<Record<string, unknown> | null>(null)
const form = ref<Record<string, unknown>>({})
const stopsJson = ref('[]')
const loading = ref(true)
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
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/itineraries', { headers: authHeaders() })
    itineraries.value = (res.itineraries || res || []) as Itinerary[]
  } catch {
    showToast('Không thể tải danh sách lịch trình', 'error')
  }
  loading.value = false
}

function openCreate() {
  editing.value = null
  form.value = { id: '', name: '', area: '', duration: '', description: '' }
  stops.value = []
  stopsJson.value = '[]'
  jsonMode.value = false
  showModal.value = true
}

function openEdit(it: Itinerary) {
  editing.value = it
  form.value = { id: it.id, name: it.name, area: it.area || '', duration: it.duration || '', description: it.description || '' }
  const rawStops = it.stops || []
  stops.value = rowsFromStops(rawStops)
  stopsJson.value = JSON.stringify(rawStops, null, 2)
  jsonMode.value = false
  showModal.value = true
}

async function save() {
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
    showToast((e as any)?.data?.detail || 'Lỗi khi lưu lịch trình', 'error')
  }
  saving.value = false
}

async function deleteItinerary(id: string) {
  if (!confirm(`Xóa lịch trình "${id}"?`)) return
  acting.value = id
  try {
    await $fetch(`/admin-api/itineraries/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa lịch trình', 'success')
    await fetchItineraries()
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi xóa', 'error')
  }
  acting.value = null
}

onMounted(() => fetchItineraries())
</script>

<style scoped>
.lt-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

.lt-area-badge {
  display: inline-block; padding: 2px 10px; border-radius: 100px;
  font-size: .72rem; font-weight: 600; letter-spacing: .3px;
  background: rgba(52,120,246,.08); color: #3478F6;
  transition: background .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.lt-area-badge:hover { background: rgba(52,120,246,.14); transform: scale(1.04); }
.lt-duration {
  font-size: .82rem; color: var(--muted);
  display: inline-flex; align-items: center; gap: 4px;
}
.lt-stops-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 6px;
  border-radius: 8px; font-size: .78rem; font-weight: 700;
  background: rgba(33,150,83,.08); color: #219653;
  transition: transform .2s cubic-bezier(.2,1,.4,1);
}
tr:hover .lt-stops-badge { transform: scale(1.1); }

.lt-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.lt-empty-icon { font-size: 2rem; opacity: .3; }

@media (prefers-reduced-motion: reduce) {
  .lt-area-badge:hover, tr:hover .lt-stops-badge { transform: none; }
}

.dark .lt-area-badge { background: rgba(52,120,246,.12); }
.dark .lt-area-badge:hover { background: rgba(52,120,246,.2); }
.dark .lt-stops-badge { background: rgba(33,150,83,.15); }

/* --- Visual stops editor --- */
.lt-stops-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-2); margin-top: var(--space-1);
}
.lt-stops-label { margin: 0; display: inline-flex; align-items: center; gap: 8px; }
.lt-stops-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; padding: 0 6px;
  border-radius: 7px; font-size: .74rem; font-weight: 700;
  background: rgba(33,150,83,.08); color: #219653;
}
.lt-mode-toggle {
  appearance: none; border: 1px solid var(--border, rgba(0,0,0,.12));
  background: transparent; color: var(--muted);
  font-size: .76rem; font-weight: 600; padding: 6px 10px; border-radius: 8px;
  cursor: pointer; transition: background .2s, color .2s, border-color .2s;
}
.lt-mode-toggle:hover { background: rgba(52,120,246,.08); color: #3478F6; border-color: rgba(52,120,246,.3); }
.lt-mode-toggle:focus-visible { outline: 2px solid #3478F6; outline-offset: 2px; }

.lt-stops-empty {
  font-size: .82rem; color: var(--muted);
  padding: var(--space-3); text-align: center;
  border: 1px dashed var(--border, rgba(0,0,0,.14)); border-radius: 10px;
}

.lt-stop-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.lt-stop-row {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: var(--space-2); border: 1px solid var(--border, rgba(0,0,0,.1));
  border-radius: 12px; background: rgba(0,0,0,.015);
  transition: border-color .2s, background .2s;
}
.lt-stop-row:hover { border-color: rgba(52,120,246,.28); background: rgba(52,120,246,.03); }

.lt-stop-order { display: flex; flex-direction: column; align-items: center; gap: 2px; flex: 0 0 auto; padding-top: 2px; }
.lt-stop-num {
  font-size: .8rem; font-weight: 700; color: var(--muted);
  min-width: 22px; text-align: center;
}
.lt-move {
  appearance: none; border: none; background: transparent; cursor: pointer;
  color: var(--muted); font-size: .7rem; line-height: 1;
  width: 28px; height: 24px; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .2s, color .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.lt-move:hover:not(:disabled) { background: rgba(52,120,246,.1); color: #3478F6; transform: scale(1.12); }
.lt-move:focus-visible { outline: 2px solid #3478F6; outline-offset: 1px; }
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
.lt-stop-del:hover { background: rgba(235,87,87,.12); color: #EB5757; transform: scale(1.1); }
.lt-stop-del:focus-visible { outline: 2px solid #EB5757; outline-offset: 1px; }

.lt-add-stop {
  appearance: none; cursor: pointer; margin-top: var(--space-2);
  border: 1px dashed rgba(52,120,246,.4); background: rgba(52,120,246,.04);
  color: #3478F6; font-size: .84rem; font-weight: 600;
  padding: 10px 14px; border-radius: 10px; width: 100%; min-height: 44px;
  transition: background .2s, border-color .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.lt-add-stop:hover { background: rgba(52,120,246,.1); border-color: rgba(52,120,246,.6); transform: translateY(-1px); }
.lt-add-stop:focus-visible { outline: 2px solid #3478F6; outline-offset: 2px; }

@media (max-width: 540px) {
  .lt-stop-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .lt-move:hover:not(:disabled), .lt-stop-del:hover, .lt-add-stop:hover { transform: none; }
}

.dark .lt-stops-count { background: rgba(33,150,83,.15); }
.dark .lt-stop-row { background: rgba(255,255,255,.02); border-color: rgba(255,255,255,.08); }
.dark .lt-stop-row:hover { background: rgba(52,120,246,.08); }
.dark .lt-stops-empty { border-color: rgba(255,255,255,.14); }
</style>
