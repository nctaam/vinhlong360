<template>
  <div>
    <div class="admin-head-row">
      <h1>Danh bạ hành chính</h1>
      <button class="admin-refresh" :disabled="loadingList" @click="loadFacilities">🔄 Làm mới</button>
    </div>
    <p class="admin-muted">Nhập cơ quan công vụ (UBND/công an/...) theo xã/phường. <strong>Bắt buộc khai nguồn chính thống</strong> — không tự bịa địa chỉ/SĐT.</p>

    <form class="card-form" @submit.prevent="create">
      <div class="grid2">
        <label>Tên cơ quan*<input v-model="f.name" class="input" required placeholder="UBND xã An Bình" /></label>
        <label>Loại cơ quan*
          <select v-model="f.office_kind" class="input" required>
            <option value="">— Chọn —</option>
            <option v-for="(m, k) in OFFICE_KIND" :key="k" :value="k">{{ m.emoji }} {{ m.label }}</option>
          </select>
        </label>
        <label>Xã / phường*
          <select v-model="f.placeId" class="input" required>
            <option value="">— Chọn —</option>
            <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
              <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
        </label>
        <label>Số điện thoại<input v-model="f.phone" class="input" placeholder="0270 xxx xxxx" /></label>
        <label>Địa chỉ<input v-model="f.address" class="input" placeholder="Ấp …, xã …" /></label>
        <label>Giờ làm việc<input v-model="f.hours" class="input" placeholder="7:30–17:00, T2–T6" /></label>
        <label>Nguồn (URL chính thống)*<input v-model="f.sourceUrl" class="input" required placeholder="https://...gov.vn/..." /></label>
      </div>
      <button class="btn btn-primary" :disabled="busy">{{ busy ? 'Đang lưu…' : '➕ Thêm cơ quan' }}</button>
    </form>

    <h2 class="admin-section-title" style="margin-top:20px">Đã có ({{ facilities.length }})</h2>

    <div v-if="loadingList" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <table v-if="facilities.length" class="admin-simple-table">
        <thead><tr><th>Cơ quan</th><th>Liên hệ</th><th>Nguồn</th><th></th></tr></thead>
        <tbody>
          <tr v-for="e in facilities" :key="e.id">
            <td><strong>{{ e.name }}</strong><br><small class="admin-muted">{{ kindLabel(e) }} · {{ placeName(e) }}</small></td>
            <td><small>{{ attr(e,'phone') }}<br>{{ attr(e,'address') }}</small></td>
            <td><small class="admin-muted">{{ e.source?.url || e.source?.title || '—' }}</small></td>
            <td><button class="btn btn-sm btn-ghost danger" :disabled="deleting === e.id" @click="del(e)">Xóa</button></td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-else message="Chưa có cơ quan nào. Thêm từ form trên." />
    </template>
  </div>
</template>

<script setup lang="ts">
import { AREA_META, OFFICE_KIND } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']

const f = ref({ name: '', office_kind: '', placeId: '', phone: '', address: '', hours: '', sourceUrl: '' })
const busy = ref(false)
const facilities = ref<any[]>([])
const loadingList = ref(true)
const deleting = ref<string | null>(null)

const { data: places } = await useAsyncData('adb-places', () => $fetch<any>('/api/places').catch(() => []))
const placeById = computed(() => Object.fromEntries((places.value || []).map((p: any) => [p.id, p])))
const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: any) => ADMIN_LEVELS.includes(p.level))
  return Object.keys(AREA_META).map(area => ({
    area, label: AREA_META[area].name,
    wards: wards.filter((w: any) => w.area === area).sort((a: any, b: any) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

function attr(e: any, k: string) { return (e.attributes || {})[k] || '' }
function kindLabel(e: any) { return (OFFICE_KIND[attr(e, 'office_kind')] || OFFICE_KIND.khac)?.label || '' }
function placeName(e: any) { return placeById.value[e.placeId]?.name || '' }

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
  if (!f.value.name || !f.value.office_kind || !f.value.placeId || !f.value.sourceUrl) return
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
  } catch (e: any) {
    showToast(e?.data?.detail || 'Thêm thất bại (id trùng?)', 'error')
  }
  busy.value = false
}

async function del(e: any) {
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
.card-form { border: 1px solid var(--line, #eee); border-radius: 10px; padding: 16px; margin-top: 12px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.grid2 label { display: flex; flex-direction: column; gap: 4px; font-size: .9rem; }
@media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } }
</style>
