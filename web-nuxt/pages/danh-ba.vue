<template>
  <div class="page dir-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Danh bạ' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-directory">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon">🏛️</span>
        <div>
          <h1>Danh bạ hành chính</h1>
          <p>Địa chỉ &amp; liên hệ UBND, công an và cơ quan công vụ theo từng xã/phường của tỉnh Vĩnh Long (sau hợp nhất: Vĩnh Long · Bến Tre · Trà Vinh).</p>
        </div>
      </div>
      <div v-if="totalWards" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ totalWards }}</span>
          <span class="stat-label">xã/phường</span>
        </div>
        <div v-for="g in wardGroups" :key="g.area" class="stat-item">
          <span class="stat-num">{{ g.wards.length }}</span>
          <span class="stat-label">{{ g.label }}</span>
        </div>
      </div>
    </section>

    <!-- Region quick-picks -->
    <section class="block">
      <div class="section-head">
        <h2>Chọn khu vực</h2>
      </div>
      <div class="quick-picks">
        <button
          v-for="g in wardGroups" :key="g.area"
          :class="['quick-pick', { active: selectedArea === g.area }]"
          @click="selectedArea = selectedArea === g.area ? '' : g.area"
        >
          <span class="quick-pick-icon">{{ AREA_META[g.area]?.emoji }}</span>
          <span class="quick-pick-label">{{ g.label }}</span>
          <span class="quick-pick-count">{{ g.wards.length }} xã/phường</span>
        </button>
      </div>
    </section>

    <!-- Ward picker -->
    <section class="block reveal">
      <label class="ward-pick">
        <span class="control-label">Chọn xã / phường:</span>
        <select v-model="wardId" aria-label="Chọn xã/phường">
          <option value="">— Chọn —</option>
          <optgroup v-for="g in filteredGroups" :key="g.area" :label="g.label">
            <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
          </optgroup>
        </select>
      </label>
    </section>

    <p class="dir-disclaimer">⚠️ Thông tin mang tính tham khảo và có thể thay đổi sau sắp xếp đơn vị hành chính —
      vui lòng kiểm chứng với cơ quan trước khi sử dụng.
      <NuxtLink to="/lien-he">Báo thông tin sai</NuxtLink>.</p>

    <div v-if="!wardId" class="empty-hint">
      <span class="empty-hint-icon">🏘️</span>
      <p>Hãy chọn một xã/phường để xem danh bạ cơ quan hành chính.</p>
    </div>
    <template v-else>
      <p class="ward-hub-link">
        <NuxtLink :to="`/xa-phuong/${wardId}`">🏘️ Xem trang đầy đủ xã/phường này (du lịch · lưu trú · đặc sản) →</NuxtLink>
      </p>
      <div v-if="loading" class="fac-skeleton" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
        <div v-for="i in 3" :key="i" class="fac-sk-item">
          <div class="sk-bar" style="width:35%"></div>
          <div class="sk-bar sk-bar--lg" style="width:65%"></div>
          <div class="sk-bar" style="width:50%"></div>
        </div>
      </div>
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

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/lien-he" class="cross-card">
          <span class="cross-icon">📩</span>
          <div><strong>Liên hệ</strong><p>Góp ý & báo sai</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { OFFICE_KIND, AREA_META } from '~/composables/useConstants'

useReveal()
const { show: showToast } = useToast()

const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']
const route = useRoute()

const { data: places } = await useAsyncData('dir-places', () => $fetch<any>('/api/places'))

const areaFromQuery = computed(() => {
  const a = route.query.area as string
  return a && AREA_META[a] ? a : ''
})

const selectedArea = ref(areaFromQuery.value)

