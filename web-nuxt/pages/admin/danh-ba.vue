<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Danh bạ hành chính</h1>
        <p class="db-subtitle">Nhập cơ quan công vụ (UBND/công an/...) theo xã/phường. <strong>Bắt buộc khai nguồn chính thống.</strong></p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loadingList" @click="loadFacilities"><span :class="{ 'refresh-spin': loadingList }">&#8635;</span> Làm mới</button>
    </div>

    <!-- Form -->
    <form class="db-form" @submit.prevent="create">
      <h3 class="db-form-title">Thêm cơ quan mới</h3>
      <div class="db-form-grid">
        <label class="db-field">
          <span class="db-field-label">Tên cơ quan *</span>
          <input v-model="f.name" class="input" required placeholder="UBND xã An Bình" />
        </label>
        <label class="db-field">
          <span class="db-field-label">Loại cơ quan *</span>
          <select v-model="f.office_kind" class="input" required>
            <option value="">— Chọn —</option>
            <option v-for="(m, k) in OFFICE_KIND" :key="k" :value="k">{{ m.emoji }} {{ m.label }}</option>
          </select>
        </label>
        <label class="db-field">
          <span class="db-field-label">Xã / phường *</span>
          <select v-model="f.placeId" class="input" required>
            <option value="">— Chọn —</option>
            <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
              <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
        </label>
        <label class="db-field">
          <span class="db-field-label">Số điện thoại</span>
          <input v-model="f.phone" class="input" placeholder="0270 xxx xxxx" />
        </label>
        <label class="db-field">
          <span class="db-field-label">Địa chỉ</span>
          <input v-model="f.address" class="input" placeholder="Ấp ..., xã ..." />
        </label>
        <label class="db-field">
          <span class="db-field-label">Giờ làm việc</span>
          <input v-model="f.hours" class="input" placeholder="7:30-17:00, T2-T6" />
        </label>
        <label class="db-field db-field-full">
          <span class="db-field-label">Nguồn (URL chính thống) *</span>
          <input v-model="f.sourceUrl" class="input" required placeholder="https://...gov.vn/..." />
        </label>
      </div>
      <button type="submit" class="btn btn-primary" :disabled="busy">{{ busy ? 'Đang lưu...' : 'Thêm cơ quan' }}</button>
    </form>

    <!-- List -->
    <div class="db-list-section">
      <div class="db-list-head">
        <h2 class="admin-section-title">Đã có</h2>
        <span v-if="facilities.length" class="db-count-badge">{{ facilities.length }}</span>
      </div>

      <div v-if="loadingList" class="admin-loading"><div class="spinner"></div></div>
      <template v-else>
        <div v-if="facilities.length" class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>Cơ quan</th><th>Liên hệ</th><th>Nguồn</th><th></th></tr></thead>
            <tbody>
              <tr v-for="e in facilities" :key="e.id">
                <td>
                  <strong>{{ e.name }}</strong>
                  <small class="db-meta">{{ kindLabel(e) }} · {{ placeName(e) }}</small>
                </td>
                <td class="admin-td-muted">
                  <span v-if="attr(e,'phone')">{{ attr(e,'phone') }}</span>
                  <small v-if="attr(e,'address')" class="db-meta">{{ attr(e,'address') }}</small>
                </td>
                <td class="admin-td-muted"><small>{{ e.source?.url || e.source?.title || '—' }}</small></td>
                <td>
                  <button type="button" class="btn-danger btn-sm" style="border:none" :disabled="deleting === e.id" @click="del(e)">Xóa</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="db-empty">
          <span class="db-empty-icon">&#127963;</span>
          <span>Chưa có cơ quan nào. Thêm từ form trên.</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity, Place } from '~/types'
import { AREA_META, OFFICE_KIND } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']

const f = ref({ name: '', office_kind: '', placeId: '', phone: '', address: '', hours: '', sourceUrl: '' })
const busy = ref(false)
const facilities = ref<Entity[]>([])
const loadingList = ref(true)
const deleting = ref<string | null>(null)

