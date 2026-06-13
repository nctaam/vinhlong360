<template>
  <main class="dir-page">
    <header>
      <h1>Danh bạ hành chính</h1>
      <p class="muted">Địa chỉ &amp; liên hệ UBND, công an và cơ quan công vụ theo từng xã/phường
      của tỉnh Vĩnh Long (sau hợp nhất: Vĩnh Long · Bến Tre · Trà Vinh).</p>
    </header>

    <label class="ward-pick">
      <span>Chọn xã / phường:</span>
      <select v-model="wardId">
        <option value="">— Chọn —</option>
        <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
          <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
        </optgroup>
      </select>
    </label>

    <p class="dir-disclaimer">⚠️ Thông tin mang tính tham khảo và có thể thay đổi sau sắp xếp đơn vị hành chính —
      vui lòng kiểm chứng với cơ quan trước khi sử dụng.
      <NuxtLink to="/lien-he">Báo thông tin sai</NuxtLink>.</p>

    <div v-if="!wardId" class="muted">Hãy chọn một xã/phường để xem danh bạ.</div>
    <template v-else>
      <p class="ward-hub-link">
        <NuxtLink :to="`/xa-phuong/${wardId}`">🏘️ Xem trang đầy đủ xã/phường này (du lịch · lưu trú · đặc sản) →</NuxtLink>
      </p>
      <div v-if="loading" class="muted">Đang tải…</div>
      <ul v-else-if="facilities.length" class="fac-list">
        <li v-for="f in facilities" :key="f.id" class="fac">
          <div class="fac-head">
            <span class="fac-kind">{{ kindMeta(f).emoji }} {{ kindMeta(f).label }}</span>
            <strong>{{ f.name }}</strong>
          </div>
          <div v-if="attr(f, 'address')" class="fac-row">📍 {{ attr(f, 'address') }}</div>
          <div v-if="attr(f, 'phone')" class="fac-row">📞 <a :href="`tel:${attr(f, 'phone')}`">{{ attr(f, 'phone') }}</a></div>
          <div v-if="attr(f, 'hours')" class="fac-row">🕒 {{ attr(f, 'hours') }}</div>
          <small v-if="f.source?.url || f.updatedAt" class="fac-src">
            Nguồn: <a v-if="f.source?.url" :href="f.source.url" target="_blank" rel="nofollow">{{ f.source?.title || 'nguồn' }}</a>
            <span v-else>{{ f.source?.title }}</span>
            <span v-if="f.updatedAt"> · cập nhật {{ f.updatedAt }}</span>
          </small>
          <button class="fac-report" :disabled="reported[f.id]" @click="reportFacility(f)">
            {{ reported[f.id] ? '✓ Đã gửi báo sai' : '⚠️ Báo thông tin sai' }}
          </button>
        </li>
      </ul>
      <EmptyState v-else message="Chưa có dữ liệu danh bạ cho xã/phường này. Dữ liệu đang được bổ sung từ nguồn chính thống." />
    </template>
  </main>
</template>

<script setup lang="ts">
import { OFFICE_KIND, AREA_META } from '~/composables/useConstants'

// canonicalUrl là hàm auto-import từ composables/useSeoHelpers.ts (KHÔNG phải composable useSeoHelpers()).
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']
const route = useRoute()

const { data: places } = await useAsyncData('dir-places', () => $fetch<any>('/api/places'))

// Pre-scope theo ?area= (đến từ trang khu-vuc/[area]); rỗng/không hợp lệ → hiện cả 3 vùng.
const areaFilter = computed(() => {
  const a = route.query.area as string
  return a && AREA_META[a] ? a : ''
})

const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: any) => ADMIN_LEVELS.includes(p.level))
  const areas = areaFilter.value ? [areaFilter.value] : Object.keys(AREA_META)
  return areas.map(area => ({
    area,
    label: AREA_META[area].name,
    wards: wards.filter((w: any) => w.area === area).sort((a: any, b: any) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

const wardId = ref('')
const facilities = ref<any[]>([])
const loading = ref(false)

function attr(f: any, k: string) { return (f.attributes || {})[k] }
function kindMeta(f: any) { return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac }

const reported = ref<Record<string, boolean>>({})
async function reportFacility(f: any) {
  if (reported.value[f.id]) return
  const detail = (globalThis.prompt?.('Thông tin nào sai? (địa chỉ / SĐT / giờ làm việc…)') || '').trim()
  try {
    await $fetch('/api/report', {
      method: 'POST',
      body: { target_id: f.id, target_type: 'facility', reason: 'Báo sai thông tin danh bạ', detail },
    })
    reported.value = { ...reported.value, [f.id]: true }
  } catch { /* rate-limited / lỗi mạng — bỏ qua, người dùng có thể thử lại */ }
}

watch(wardId, async (id) => {
  facilities.value = []
  if (!id) return
  loading.value = true
  try {
    const res = await $fetch<any>(`/api/facilities?place=${encodeURIComponent(id)}`)
    facilities.value = res.facilities || []
  } catch { /* empty */ }
  loading.value = false
})

// JSON-LD GovernmentOffice cho các cơ quan đang hiển thị (AI/Google trích dẫn).
const jsonLd = computed(() => facilities.value
  .filter((f: any) => attr(f, 'address') || attr(f, 'phone'))
  .map((f: any) => ({
    '@context': 'https://schema.org', '@type': 'GovernmentOffice',
    name: f.name,
    ...(attr(f, 'address') ? { address: attr(f, 'address') } : {}),
    ...(attr(f, 'phone') ? { telephone: attr(f, 'phone') } : {}),
    ...(attr(f, 'hours') ? { openingHours: attr(f, 'hours') } : {}),
  })))

useSeoMeta({
  title: 'Danh bạ hành chính xã/phường — vinhlong360',
  description: 'Địa chỉ, số điện thoại UBND, công an và cơ quan công vụ theo xã/phường tỉnh Vĩnh Long (Vĩnh Long, Bến Tre, Trà Vinh).',
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/danh-ba') }],
  script: jsonLd.value.length
    ? [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonLd.value) }]
    : [],
}))
</script>

<style scoped>
.dir-page { max-width: 820px; margin: 0 auto; padding: 24px 16px 64px; }
.muted { color: var(--muted, #888); }
.ward-pick { display: flex; flex-direction: column; gap: 6px; margin: 16px 0; max-width: 420px; }
.ward-pick select { padding: 10px; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; font-size: 1rem; }
.dir-disclaimer { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 10px 12px; font-size: .85rem; margin: 12px 0 20px; }
.fac-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
.fac { border: 1px solid rgba(0,0,0,.1); border-radius: 10px; padding: 14px; }
.fac-head { display: flex; flex-direction: column; gap: 2px; margin-bottom: 6px; }
.fac-kind { font-size: .8rem; color: var(--primary, #9C3D22); }
.fac-row { font-size: .92rem; margin: 2px 0; }
.fac-src { color: var(--muted, #999); display: block; margin-top: 6px; }
.ward-hub-link { margin: 0 0 14px; }
.ward-hub-link a { color: var(--primary, #9C3D22); font-weight: 600; }
.fac-report { margin-top: 8px; background: none; border: none; padding: 0; color: var(--muted, #999); font-size: .78rem; cursor: pointer; text-decoration: underline; }
.fac-report:hover:not(:disabled) { color: var(--primary, #9C3D22); }
.fac-report:disabled { cursor: default; text-decoration: none; color: #16a34a; }
</style>