const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: any) => ADMIN_LEVELS.includes(p.level))
  return Object.keys(AREA_META).map(area => ({
    area,
    label: AREA_META[area].name,
    wards: wards.filter((w: any) => w.area === area).sort((a: any, b: any) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

const filteredGroups = computed(() => {
  if (!selectedArea.value) return wardGroups.value
  return wardGroups.value.filter(g => g.area === selectedArea.value)
})

const totalWards = computed(() => wardGroups.value.reduce((sum, g) => sum + g.wards.length, 0))

const wardId = ref('')
const facilities = ref<any[]>([])
const loading = ref(false)

function attr(f: any, k: string) { return (f.attributes || {})[k] }
function kindMeta(f: any) { return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac }

const reported = ref<Record<string, boolean>>({})
async function reportFacility(f: any) {
  if (reported.value[f.id]) return
  const detail = (globalThis.prompt?.('Thông tin nào sai? (địa chỉ / SĐT / giờ làm việc…)') || '').trim()
  if (!detail) return
  try {
    await $fetch('/api/report', {
      method: 'POST',
      body: { target_id: f.id, target_type: 'facility', reason: 'Báo sai thông tin danh bạ', detail },
    })
    reported.value = { ...reported.value, [f.id]: true }
  } catch { showToast('Không thể gửi báo sai. Vui lòng thử lại.', 'error') }
}

watch(wardId, async (id) => {
  facilities.value = []
  if (!id) return
  loading.value = true
  try {
    const res = await $fetch<any>(`/api/facilities?place=${encodeURIComponent(id)}`)
    facilities.value = res.facilities || []
  } catch { showToast('Không thể tải danh bạ cơ quan', 'error') }
  loading.value = false
})

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
.dir-page { max-width: 920px; }
.empty-hint { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-8) var(--space-4); color: var(--muted); text-align: center; }
.empty-hint-icon { font-size: 2.5rem; }
.empty-hint p { margin: 0; font-size: var(--text-sm); }
.muted { color: var(--muted); }
.ward-pick { display: flex; flex-direction: column; gap: var(--space-2); max-width: 420px; }
.ward-pick select { padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-md); font-size: 1rem; min-height: 44px; background: var(--bg-alt); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.ward-pick select:focus { outline: none; border-color: var(--primary-fg); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .12), var(--shadow-xs); }
.dir-disclaimer { background: rgba(234, 140, 30, .06); border: .5px solid rgba(234, 140, 30, .2); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--text-sm); margin: var(--space-3) 0 var(--space-5); line-height: var(--leading-relaxed); }
.fac-list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); }
.fac { border: .5px solid var(--line); border-radius: var(--radius-lg); padding: var(--space-4); background: var(--card); box-shadow: var(--shadow-xs); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.fac:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.fac-head { display: flex; flex-direction: column; gap: 2px; margin-bottom: var(--space-2); }
.fac-kind { font-size: var(--text-xs); color: var(--primary-fg); font-weight: var(--weight-semibold); }
.fac-row { font-size: var(--text-sm); margin: 2px 0; }
.fac-row a { transition: color .3s var(--ease-out); }
.fac-row a:hover { color: var(--primary-fg); }
.fac-src { color: var(--muted); display: block; margin-top: var(--space-2); font-size: var(--text-xs); }
.ward-hub-link { margin: 0 0 var(--space-4); }
.ward-hub-link a { color: var(--primary-fg); font-weight: var(--weight-semibold); transition: opacity .3s var(--ease-out); }
.ward-hub-link a:active { opacity: .7; }
.fac-report { margin-top: var(--space-2); background: none; border: none; padding: 4px 0; color: var(--muted); font-size: var(--text-xs); cursor: pointer; text-decoration: underline; transition: color .3s var(--ease-out); min-height: 44px; display: inline-flex; align-items: center; }
.fac-report:hover:not(:disabled) { color: var(--primary-fg); }
.fac-report:active:not(:disabled) { transform: scale(.97); }
.fac-report:disabled { cursor: default; text-decoration: none; color: var(--success, #16a34a); }
.fac-skeleton { display: grid; gap: var(--space-3); }
.fac-sk-item { border: .5px solid var(--line); border-radius: var(--radius-lg); padding: var(--space-4); background: var(--card); display: flex; flex-direction: column; gap: var(--space-2); }
.sk-bar { height: 10px; border-radius: var(--radius-sm); background: linear-gradient(110deg, var(--bg-alt) 30%, var(--card) 50%, var(--bg-alt) 70%); background-size: 200% 100%; animation: shimmer 1.6s infinite linear; }
.sk-bar--lg { height: 14px; }
@media (prefers-reduced-motion: reduce) { .sk-bar { animation: none; } }
</style>