const { data: places } = await useAsyncData('adb-places', () => $fetch<Place[]>('/api/places').catch(() => []))
const placeById = computed(() => Object.fromEntries((places.value || []).map((p: Entity) => [p.id, p])))
const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: Entity) => ADMIN_LEVELS.includes(p.level))
  return Object.keys(AREA_META).map(area => ({
    area, label: AREA_META[area].name,
    wards: wards.filter((w: Entity) => w.area === area).sort((a: Entity, b: Entity) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

function attr(e: any, k: string) { return (e.attributes || {})[k] || '' }
function kindLabel(e: Entity) { return (OFFICE_KIND[attr(e, 'office_kind')] || OFFICE_KIND.khac)?.label || '' }
function placeName(e: Entity) { return placeById.value[e.placeId]?.name || '' }

function slugify(s: string) {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'd')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)
}

async function loadFacilities() {
  loadingList.value = true
  try {
    facilities.value = await $fetch<any>('/api/facilities').then((r: any) => r.facilities || [])
  } catch {
    showToast('Không thể tải danh sách cơ quan', 'error')
    facilities.value = []
  }
  loadingList.value = false
}

async function create() {
  if (!f.value.name || !f.value.office_kind || !f.value.placeId || !f.value.sourceUrl) {
    showToast('Vui lòng điền đầy đủ các trường bắt buộc', 'error'); return
  }
  busy.value = true
  try {
    const id = `${f.value.office_kind}-${slugify(f.value.name)}`.slice(0, 90)
    await $fetch('/admin-api/entities', {
      method: 'POST', headers: authHeaders(),
      body: {
        id, type: 'facility', name: f.value.name, placeId: f.value.placeId,
        summary: f.value.name,
        attributes: { office_kind: f.value.office_kind, address: f.value.address, phone: f.value.phone, hours: f.value.hours },
        source: { url: f.value.sourceUrl, title: 'nguồn chính thống' },
      },
    })
    showToast('Đã thêm cơ quan', 'success')
    f.value = { name: '', office_kind: '', placeId: '', phone: '', address: '', hours: '', sourceUrl: '' }
    await loadFacilities()
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Thêm thất bại (id trùng?)', 'error')
  }
  busy.value = false
}

async function del(e: Entity) {
  if (!confirm(`Xóa "${e.name}"?`)) return
  deleting.value = e.id
  try {
    await $fetch(`/admin-api/entities/${e.id}`, { method: 'DELETE', headers: authHeaders() })
    facilities.value = facilities.value.filter(x => x.id !== e.id)
    showToast('Đã xóa cơ quan', 'success')
  } catch { showToast('Xóa thất bại', 'error') }
  deleting.value = null
}

onMounted(loadFacilities)
</script>

<style scoped>
.db-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; max-width: 500px; }

/* ── Form ── */
.db-form {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-5); margin-bottom: var(--space-6);
  transition: box-shadow .3s cubic-bezier(.2,1,.4,1), border-color .3s;
}
.db-form:focus-within { box-shadow: 0 4px 20px rgba(0,0,0,.06); border-color: rgba(33,150,83,.2); }
.db-form-title { font-size: .95rem; font-weight: 600; margin: 0 0 var(--space-4); }
.db-form-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: var(--space-3); margin-bottom: var(--space-4);
}
.db-field { display: flex; flex-direction: column; gap: 4px; }
.db-field-label {
  font-size: .78rem; font-weight: 600; color: var(--muted);
  transition: color .2s;
}
.db-field:focus-within .db-field-label { color: var(--primary, #219653); }
.db-field-full { grid-column: 1 / -1; }

/* ── List ── */
.db-list-section { margin-top: var(--space-4); }
.db-list-head {
  display: flex; align-items: center; gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.db-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 8px;
  border-radius: 100px; font-size: .72rem; font-weight: 700;
  background: rgba(52,120,246,.08); color: #3478F6;
}
.db-meta { display: block; color: var(--muted); margin-top: 2px; font-size: .78rem; }

.db-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-8);
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  color: var(--muted); font-size: .88rem;
}
.db-empty-icon { font-size: 2rem; opacity: .3; }

/* ── Dark ── */
.dark .db-form { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .db-form:focus-within { box-shadow: 0 4px 20px rgba(0,0,0,.3); border-color: rgba(33,150,83,.3); }
.dark .db-count-badge { background: rgba(52,120,246,.12); }
.dark .db-empty { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }

@media (max-width: 640px) {
  .db-form-grid { grid-template-columns: 1fr; }
}
</style>
