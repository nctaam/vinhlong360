<template>
  <section class="page dir-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Danh bạ' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-directory">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🏛️</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="totalWards" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="totalWards" class="stat-num" />
          <span class="stat-label">xã/phường</span>
        </div>
        <div v-for="g in wardGroups" :key="g.area" class="stat-item">
          <CountUp :value="g.wards.length" class="stat-num" />
          <span class="stat-label">{{ g.label }}</span>
        </div>
      </div>
    </section>

    <!-- Error state -->
    <EmptyState v-if="placesError && !places?.length" icon="⚠️" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau.">
      <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('dir-places')">Thử lại</button>
    </EmptyState>

    <!-- Region quick-picks -->
    <section v-if="!placesError" class="block band reveal">
      <div class="section-head">
        <h2>Chọn khu vực</h2>
      </div>
      <div class="quick-picks region-quick-picks" role="group" aria-label="Chọn khu vực">
        <button type="button"
          v-for="g in wardGroups" :key="g.area"
          :class="['quick-pick', { active: selectedArea === g.area }]"
          :style="{ '--AREA-rgb': AREA_RGB[g.area] }"
          :aria-pressed="selectedArea === g.area"
          @click="selectedArea = selectedArea === g.area ? '' : g.area"
        >
          <span class="quick-pick-icon">{{ AREA_META[g.area]?.emoji }}</span>
          <span class="quick-pick-label">{{ g.label }}</span>
          <span class="quick-pick-count">{{ g.wards.length }} xã/phường</span>
        </button>
      </div>
    </section>

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2>Danh bạ hành chính — tìm nhanh liên hệ địa phương</h2>
      <p>Khi đến một vùng đất mới, việc biết số điện thoại và địa chỉ cơ quan hành chính địa phương là rất cần thiết — từ xin xác nhận tạm trú, hỏi thông tin quy hoạch, đến liên hệ công an khi cần hỗ trợ. Danh bạ này tổng hợp thông tin liên hệ UBND, công an và các cơ quan công vụ theo từng xã, phường trên toàn vùng Vĩnh Long, Bến Tre và Trà Vinh.</p>
      <p>Sau khi sáp nhập ba tỉnh thành một đơn vị hành chính mới, hệ thống xã/phường đang trong quá trình điều chỉnh. Thông tin trên đây được cập nhật liên tục nhưng có thể chưa phản ánh đầy đủ các thay đổi mới nhất — vui lòng kiểm chứng trực tiếp với cơ quan khi cần.</p>
    </section>

    <!-- Ward picker -->
    <section ref="wardSection" class="block reveal">
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

    <p class="dir-disclaimer"><strong class="dir-disclaimer-mark" aria-hidden="true">⚠️</strong> Thông tin mang tính tham khảo và có thể thay đổi sau sắp xếp đơn vị hành chính —
      vui lòng kiểm chứng với cơ quan trước khi sử dụng.
      <NuxtLink to="/lien-he" class="dir-disclaimer-link">Báo thông tin sai</NuxtLink>.</p>

    <div v-if="!wardId" class="empty-hint">
      <span class="empty-hint-halo" aria-hidden="true"><span class="empty-hint-icon">🏘️</span></span>
      <h3 class="empty-hint-title">Chọn một xã/phường</h3>
      <p>Chọn khu vực rồi chọn xã/phường ở trên để xem danh bạ cơ quan hành chính.</p>
    </div>
    <template v-else>
      <p class="ward-hub-link">
        <NuxtLink :to="`/xa-phuong/${wardId}`">🏘️ Xem trang đầy đủ xã/phường này (du lịch · lưu trú · đặc sản) →</NuxtLink>
      </p>
      <div v-if="loading" class="fac-skeleton" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
        <div v-for="i in 3" :key="i" class="fac-sk-item">
          <div class="sk-bar sk-bar--badge"></div>
          <div class="sk-bar sk-bar--lg sk-bar--wide"></div>
          <div class="sk-bar sk-bar--mid"></div>
          <div class="sk-bar sk-bar--sm"></div>
        </div>
      </div>
      <ul v-else-if="facilities.length" class="fac-list">
        <li v-for="f in facilities" :key="f.id" class="fac">
          <div class="fac-head">
            <span class="fac-kind">{{ kindMeta(f).emoji }} {{ kindMeta(f).label }}</span>
            <strong>{{ f.name }}</strong>
          </div>
          <div v-if="attr(f, 'address')" class="fac-row">📍 {{ attr(f, 'address') }}</div>
          <div v-if="attr(f, 'phone')" class="fac-row">📞 <a :href="telHref(attr(f, 'phone'))">{{ attr(f, 'phone') }}</a></div>
          <div v-if="attr(f, 'hours')" class="fac-row">🕒 {{ attr(f, 'hours') }}</div>
          <footer v-if="sourceUrl(f) || f.updatedAt" class="fac-src">
            <span v-if="isOfficialSource(f)" class="fac-verified" title="Nguồn chính thống">✓</span>
            Nguồn: <a v-if="sourceUrl(f)" :href="sourceUrl(f)" target="_blank" rel="nofollow noopener">{{ sourceName(f) || 'nguồn' }}</a>
            <span v-else>{{ sourceName(f) }}</span>
            <time v-if="f.updatedAt" :datetime="f.updatedAt"> · cập nhật {{ relativeUpdated(f.updatedAt) }}</time>
          </footer>
          <button type="button" class="fac-report" :disabled="reported[f.id]" :aria-expanded="reportingId === f.id" :aria-controls="`report-${f.id}`" @click="openReport(f)">
            {{ reported[f.id] ? '✓ Đã gửi báo sai' : '⚠️ Báo thông tin sai' }}
          </button>
          <div v-if="reportingId === f.id" :id="`report-${f.id}`" class="fac-report-form" role="region" :aria-label="`Báo sai thông tin ${f.name}`">
            <textarea v-model="reportDetail" class="textarea" rows="2" placeholder="Thông tin nào sai? (địa chỉ / SĐT / giờ làm việc…)" aria-label="Mô tả thông tin sai"></textarea>
            <div class="fac-report-actions">
              <button type="button" class="btn btn-primary btn-sm" :disabled="reportSending || reportDetail.trim().length < 3" @click="submitReport(f)">{{ reportSending ? 'Đang gửi…' : 'Gửi' }}</button>
              <button type="button" class="btn btn-ghost btn-sm" @click="reportingId = ''">Hủy</button>
            </div>
          </div>
        </li>
      </ul>
      <EmptyState v-else-if="facilitiesError" icon="⚠️" title="Không thể tải danh bạ" message="Có lỗi khi tải dữ liệu. Vui lòng thử lại.">
        <button type="button" class="btn btn-outline btn-sm" @click="loadFacilities">Thử lại</button>
      </EmptyState>
      <EmptyState v-else icon="📋" title="Chưa có danh bạ" message="Chưa có dữ liệu danh bạ cho xã/phường này. Dữ liệu đang được bổ sung từ nguồn chính thống." />
    </template>

    <!-- Cross-links -->
    <section class="block band reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/lien-he" class="cross-card">
          <span class="cross-icon" aria-hidden="true">📩</span>
          <div><strong>Liên hệ</strong><p>Góp ý & báo sai</p></div>
        </NuxtLink>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { Entity, EntitySource } from '~/types'
import { OFFICE_KIND, AREA_META } from '~/composables/useConstants'

const AREA_RGB: Record<string, string> = {
  'vinh-long': 'var(--primary-rgb)',
  'ben-tre': 'var(--secondary-rgb)',
  'tra-vinh': 'var(--river-rgb)',
}

useReveal()
const { f: pc } = usePageContent('danh_ba')
const { show: showToast } = useToast()

const ADMIN_LEVELS = ['phuong', 'xa']  // danh-bạ chỉ xã/phường (124), KHÔNG gộp cấp tỉnh
const route = useRoute()

const { data: places, error: placesError } = await useAsyncData('dir-places', () => apiFetch<Entity[]>('/api/places'))

const areaFromQuery = computed(() => {
  const a = route.query.area as string
  return a && AREA_META[a] ? a : ''
})

const selectedArea = ref(areaFromQuery.value)
const wardSection = ref<HTMLElement | null>(null)

watch(selectedArea, () => {
  nextTick(() => wardSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
})

const wardGroups = computed(() => {
  const grouped: Record<string, Entity[]> = {}
  for (const p of (places.value || [])) {
    const area = p.area
    if (!p.level || !ADMIN_LEVELS.includes(p.level) || !area || !AREA_META[area]) continue
    if (!grouped[area]) grouped[area] = []
    grouped[area].push(p)
  }
  return Object.keys(AREA_META)
    .filter(area => grouped[area]?.length)
    .map(area => {
      const meta = AREA_META[area]
      return {
        area,
        label: meta?.name || area,
        wards: (grouped[area] || []).sort((a: Entity, b: Entity) => a.name.localeCompare(b.name, 'vi')),
      }
    })
})

const filteredGroups = computed(() => {
  if (!selectedArea.value) return wardGroups.value
  return wardGroups.value.filter(g => g.area === selectedArea.value)
})

const totalWards = computed(() => wardGroups.value.reduce((sum, g) => sum + g.wards.length, 0))

const wardId = ref('')
const facilities = ref<Entity[]>([])
const facilitiesError = ref(false)
const loading = ref(false)

function attr(f: Entity, k: string): string {
  const value = (f.attributes || {})[k]
  return typeof value === 'string' ? value : value == null ? '' : String(value)
}
function kindMeta(f: Entity): { emoji: string; label: string } {
  return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac || { emoji: '🏛️', label: 'Cơ quan' }
}
function primarySource(f: Entity): EntitySource | undefined {
  return Array.isArray(f.source) ? f.source[0] : f.source
}
function sourceUrl(f: Entity): string {
  return primarySource(f)?.url || ''
}
function sourceName(f: Entity): string {
  return primarySource(f)?.name || ''
}

// Only flag as verified when the source URL is a genuine official gov domain — never fabricate trust (Track-H)
function isOfficialSource(f: Entity) {
  const url = sourceUrl(f)
  return /\.gov\.vn(\/|$|\?|#)/i.test(url)
}
// Relative "x ngày trước"; falls back to the raw stored value if unparseable
function relativeUpdated(raw: string) {
  if (!raw) return ''
  const t = Date.parse(raw)
  if (Number.isNaN(t)) return raw
  const days = Math.floor((Date.now() - t) / 86400000)
  if (days <= 0) return 'hôm nay'
  if (days === 1) return 'hôm qua'
  if (days < 30) return `${days} ngày trước`
  if (days < 365) return `${Math.floor(days / 30)} tháng trước`
  return `${Math.floor(days / 365)} năm trước`
}

const reported = ref<Record<string, boolean>>({})
const reportingId = ref('')
const reportDetail = ref('')
const reportSending = ref(false)

function openReport(f: Entity) {
  if (reported.value[f.id]) return
  reportingId.value = reportingId.value === f.id ? '' : f.id
  reportDetail.value = ''
}

async function submitReport(f: Entity) {
  const detail = reportDetail.value.trim()
  if (!detail) return
  reportSending.value = true
  try {
    await $fetch('/api/report', {
      method: 'POST',
      body: { target_id: f.id, target_type: 'facility', reason: 'Báo sai thông tin danh bạ', detail },
    })
    reported.value = { ...reported.value, [f.id]: true }
    reportingId.value = ''
    showToast('Đã gửi báo sai. Cảm ơn bạn!', 'success')
  } catch { showToast('Không thể gửi báo sai. Vui lòng thử lại.', 'error') }
  reportSending.value = false
}

let facilitiesAbort: AbortController | null = null

onBeforeUnmount(() => {
  facilitiesAbort?.abort()
})

async function loadFacilities() {
  if (facilitiesAbort) facilitiesAbort.abort()
  const id = wardId.value
  facilities.value = []
  facilitiesError.value = false
  if (!id) { loading.value = false; return }
  loading.value = true
  const ctrl = new AbortController()
  facilitiesAbort = ctrl
  try {
    const res = await $fetch<{ facilities: Entity[] }>(`/api/facilities?place=${encodeURIComponent(id)}`, { signal: ctrl.signal })
    if (ctrl.signal.aborted) return
    facilities.value = res.facilities || []
  } catch (err: unknown) {
    if (ctrl.signal.aborted) return
    facilitiesError.value = true
    showToast('Không thể tải danh bạ cơ quan', 'error')
  }
  loading.value = false
}
watch(wardId, loadFacilities)

const jsonLd = computed(() => facilities.value
  .filter((f: Entity) => attr(f, 'address') || attr(f, 'phone'))
  .map((f: Entity) => ({
    '@context': 'https://schema.org', '@type': 'GovernmentOffice',
    name: f.name,
    ...(attr(f, 'address') ? { address: attr(f, 'address') } : {}),
    ...(attr(f, 'phone') ? { telephone: attr(f, 'phone') } : {}),
    ...(attr(f, 'hours') ? { openingHours: attr(f, 'hours') } : {}),
  })))

useSeoMeta({
  ogType: 'website',
  title: () => pc('seo_title') || 'Danh bạ hành chính — vinhlong360',
  description: () => pc('seo_description') || 'Danh bạ xã/phường, cơ quan hành chính Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: () => pc('og_title') || 'Danh bạ — vinhlong360',
  ogDescription: () => pc('og_description') || 'Tra cứu thông tin hành chính địa phương.',
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/danh-ba') }],
  script: jsonLd.value.length
    ? [{ type: 'application/ld+json', innerHTML: safeJsonLd(jsonLd.value) }]
    : [],
}))
</script>

<style scoped>
.dir-page { max-width: 920px; }
.empty-hint { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-8) var(--space-4); color: var(--muted); text-align: center; background: radial-gradient(120% 100% at 50% 0%, rgba(var(--primary-rgb), .06), transparent 70%); border: .5px solid var(--line); border-radius: var(--radius-lg); }
.empty-hint-halo { display: inline-flex; align-items: center; justify-content: center; width: 96px; height: 96px; border-radius: 50%; background: radial-gradient(circle, rgba(var(--primary-rgb), .14), rgba(var(--primary-rgb), .04) 70%); margin-bottom: var(--space-1); }
.empty-hint-icon { font-size: 2.6rem; line-height: 1; }
.empty-hint-title { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); }
.empty-hint p { margin: 0; font-size: var(--text-sm); max-width: 38ch; }
.muted { color: var(--muted); }
.ward-pick { display: flex; flex-direction: column; gap: var(--space-2); max-width: 420px; padding: var(--space-4); border: .5px solid var(--line); border-radius: var(--radius-lg); background: var(--card); box-shadow: var(--shadow-xs); }
.ward-pick .control-label { font-weight: var(--weight-semibold); }
.ward-pick select { padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-md); font-size: 1rem; min-height: 44px; background: var(--bg-alt); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.ward-pick select:focus-visible { outline: none; border-color: var(--primary-fg); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .15), var(--shadow-xs); }
.dir-disclaimer { background: rgba(var(--accent-rgb), .06); border: .5px solid rgba(var(--accent-rgb), .2); border-left: 2px solid var(--accent); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--text-sm); margin: var(--space-6) 0 var(--space-5); line-height: var(--leading-relaxed); }
.dir-disclaimer-mark { font-style: normal; }
.dir-disclaimer-link { color: var(--primary-fg); font-weight: var(--weight-semibold); }
.dir-disclaimer-link:hover { text-decoration: underline; }
.fac-list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); }
.fac { position: relative; border: .5px solid var(--line); border-left: 4px solid var(--secondary-fg); border-radius: var(--radius-lg); padding: var(--space-5); background: linear-gradient(180deg, rgba(var(--primary-rgb), .04), transparent 60%), var(--card); box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.fac:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); border-left-color: var(--secondary-fg); }
.fac-head { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-1); margin-bottom: var(--space-2); }
.fac-kind { align-self: flex-start; font-size: var(--text-xs); color: var(--primary-fg); font-weight: var(--weight-semibold); text-transform: uppercase; letter-spacing: var(--tracking-wide, .04em); background: rgba(var(--primary-rgb), .12); border-radius: var(--radius-sm); padding: 2px var(--space-2); line-height: 1.5; }
.fac-row { font-size: var(--text-sm); margin: 2px 0; }
.fac-row a { transition: color .3s var(--ease-out); }
.fac-row a:hover { color: var(--primary-fg); }
.fac-row a:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm); }
/* Phone as accessible tel: target — full 44px tap area, brand colour on hover */
.fac-row a[href^="tel:"] { display: inline-flex; align-items: center; min-height: 44px; color: var(--primary-fg); font-weight: var(--weight-semibold); border-radius: var(--radius-sm); }
.fac-row a[href^="tel:"]:hover { color: var(--primary-fg-strong, var(--primary-fg)); text-decoration: underline; }
.fac-src { color: var(--muted); display: block; margin: var(--space-3) calc(-1 * var(--space-5)) 0; padding: var(--space-2) var(--space-5); font-size: var(--text-xs); background: var(--overlay-subtle, rgba(0,0,0,.02)); border-top: .5px solid var(--line); }
.fac-src a { color: var(--ink-secondary); text-decoration: underline; transition: color .3s var(--ease-out); }
.fac-src a:hover { color: var(--primary-fg); }
.fac-verified { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; margin-right: 2px; border-radius: 50%; background: rgba(var(--secondary-rgb, 22,163,74), .14); color: var(--success, #16a34a); font-weight: var(--weight-bold); font-size: .65rem; vertical-align: middle; }
.ward-hub-link { margin: 0 0 var(--space-4); }
.ward-hub-link a { color: var(--primary-fg); font-weight: var(--weight-semibold); transition: opacity .3s var(--ease-out); }
.ward-hub-link a:active { opacity: .7; }
.fac-report { margin-top: var(--space-2); background: none; border: none; padding: var(--space-2) var(--space-3); margin-left: calc(-1 * var(--space-3)); color: var(--muted); font-size: var(--text-xs); cursor: pointer; text-decoration: underline; transition: color .3s var(--ease-out), background .3s var(--ease-out); min-height: 44px; border-radius: var(--radius-sm); display: inline-flex; align-items: center; }
.fac-report:hover:not(:disabled) { color: var(--primary-fg); background: rgba(var(--primary-rgb), .06); }
.fac-report:active:not(:disabled) { transform: scale(.97); }
.fac-report:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.fac-report:disabled { cursor: default; text-decoration: none; color: var(--success, #16a34a); }
.fac-report-form { margin-top: var(--space-2); display: flex; flex-direction: column; gap: var(--space-2); }
.fac-report-actions { display: flex; gap: var(--space-2); }
.fac-skeleton { display: grid; gap: var(--space-3); }
.fac-sk-item { border: .5px solid var(--line); border-left: 4px solid var(--secondary-fg); border-radius: var(--radius-lg); padding: var(--space-5); background: var(--card); display: flex; flex-direction: column; gap: var(--space-2); }
.sk-bar { height: 10px; border-radius: var(--radius-sm); background: linear-gradient(110deg, var(--bg-alt) 30%, var(--card) 50%, var(--bg-alt) 70%); background-size: 200% 100%; animation: shimmer 1.6s infinite linear; }
.sk-bar--badge { width: 70px; height: 16px; border-radius: var(--radius-sm); }
.sk-bar--sm { width: 35%; }
.sk-bar--lg { height: 14px; }
.sk-bar--wide { width: 65%; }
.sk-bar--mid { width: 50%; }
@media (prefers-reduced-motion: reduce) { .sk-bar { animation: none; } }

/* Dark mode */
.dark .fac { background: var(--bg-alt); border-color: var(--line); border-left-color: var(--secondary-fg); }
.dark .fac:hover { box-shadow: var(--shadow-lg); border-color: rgba(255,255,255,.1); border-left-color: var(--secondary-fg); }
.dark .dir-disclaimer { background: rgba(var(--accent-rgb), .08); border-color: rgba(var(--accent-rgb), .15); border-left-color: var(--accent); }
.dark .ward-pick select { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .ward-pick select:focus-visible { border-color: var(--primary-fg); }
.dark .empty-hint { color: var(--muted); border-color: rgba(255,255,255,.08); background: radial-gradient(120% 100% at 50% 0%, rgba(var(--primary-rgb), .1), transparent 70%); }
.dark .empty-hint-title { color: var(--ink); }
.dark .fac-src { background: rgba(255,255,255,.03); border-top-color: rgba(255,255,255,.08); }
.dark .fac-report:hover:not(:disabled) { color: var(--primary); }
.dark .fac-sk-item { background: var(--bg-alt); border-color: var(--line); border-left-color: var(--secondary-fg); }

/* Reduced motion — full */
@media (prefers-reduced-motion: reduce) {
  .fac:hover { transform: none; }
  .fac-report:active:not(:disabled) { transform: none; }
}
</style>
